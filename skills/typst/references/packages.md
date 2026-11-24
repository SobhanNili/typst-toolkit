# Packages worth reaching for

Before building a figure, environment or layout feature from scratch, check whether a maintained package
already does it. This is a curated starting point for scientific writing, slides and figures, not the full
catalogue: `ttk pkg search <words>` searches all of Typst Universe.

## Rules

1. **The project's choice wins.** Run `ttk pkg deps` first. If the project already imports a package for
   this job, use that package at its pinned version, even if another one is listed here.
2. **Pick the version, then read its docs.** New import: take the latest from `ttk pkg info <name>` and check
   that its `compiler` minimum is no newer than `ttk doctor`'s typst. Then read `ttk pkg readme <name:ver>`
   and look up exact parameters with `ttk pkg api <name:ver> <symbol>`. Never write a package's API from
   memory; most of these changed between versions.
3. **Prototype in isolation.** `ttk snippet -e '#import "@preview/<name>:<ver>": *  ...'`, render, look, then
   integrate.
4. **Don't stack overlapping packages.** One plotting package, one theorem package, one code-listing package
   per project, unless there is a clear reason.

## Figures and diagrams

| Package | Use for |
|---|---|
| `cetz` | General drawing (TikZ equivalent): custom figures, geometry, anything without a dedicated package. Many packages below are built on it. |
| `fletcher` | Nodes and arrows: flowcharts, pipelines, architecture and block diagrams (including transformer / attention block diagrams), commutative diagrams, state machines. |
| `diagraph` | Graphs laid out automatically by Graphviz (DOT syntax), with math in labels. Large graphs, trees, dependency graphs. |
| `neural-netz` | PlotNeuralNet-style 3D layer stacks for CNN architectures (conv, pool, residual blocks, legends). For non-CNN architectures use `fletcher` or `cetz`. |

## Plots and data

| Package | Use for |
|---|---|
| `lilaq` | Scientific data plots: line, scatter, bar, error bars, colormaps, legends, axes. First choice for plots from data. |
| `cetz-plot` | Plots that are part of a `cetz` drawing (shared coordinates, annotations drawn on top). |

## Algorithms and code

| Package | Use for |
|---|---|
| `algorithmic` | Pseudocode in the style of LaTeX algorithmicx (`Procedure`, `If`, `For`, `Return`, numbered lines). |
| `lovelace` | Free-form pseudocode with line numbers and indentation guides; least opinionated. |
| `codly` (+ `codly-languages`) | Code listings: line numbers, highlighted and annotated lines, language labels. |

## Math and scientific writing

| Package | Use for |
|---|---|
| `physica` | Physics and engineering notation: derivatives, differentials, bra-ket, tensors, vector calculus, matrices. |
| `unify` / `zero` | Numbers with units and uncertainties (siunitx equivalents). `zero` also aligns numbers in table columns. |
| `equate` | Numbering individual lines of multi-line equations, and sub-numbering (1a, 1b). |
| `numera` | Per-chapter figure and equation numbering (1.1, 1.2, 2.1), subfigure numbering, different formats on the element and in references. Works with `equate`. |
| `theorion` / `ctheorems` | Theorem, lemma, definition, proof environments with shared counters. |
| `subpar` | Subfigures (a), (b) in a grid, each referenceable. |

## Slides and posters

| Package | Use for |
|---|---|
| `touying` | Slides: themes (metropolis, university, dewdrop, ...), `#pause` / `#meanwhile` reveals, animated `cetz` / `fletcher` via `touying-reduce`, speaker notes. |
| `peace-of-posters` | Scientific posters: column layouts, titled boxes, themes. |

## Domain-specific (search these when the topic comes up)

Sequence diagrams `chronos` · automata `finite` · quantum circuits `quill` · electronic circuits `zap`,
`circuiteria` · Mermaid diagrams `merman` · Venn diagrams `cetz-venn` · chemical structures `alchemist` ·
chemical formulas `typsium` · function plots `simple-plot` · 3D surfaces `plotsy-3d` · annotating parts of
equations `mannot` · glossaries and acronyms `glossarium`, `acrostiche` · callout boxes `showybox`,
`gentle-clues` · margin notes and TODOs `drafting`, `marginalia` · table shortcuts `pillar`, `rowmantic`,
`tablem` · pointing at parts of slides `pinit` · paper templates `charged-ieee`, `arkheion`,
`bloated-neurips`, `clear-iclr`, `lucky-icml`, `fine-lncs`, `tracl`.

## Avoid

- `tablex`: superseded by the built-in `table` (Typst ≥ 0.11).
- `mitex`: renders LaTeX math. Write Typst math instead.
- Icon packages that need a locally installed font (e.g. `fontawesome`): the document then breaks on
  typst.app unless the font is uploaded there.
