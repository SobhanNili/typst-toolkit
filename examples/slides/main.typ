// Touying 0.8 slide deck (metropolis theme). Requires Typst ≥ 0.15.
#import "@preview/touying:0.8.0": *
#import themes.metropolis: *
#import "@preview/cetz:0.5.2"

// cetz canvas that understands touying's (pause,) inside the drawing
#let cetz-canvas = touying-reduce.with(cetz)

#show: metropolis-theme.with(
  aspect-ratio: "16-9",
  footer: self => self.info.title,
  config-info(
    title: [Grounded Typst with Claude Code],
    subtitle: [A small demo deck for the typst-toolkit plugin],
    author: [Demo Author],
    date: datetime(year: 2026, month: 11, day: 24),
    institution: [typst-toolkit],
  ),
)

#set text(font: "DejaVu Sans", size: 20pt)
#set par(justify: true)

#title-slide()

== Outline <touying:hidden>

#outline(title: none, indent: 1em, depth: 1)

= The problem

== Why agents get Typst wrong

- Training data is dominated by *LaTeX*
#pause
- Typst changed between versions (0.11 → 0.15)
#pause
- Packages change even faster: cetz, touying, fletcher

#pause
#alert[Result:] code that looks plausible but fails to compile, or compiles and renders wrong.

== A silent failure

#grid(columns: (1fr, 1fr), gutter: 1.5em, align: top,
  [
    *What was written*
    #text(1.25em)[```typ
    \textbf{important}
    $\frac{a}{b}$
    ```]
  ],
  [
    *What Typst sees*
    - `\t` escapes `t`, so the text prints as `textbf{important}`
    - `rac` is an unknown variable → error
  ],
)

= The workflow

== Ground → check → look

#align(center, scale(120%, reflow: true, include "figures/architecture.typ"))

== Building a diagram step by step

#cetz-canvas({
  import cetz.draw: *
  circle((0, 0), radius: 1.2, name: "docs", fill: rgb("#d6c6b7"))
  content("docs", [docs])
  (pause,)
  circle((4, 0), radius: 1.2, name: "check", fill: rgb("#eb811b").lighten(40%))
  content("check", [check])
  line("docs.east", "check.west", mark: (end: "stealth"), stroke: 1.5pt)
  (pause,)
  circle((8, 0), radius: 1.2, name: "look", fill: rgb("#23373b").lighten(70%))
  content("look", [look])
  line("check.east", "look.west", mark: (end: "stealth"), stroke: 1.5pt)
})

== Math stays native

$
  f(x) &= pause x^2 + 2x + 1 \
       &= pause (x + 1)^2
$

#meanwhile
Typst math: `x^2`, `(x + 1)^2`. No backslashes, no braces.

#speaker-note[
  Point out that `pause` also works inside equations.
]

#focus-slide[
  Don't guess. Look it up, compile, render.
]
