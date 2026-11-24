# Visual feedback loop for templates and figures

Compiling only proves the document is valid. For layout, styling, figures and templates you must look.
Images cost context: pick the cheapest view that answers your question.

## Choosing the view

| Question | View | Cost |
|---|---|---|
| Overall flow of a long doc: page breaks, empty pages, figure placement | `ttk render f --sheet` (contact sheet, 1 image) | low |
| Does page N look right? | `ttk render f -p N` (110 ppi default) | medium |
| Fine detail: kerning, arrow heads, alignment, overlaps, thin strokes, small labels | `ttk render f -p N --region x0,y0,x1,y1` (200 ppi crop) | low–medium |
| Did my change do what I intended (and nothing else)? | `ttk render f -p N --compare` (before│after) | medium |
| Iterating on one figure/table/component | `ttk snippet fig.typ` (auto-sized page, 180 ppi) | low |
| Where is section/figure X? | `ttk outline f` (text, no image) | tiny |

`--region` fractions: `0,0,1,0.5` = top half; `0.5,0.5,1,1` = bottom-right quarter.

## Loop

1. **State the target** in one or two sentences (what it should look like; measurable where possible:
   "caption centered under figure, 6pt gap; arrows touch box edges; table fits text width").
2. **Smallest viable step.** Build the component in isolation with `ttk snippet` (figure files should be
   includable on their own: no `#set page` inside a figure file).
3. **Render and actually inspect** the PNG with Read. Check systematically, top-left to bottom-right:
   - text overflow / clipping / overfull lines, unintended hyphenation, widows
   - alignment and spacing consistency (equal gaps, baselines, margins)
   - figure details: arrow tips attach to anchors, labels don't collide with strokes, legible font sizes
     (≥ ~7pt at print size), consistent stroke widths, colors distinguishable
   - fonts: a fallback font in the render means the requested font is missing (the check also warns
     `unknown font family`) — `typst fonts` lists available ones
   - for templates: first page, a body page, a page with a figure/table, and the last page
4. **Fix one thing at a time**, re-render with `--compare` to confirm the change and catch regressions.
5. **Integrate** into the document, then `ttk render <entrypoint> -p <page>` (find the page with
   `ttk outline`) to verify it in context (width constraints, float placement, numbering).
6. **Report** what you verified visually and anything you could not (e.g. fonts not installed here).

Stop iterating when the stated target is met; don't polish blindly. If two attempts at the same visual
problem fail, re-read the relevant docs (`ttk docs show place`, `ttk pkg api cetz:… anchor`) instead of
nudging numbers.

## Figure & template tips

- Prefer relative/structural positioning (anchors, `grid`, `stack`, `align`, `fr` units) over hard-coded
  offsets; it survives content changes.
- Expose template knobs as named parameters with defaults (`#let tpl(title: none, accent: blue, body) = ...`),
  apply in the entrypoint with `#show: tpl.with(...)`.
- Keep colors/sizes in one `#let theme = (...)` dictionary imported by template and figures.
- For cetz: everything inside `canvas({ import draw: * ... })`; name elements (`name: "a"`) and connect
  anchors (`"a.east"`); check the pinned version's API with `ttk pkg api cetz:<ver> <fn>`.
- For data plots, check whether the project already uses a plotting package (`ttk pkg deps`) before adding one.
- Test templates with realistic stress content: long titles, many authors, `#lorem(400)`, wide tables,
  multi-line captions.
