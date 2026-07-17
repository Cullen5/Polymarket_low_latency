#!/usr/bin/env python3
"""
make_figures.py -- Generate all figures for the Polymarket low-latency writeup.

Data sources (all real project artefacts):
  * Recovered backtest data (from git history, origin/Optimized branch),
    under ../recovered_optimizer/optimizer/dublin/ :
        regime_trade_log.parquet   8,576 replayed trades w/ P&L + microstructure
        edge_signals.parquet       4,892 signals w/ Polymarket repricing curves
  * Measured deployment latencies (from the live AWS deployment)
  * Observed live fill rate (post-mortem)

Figures produced:
  * fig_architecture.png     two-node system topology
  * fig_latency_budget.png   measured end-to-end latency path (~140 ms)
  * fig_repricing_curve.png  empirical Polymarket repricing after a Binance move (the edge)
  * fig_equity_curve.png     cumulative gross vs net P&L across 8,576 trades (fee drag)
  * fig_pnl_distribution.png per-trade net P&L distribution
  * fig_edge_drivers.png     conditional edge: tick rate / poly distance / hold time / asset

Run from the writeup directory:
    python make_figures.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
REC = HERE.parent / "recovered_optimizer" / "optimizer" / "dublin"

# ── House style (light, print-friendly) ──────────────────────────────
plt.rcParams.update({
    "font.size": 11,
    "font.family": "sans-serif",
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "figure.dpi": 150,
})

INK   = "#1b2430"
BLUE  = "#2f6db0"
TEAL  = "#2a9d8f"
AMBER = "#e9a13b"
RED   = "#c1443c"
GREY  = "#9aa4ad"
GREEN = "#3a9b57"
LIGHT = "#eef2f5"
ASSET_C = {"BTC": "#e9a13b", "ETH": "#2f6db0", "SOL": "#2a9d8f", "XRP": "#8f5fb0"}


def _load(name: str) -> pd.DataFrame:
    return pd.read_parquet(REC / name)


def _wr(x) -> float:
    return (x > 0).mean() * 100.0


# ═════════════════════════════════════════════════════════════════════
# 1. SYSTEM ARCHITECTURE
# ═════════════════════════════════════════════════════════════════════

def fig_architecture() -> None:
    fig, ax = plt.subplots(figsize=(11, 6.2))
    ax.set_xlim(0, 100); ax.set_ylim(0, 62); ax.axis("off")

    def node(x, y, w, h, ec):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
            boxstyle="round,pad=0.6,rounding_size=1.6",
            linewidth=1.6, edgecolor=ec, facecolor=LIGHT, zorder=1))

    def sub(x, y, w, h, title, lines, ec):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
            boxstyle="round,pad=0.3,rounding_size=1.0",
            linewidth=1.1, edgecolor=ec, facecolor="white", zorder=2))
        ax.text(x + w / 2, y + h - 2.1, title, ha="center", va="top",
                fontsize=9.5, fontweight="bold", color=INK, zorder=3)
        ax.text(x + w / 2, y + h - 4.7, lines, ha="center", va="top",
                fontsize=7.6, color="#41505e", zorder=3, linespacing=1.35)

    node(3, 6, 40, 50, BLUE)
    ax.text(23, 53.3, "TOKYO  ·  AWS ap-northeast-1", ha="center",
            fontsize=11.5, fontweight="bold", color=BLUE)
    ax.text(23, 50.6, "co-located with Binance matching engine  (~3 ms)",
            ha="center", fontsize=8.2, color="#41505e", style="italic")
    sub(6.5, 40, 33, 8.4, "BinanceFeed  (asyncio, core 0)",
        "depth10@100ms + @trade  ·  BTC ETH SOL XRP", BLUE)
    sub(6.5, 29.5, 33, 8.4, "RollingWindow x4  (worker, core 1)",
        "60 s metrics: mid · OFI · VWAP · flow", TEAL)
    sub(6.5, 19, 33, 8.4, "LargeMoveDetector  (3-gate AND)",
        "price move · tick density · dollar flow", TEAL)
    sub(6.5, 8.5, 33, 8.4, "SignalBridge -> UDP sender",
        "pack 20 B  ·  3x redundant  ·  2 s heartbeat", AMBER)

    node(57, 6, 40, 50, RED)
    ax.text(77, 53.3, "DUBLIN  ·  AWS eu-west-1", ha="center",
            fontsize=11.5, fontweight="bold", color=RED)
    ax.text(77, 50.6, "near Polymarket CLOB  (~11 ms)",
            ha="center", fontsize=8.2, color="#41505e", style="italic")
    sub(60.5, 40, 33, 8.4, "SignalReceiver (UDP)  +  dedup",
        "unpack · drop 2 redundant copies · dead-man", AMBER)
    sub(60.5, 29.5, 33, 8.4, "8 MarketWorkers  (4 asset x 2 tf)",
        "own ring buffers · live CLOB book", BLUE)
    sub(60.5, 19, 33, 8.4, "trade_logic  (10 entry / 5 exit gates)",
        "PositionManager FSM · RateLimiter", TEAL)
    sub(60.5, 8.5, 33, 8.4, "OrderEngine  (ECDSA + HTTP)",
        "FOK/FAK  ·  mock <-> live: one URL", RED)

    ax.add_patch(FancyArrowPatch((43.5, 12.7), (56.5, 44.2),
        arrowstyle="-|>", mutation_scale=22, linewidth=2.4, color=INK,
        zorder=4, connectionstyle="arc3,rad=0.16"))
    ax.text(50, 41.5, "UDP", ha="center", fontsize=10.5, fontweight="bold", color=INK)
    ax.text(50, 38.4, "20 bytes  ·  3x copies", ha="center", fontsize=8.0, color="#41505e")
    ax.text(50, 35.9, "~120 ms transit", ha="center", fontsize=8.0, color=RED, fontweight="bold")

    ax.text(23, 2.6, "Binance spot  (source of truth)", ha="center", fontsize=8.4, color=INK,
            bbox=dict(boxstyle="round,pad=0.3", fc="#dfeaf5", ec=BLUE))
    ax.text(77, 2.6, "Polymarket 5m / 15m up-down markets", ha="center", fontsize=8.4, color=INK,
            bbox=dict(boxstyle="round,pad=0.3", fc="#f6e2e0", ec=RED))
    ax.add_patch(FancyArrowPatch((23, 6), (23, 4.4), arrowstyle="-", linewidth=1.2, color=GREY))
    ax.add_patch(FancyArrowPatch((77, 4.4), (77, 6), arrowstyle="-|>",
                 mutation_scale=14, linewidth=1.2, color=GREY))

    fig.tight_layout()
    fig.savefig(HERE / "fig_architecture.png", bbox_inches="tight")
    plt.close(fig)
    print("  wrote fig_architecture.png")


# ═════════════════════════════════════════════════════════════════════
# 2. LATENCY BUDGET
# ═════════════════════════════════════════════════════════════════════

def fig_latency_budget() -> None:
    segments = [
        ("Binance -> Tokyo detect",     3.0,   BLUE),
        ("Tokyo compute (detect+pack)", 0.5,   TEAL),
        ("Tokyo -> Dublin (UDP)",       120.0, RED),
        ("Dublin compute (gates+sign)", 5.0,   AMBER),
        ("Dublin -> Polymarket order",  11.0,  "#8f5fb0"),
    ]
    fig, ax = plt.subplots(figsize=(11, 3.3))
    left = 0.0
    for label, dur, c in segments:
        ax.barh(0, dur, left=left, height=0.62, color=c, edgecolor="white",
                linewidth=1.4, label=f"{label}  ({dur:g} ms)")
        if dur > 8:
            ax.text(left + dur / 2, 0, f"{dur:g} ms", ha="center", va="center",
                    color="white", fontsize=10, fontweight="bold")
        left += dur
    total = sum(d for _, d, _ in segments)
    ax.axvline(total, color=INK, linestyle=":", linewidth=1.3)
    ax.text(total + 1.5, 0.0, f"~{total:.0f} ms\nend-to-end", ha="left", va="center",
            fontsize=10.5, fontweight="bold", color=INK, linespacing=1.1)
    ax.axhspan(-0.70, -0.50, xmin=0.0, xmax=150 / (total * 1.18), color=TEAL, alpha=0.20)
    ax.text(75, -0.60, "Polymarket book repricing lag ~150-500 ms  (the window we must beat)",
            ha="center", va="center", fontsize=8.4, color="#1f7a6d", style="italic")
    ax.set_ylim(-0.95, 0.55); ax.set_xlim(0, total * 1.18); ax.set_yticks([])
    ax.set_xlabel("milliseconds"); ax.grid(axis="x", alpha=0.25)
    ax.set_title("End-to-End Signal Path: Binance Move to Polymarket Order", loc="left", pad=46)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.52), ncol=3, frameon=False,
              fontsize=8.6, handlelength=1.3, columnspacing=1.6)
    fig.tight_layout()
    fig.savefig(HERE / "fig_latency_budget.png", bbox_inches="tight")
    plt.close(fig)
    print("  wrote fig_latency_budget.png")


# ═════════════════════════════════════════════════════════════════════
# 3. EMPIRICAL REPRICING CURVE  (the edge, measured)
# ═════════════════════════════════════════════════════════════════════

def fig_repricing_curve() -> None:
    e = _load("edge_signals.parquet")
    horizons = [0.5, 1, 2, 3, 5, 10]
    cols = ["repricing_500ms", "repricing_1s", "repricing_2s",
            "repricing_3s", "repricing_5s", "repricing_10s"]

    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    for a in ["BTC", "ETH", "SOL", "XRP"]:
        sub = e[e.asset == a]
        ys = [sub[c].mean() for c in cols]
        ax.plot(horizons, ys, marker="o", markersize=5, linewidth=1.6,
                color=ASSET_C[a], alpha=0.85, label=a)
    agg = [e[c].mean() for c in cols]
    ax.plot(horizons, agg, marker="s", markersize=8, linewidth=3.0,
            color=INK, label="all signals", zorder=5)
    ax.axhline(0, color=GREY, linewidth=1.0, linestyle="--")

    # Shade the profitable short-horizon region.
    ax.axvspan(0.5, 2, color=TEAL, alpha=0.08)
    ax.text(1.05, ax.get_ylim()[1] * 0.9, "edge lives here\n(~0.5-2 s)", fontsize=8.5,
            color="#1f7a6d", ha="center", style="italic")

    ax.set_xscale("log")
    ax.set_xticks(horizons)
    ax.set_xticklabels([f"{h:g}s" for h in horizons])
    ax.set_xlabel("time after Binance signal")
    ax.set_ylabel("mean Polymarket repricing toward signal (cents)")
    ax.set_title("Empirical Edge: How Polymarket Reprices After a Binance Move", loc="left")
    ax.legend(frameon=False, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.16))
    fig.tight_layout()
    fig.savefig(HERE / "fig_repricing_curve.png", bbox_inches="tight")
    plt.close(fig)
    print("  wrote fig_repricing_curve.png")


# ═════════════════════════════════════════════════════════════════════
# 4. EQUITY CURVE  (gross vs net -> fee drag)
# ═════════════════════════════════════════════════════════════════════

def fig_equity_curve() -> None:
    t = _load("regime_trade_log.parquet").sort_values("local_ns").reset_index(drop=True)
    n = np.arange(1, len(t) + 1)
    net = t.pnl_cents.cumsum().values
    gross = t.pnl_gross_cents.cumsum().values

    fig, ax = plt.subplots(figsize=(11, 4.4))
    ax.plot(n, gross, color=GREY, linewidth=1.6, label=f"gross  (+{gross[-1]:,.0f}¢)")
    ax.plot(n, net, color=BLUE, linewidth=1.8, label=f"net of fees  (+{net[-1]:,.0f}¢)")
    ax.fill_between(n, net, gross, color=RED, alpha=0.12)
    ax.text(len(t) * 0.5, (gross[int(len(t)*0.5)] + net[int(len(t)*0.5)]) / 2,
            f"fees: {t.fees_cents.sum():,.0f}¢\n({t.fees_cents.sum()/gross[-1]*100:.0f}% of gross)",
            fontsize=9, color=RED, ha="center", va="center", fontweight="bold")
    ax.axhline(0, color=GREY, linewidth=0.8, linestyle="--")
    ax.set_xlabel("trade number (chronological)")
    ax.set_ylabel("cumulative P&L (cents)")
    ax.set_title(f"Backtest Equity Curve — {len(t):,} Trades, Gross vs Net of Fees", loc="left")
    ax.legend(frameon=False, loc="upper left")
    ax.set_xlim(0, len(t))
    fig.tight_layout()
    fig.savefig(HERE / "fig_equity_curve.png", bbox_inches="tight")
    plt.close(fig)
    print("  wrote fig_equity_curve.png")


# ═════════════════════════════════════════════════════════════════════
# 5. PER-TRADE P&L DISTRIBUTION
# ═════════════════════════════════════════════════════════════════════

def fig_pnl_distribution() -> None:
    t = _load("regime_trade_log.parquet")
    p = t.pnl_cents.clip(-25, 25)
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    ax.hist(p, bins=60, color=GREY, edgecolor="white", linewidth=0.4)
    ax.axvline(0, color=INK, linewidth=1.2)
    ax.axvline(t.pnl_cents.median(), color=BLUE, linestyle="--", linewidth=1.6,
               label=f"median {t.pnl_cents.median():+.2f}¢")
    ax.axvline(t.pnl_cents.mean(), color=AMBER, linestyle="--", linewidth=1.6,
               label=f"mean {t.pnl_cents.mean():+.2f}¢")
    txt = (f"n = {len(t):,}\nwin rate {_wr(t.pnl_cents):.1f}%\n"
           f"avg hold {t.hold_ms.mean()/1000:.1f}s")
    ax.text(0.97, 0.95, txt, transform=ax.transAxes, ha="right", va="top",
            fontsize=9.5, bbox=dict(boxstyle="round,pad=0.4", fc="#f5f7fa", ec=GREY))
    ax.set_xlabel("net P&L per trade (cents, clipped to ±25¢)")
    ax.set_ylabel("count")
    ax.set_title("Per-Trade Net P&L Distribution (Backtest)", loc="left")
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(HERE / "fig_pnl_distribution.png", bbox_inches="tight")
    plt.close(fig)
    print("  wrote fig_pnl_distribution.png")


# ═════════════════════════════════════════════════════════════════════
# 6. CONDITIONAL EDGE DRIVERS  (2x2)
# ═════════════════════════════════════════════════════════════════════

def fig_edge_drivers() -> None:
    t = _load("regime_trade_log.parquet")
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.2))

    # (a) win rate vs tick rate
    ax = axes[0, 0]
    tb = [0, 30, 60, 90, 120, 200, 300, 1e9]
    lab = ["<30", "30-60", "60-90", "90-120", "120-200", "200-300", "300+"]
    t["b"] = pd.cut(t.env_ticks_per_sec, tb, labels=lab)
    g = t.groupby("b", observed=True).pnl_cents
    wr = g.apply(_wr); avg = g.mean()
    cols = [GREEN if avg[l] > 0 else RED for l in lab]
    ax.bar(lab, wr.reindex(lab), color=cols, edgecolor="white")
    ax.axhline(50, color=RED, ls="--", lw=1, alpha=0.6)
    ax.text(6, 50.6, "coin flip", fontsize=7.5, color=RED, ha="right")
    for i, l in enumerate(lab):
        ax.text(i, wr[l] + 0.5, f"{wr[l]:.0f}%", ha="center", fontsize=8, fontweight="bold")
    ax.set_ylim(44, 74); ax.set_ylabel("win rate (%)")
    ax.set_title("(a) Higher tick rate → lower edge", loc="left", fontsize=11)
    ax.tick_params(axis="x", labelrotation=30, labelsize=8)
    ax.set_xlabel("Binance ticks / sec at signal")

    # (b) win rate vs poly distance from 0.50
    ax = axes[0, 1]
    db = [0, .03, .06, .09, .12, .15, .20, .30, 1]
    dl = ["<.03", ".03-.06", ".06-.09", ".09-.12", ".12-.15", ".15-.20", ".20-.30", ">.30"]
    t["d"] = pd.cut(t.env_poly_dist_from_50, db, labels=dl)
    wr2 = t.groupby("d", observed=True).pnl_cents.apply(_wr).reindex(dl)
    norm = plt.Normalize(wr2.min(), wr2.max())
    ax.bar(dl, wr2, color=plt.cm.RdYlGn(norm(wr2.values)), edgecolor="white")
    ax.axhline(50, color=RED, ls="--", lw=1, alpha=0.6)
    for i, l in enumerate(dl):
        ax.text(i, wr2[l] + 0.4, f"{wr2[l]:.0f}%", ha="center", fontsize=8, fontweight="bold")
    ax.set_ylim(46, 72); ax.set_ylabel("win rate (%)")
    ax.set_title("(b) Near 0.50 = near-random", loc="left", fontsize=11)
    ax.tick_params(axis="x", labelrotation=30, labelsize=8)
    ax.set_xlabel("Polymarket price distance from 0.50")

    # (c) total pnl by hold time
    ax = axes[1, 0]
    hb = [0, 2000, 5000, 8000, 12000, 20000, 1e9]
    hl = ["0-2s", "2-5s", "5-8s", "8-12s", "12-20s", ">20s"]
    t["h"] = pd.cut(t.hold_ms, hb, labels=hl)
    tot = t.groupby("h", observed=True).pnl_cents.sum().reindex(hl).fillna(0)
    ax.bar(hl, tot, color=[GREEN if v > 0 else RED for v in tot], edgecolor="white")
    ax.axhline(0, color=INK, lw=0.8)
    for i, l in enumerate(hl):
        off = 400 if tot[l] >= 0 else -400
        ax.text(i, tot[l] + off, f"{tot[l]:,.0f}", ha="center",
                va="bottom" if tot[l] >= 0 else "top", fontsize=8, fontweight="bold")
    ax.set_ylabel("total P&L (cents)")
    ax.set_title("(c) Hold time: sweet spots vs timeout wipeout", loc="left", fontsize=11)
    ax.set_xlabel("holding period")
    ax.tick_params(axis="x", labelsize=8)

    # (d) per-asset win rate + total pnl
    ax = axes[1, 1]
    assets = ["BTC", "ETH", "SOL", "XRP"]
    ga = t.groupby("asset").pnl_cents
    awr = ga.apply(_wr).reindex(assets)
    apnl = ga.sum().reindex(assets)
    x = np.arange(len(assets))
    ax.bar(x, awr, color=[ASSET_C[a] for a in assets], edgecolor="white", width=0.6)
    for i, a in enumerate(assets):
        ax.text(i, awr[a] + 0.4, f"{awr[a]:.0f}%", ha="center", fontsize=8.5, fontweight="bold")
        ax.text(i, 50.5, f"+{apnl[a]:,.0f}¢", ha="center", fontsize=8, color="white",
                fontweight="bold")
    ax.axhline(50, color=RED, ls="--", lw=1, alpha=0.6)
    ax.set_xticks(x); ax.set_xticklabels(assets)
    ax.set_ylim(48, 70); ax.set_ylabel("win rate (%)")
    ax.set_title("(d) Per-asset win rate (total P&L labelled)", loc="left", fontsize=11)

    fig.suptitle(f"Conditional Structure of the Edge  —  {len(t):,} backtest trades",
                 fontsize=13.5, fontweight="bold", x=0.02, ha="left")
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(HERE / "fig_edge_drivers.png", bbox_inches="tight")
    plt.close(fig)
    print("  wrote fig_edge_drivers.png")


# ═════════════════════════════════════════════════════════════════════
# 7. TICK-RATE MECHANISM  (why the edge fades in fast markets)
# ═════════════════════════════════════════════════════════════════════

def fig_tickrate_mechanism() -> None:
    tb = [0, 30, 60, 90, 120, 200, 300, 1e9]
    lab = ["<30", "30-60", "60-90", "90-120", "120-200", "200-300", "300+"]
    t = _load("regime_trade_log.parquet")
    m = _load("regime_moves.parquet")
    t["b"] = pd.cut(t.env_ticks_per_sec, tb, labels=lab)
    m["b"] = pd.cut(m.local_ticks_per_second, tb, labels=lab)

    wr = t.groupby("b", observed=True).pnl_cents.apply(_wr).reindex(lab)
    opp = t.groupby("b", observed=True).exit_reason.apply(
        lambda s: s.isin(["opposite_signal", "stop_loss"]).mean() * 100).reindex(lab)
    rev = m.groupby("b", observed=True).reverted_1s.apply(
        lambda x: x.mean() * 100).reindex(lab)
    spr = t.groupby("b", observed=True).env_poly_spread.mean().reindex(lab)
    x = np.arange(len(lab))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6))
    axb = ax1.twinx()
    l1 = ax1.plot(x, wr, "-o", color=BLUE, lw=2.4, ms=6, label="win rate (left)")
    l2 = axb.plot(x, rev, "-s", color=RED, lw=2.4, ms=6,
                  label="Binance move reverses <1s (right)")
    l3 = axb.plot(x, opp, "--^", color=AMBER, lw=1.8, ms=5,
                  label="reversed/stopped-out exits (right)")
    ax1.set_ylabel("win rate (%)", color=BLUE)
    axb.set_ylabel("reversal rate (%)", color=RED)
    ax1.set_xticks(x); ax1.set_xticklabels(lab, rotation=30, fontsize=8.5)
    ax1.set_xlabel("Binance ticks / sec")
    ax1.set_title("(a) Win rate falls as the move itself whipsaws", loc="left", fontsize=11.5)
    ax1.set_ylim(46, 72); axb.set_ylim(0, 32)
    ls = l1 + l2 + l3
    ax1.legend(ls, [h.get_label() for h in ls], loc="lower left", fontsize=8, frameon=False)

    ax2.plot(x, spr * 100, "-o", color=TEAL, lw=2.4, ms=6)
    for xi, s in zip(x, spr):
        ax2.text(xi, s * 100 + 0.03, f"{s*100:.1f}", ha="center", fontsize=8, color=INK)
    ax2.set_xticks(x); ax2.set_xticklabels(lab, rotation=30, fontsize=8.5)
    ax2.set_xlabel("Binance ticks / sec")
    ax2.set_ylabel("mean Polymarket spread (cents)")
    ax2.set_title("(b) Polymarket quotes tighten (more competition)", loc="left", fontsize=11.5)

    fig.suptitle("Why the edge fades in fast markets  —  reversal + competition, not throughput",
                 x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(HERE / "fig_tickrate_mechanism.png", bbox_inches="tight")
    plt.close(fig)
    print("  wrote fig_tickrate_mechanism.png")


# ═════════════════════════════════════════════════════════════════════

def print_summary() -> None:
    t = _load("regime_trade_log.parquet")
    # active hours = sum of per-recording spans
    hrs = t.groupby("recording").local_ns.agg(lambda s: (s.max() - s.min()) / 1e9 / 3600).sum()
    print("\n--- key numbers for the writeup ---")
    print(f"trades={len(t):,}  recordings={t.recording.nunique()}  active_hours={hrs:.1f}")
    print(f"win_rate={_wr(t.pnl_cents):.1f}%  net={t.pnl_cents.sum():,.0f}c  "
          f"gross={t.pnl_gross_cents.sum():,.0f}c  fees={t.fees_cents.sum():,.0f}c "
          f"({t.fees_cents.sum()/t.pnl_gross_cents.sum()*100:.0f}% of gross)")
    print(f"avg_hold={t.hold_ms.mean()/1000:.1f}s  "
          f"convergence={(t.exit_reason=='convergence').mean()*100:.0f}%")


if __name__ == "__main__":
    print("Generating figures ...")
    fig_architecture()
    fig_latency_budget()
    fig_repricing_curve()
    fig_equity_curve()
    fig_pnl_distribution()
    fig_edge_drivers()
    fig_tickrate_mechanism()
    print_summary()
    print("Done.")
