\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{tmsce}[2026 Clean Draft Version]

\LoadClass[11pt,a4paper]{article}

% ---------- Packages ----------
\RequirePackage{geometry}
\RequirePackage{titlesec}
\RequirePackage{setspace}
\RequirePackage{hyperref}

% ---------- Page geometry ----------
\geometry{left=1.05in,right=1.05in,top=1.0in,bottom=1.0in}

% ---------- Clean page style (NO footer line) ----------
\pagestyle{plain}

% ---------- Section style ----------
\titleformat{\section}{\normalfont\bfseries\large}{\thesection.}{0.6em}{}
\titleformat{\subsection}{\normalfont\bfseries\normalsize}{\thesubsection.}{0.6em}{}

% ---------- Abstract (simple) ----------
\renewenvironment{abstract}{%
  \par\noindent\textbf{Abstract.}\ }{%
  \par\vspace{0.6em}%
}

% ---------- Simple title ----------
\renewcommand{\maketitle}{%
  \begin{center}
    {\Large\bfseries \@title\par}
    \vspace{0.8em}
    {\normalsize \@author\par}
  \end{center}
  \vspace{1em}
}

% Slightly compact look
\setstretch{1.05}