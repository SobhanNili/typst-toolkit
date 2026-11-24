# LaTeX → Typst (verified against Typst 0.15.1)

Every Typst construct below compiles on 0.15.1 (see `examples/verify/cheatsheet-test.typ` in the plugin).
For anything not listed: `ttk docs show for-latex-users`, symbols via `ttk docs sym '<\latexcmd>'`.

## Markup

| LaTeX | Typst |
|---|---|
| `\textbf{x}` / `\textit{x}` / `\texttt{x}` | `*x*` / `_x_` / `` `x` `` (or `#strong[x]`, `#emph[x]`, `#raw("x")`) |
| `\underline{x}` `\sout{x}` `\textsc{x}` | `#underline[x]` `#strike[x]` `#smallcaps[x]` |
| `\textsuperscript{x}` / sub | `#super[x]` / `#sub[x]` |
| `{\color{red} x}` `\large` | `#text(fill: red)[x]` `#text(size: 14pt)[x]` |
| `\section{A}` `\subsection{B}` | `= A` `== B` (numbering: `#set heading(numbering: "1.1")`) |
| `\label{sec:a}` `\ref{sec:a}` | `= A <sec:a>` … `@sec:a` |
| `\cite{key}` / `\citet{key}` | `@key` / `#cite(<key>, form: "prose")` |
| `\bibliography{refs}` + style | `#bibliography("refs.bib", style: "ieee")` |
| `\footnote{x}` | `#footnote[x]` |
| `\href{url}{text}` / `\url{u}` | `#link("url")[text]` / `#link("u")` |
| `itemize` / `enumerate` / `description` | `- item` / `+ item` / `/ Term: def` (indent to nest) |
| `\\` (line break) | `\` at end of line (or `#linebreak()`); `\\` in Typst prints a backslash! |
| `\newpage` / `\clearpage` | `#pagebreak()` (`#pagebreak(weak: true)`) |
| `\vspace{4pt}` `\hspace{1em}` `\hfill` | `#v(4pt)` `#h(1em)` `#h(1fr)` |
| `~` nbsp, `--`, `---` | same: `~`, `--`, `---` |
| ``` ``quotes'' ``` | `"quotes"` (smart quotes automatic) |
| `% comment` | `// comment`, `/* block */` |
| `\begin{center}` | `#align(center)[...]` |
| `\fbox`, `minipage`, `\colorbox` | `#box(stroke: 1pt, inset: 3pt)[..]`, `#block(width: 50%)[..]`, `#block(fill: luma(230), inset: 4pt)[..]` |
| `\includegraphics[width=5cm]{f}` | `#image("f.png", width: 5cm)` |
| `figure` + `\caption` + `\label` | `#figure(image("f.png"), caption: [Cap.]) <fig:a>` |
| `tabular` | `#table(columns: 2, align: (left, center), table.header[*A*][*B*], [1], [2])` (`table.hline()`) |
| `\newcommand{\x}[1]{..}` | `#let x(arg) = [..#arg..]` |
| preamble `\usepackage` | `#import "@preview/name:ver": *` |
| `\documentclass` + geometry | `#set page(paper: "a4", margin: 2cm)`, `#set text(size: 11pt, lang: "en")`, `#set par(justify: true)` |
| `\tableofcontents` | `#outline()` |
| `\thepage` / counters | `#context counter(page).get()`, `#context counter(heading).display()` (need `context`!) |
| `\input{f}` / `\include{f}` | `#include "f.typ"` (content) / `#import "f.typ": fn` (definitions) |
| `\lipsum` | `#lorem(50)` |

## Math (inside `$...$`; `$ x $` with inner spaces = display)

| LaTeX | Typst |
|---|---|
| `\frac{a}{b}` | `a/b` or `frac(a, b)` |
| `x^{2n}`, `x_{ij}` | `x^(2n)`, `x_(i j)` — braces render literally; `ij` would be ONE variable named ij |
| `\sqrt{x}`, `\sqrt[3]{x}` | `sqrt(x)`, `root(3, x)` |
| `\sum_{i=1}^n`, `\int_0^1 f\,dx`, `\prod` | `sum_(i=1)^n`, `integral_0^1 f(x) dif x`, `product` |
| `\alpha \Gamma` | `alpha Gamma` (no backslash) |
| `\varepsilon` / `\epsilon` | `epsilon` / `epsilon.alt` |
| `\partial \nabla \infty` | `partial nabla infinity` (or `oo`) |
| `\leq \geq \neq \approx \equiv` | `<= >= != approx equiv` (or `lt.eq gt.eq eq.not`) |
| `\cdot \times \ldots \cdots` | `dot.op times dots dots.c` |
| `\to \Rightarrow \in \notin \subseteq \forall \exists` | `-> => in in.not subset.eq forall exists` |
| `\mathbb{R}`, `\mathcal{A}`, `\mathbf{v}`, `\mathrm{d}` | `RR` (`bb(X)`), `cal(A)`, `bold(v)`, `upright(d)` |
| `\operatorname{argmax}` | `op("argmax")`; under-limits: `op("argmax", limits: #true)_x` (in math, literals like `true`/`none` need `#`) |
| `\text{if}` | `"if"` (quoted text) |
| `\hat x \tilde x \bar x \vec x \dot x` | `hat(x) tilde(x) overline(x) arrow(x) dot(x)` |
| `\lvert x\rvert`, `\lVert x\rVert`, `\lfloor` | `abs(x)`, `norm(x)`, `floor(x)` / `ceil(x)` |
| `\left( \frac{a}{b} \right)` | parentheses auto-scale; explicit `lr(( a/b ))` |
| `pmatrix`, `\binom` | `mat(1, 2; 3, 4)` (`delim: "["`), `binom(n, k)` |
| column vector | `vec(1, 2)` |
| `cases` | `cases(x "if" x > 0, 0 "otherwise")` |
| `align` with `&` and `\\` | `$ a &= b \ &= c $` (single `\` for line break) |
| `\quad \qquad \,` | `quad wide thin` |
| `\label{eq}` + `\eqref` | `$ ... $ <eq:e>` + `@eq:e` (needs `#set math.equation(numbering: "(1)")`) |

## Behavioural differences that bite

- Multi-letter identifiers in math are variables/functions: `ab` is one identifier → write `a b`.
  Unknown multi-letter names error with "unknown variable".
- `#set` is scoped to the enclosing block/file; there is no global `\renewcommand` — use show rules or a
  template function applied with `#show: tpl.with(..)`.
- Content vs. strings: `[*bold*]` is content, `"text"` is a string; `+` joins content, `str()` converts numbers.
- No `\makeatletter`-style hacks: styling hooks are `show` rules on element selectors (`heading.where(level: 1)`,
  `figure.where(kind: table)`, `raw.where(block: true)`, regex `show "TODO": ...`).
- Page-dependent values (counters, `query`, `here`, `measure`) need `context`.
