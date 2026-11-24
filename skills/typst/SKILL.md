---
name: typst
description: Use for ANY work on Typst documents (.typ files, typst.toml, typst-toolkit.toml) — writing or editing content, math, tables, bibliographies, multi-file projects, templates, figures/diagrams (cetz, fletcher, etc.), using or choosing Typst Universe packages, fixing compile errors, or converting LaTeX to Typst. Provides offline official docs, package API lookup, compile/lint checks and a render-and-look visual feedback loop via the `ttk` CLI.
---

# Typst work, grounded

Typst is NOT LaTeX, and your memory of Typst is version-skewed (syntax and symbol names changed across
0.11–0.15). Ground every non-trivial construct in the docs or the package source, verify with the compiler,
and verify visual work by looking at renders. `ttk` (on PATH via this plugin; else
`${CLAUDE_SKILL_DIR}/scripts/ttk`) does all of it.

## Non-negotiables

1. **Don't guess syntax or parameter names.** Before using a function/parameter you are not certain about in
   *this* Typst version: `ttk docs show <name> [-s <param>]`. For a package symbol: `ttk pkg api <pkg:ver> <symbol>`.
2. **Never write LaTeX in .typ files** (`\textbf`, `\frac`, `\section`, `$$`, `x^{2}`, `%` comments, `\\`).
   Many of these compile *silently* and render garbage. Math symbol names: `ttk docs sym '\leq'` → `lt.eq`.
   Read `references/latex-to-typst.md` once per session if you are converting or writing math-heavy content.
3. **Compile after edits.** A PostToolUse hook compiles the affected entrypoint(s) automatically and reports
   errors / new warnings / LaTeX-isms. Treat its output as ground truth; fix errors before moving on. Run
   `ttk check <file>` yourself after multi-file refactors. A Stop hook blocks finishing with a broken build.
4. **Look at the output for anything visual** (templates, figures, tables, layout, page breaks, styling):
   `ttk render` / `ttk snippet`, then Read the PNG. Compiling ≠ looking right. See `references/visual-loop.md`.
5. **Pin package versions** exactly as the project does (`@preview/cetz:0.3.4`). APIs differ between
   versions — always read the docs/source of the version actually imported (`ttk pkg deps`).

## Command reference

| Need | Command |
|---|---|
| Toolchain status | `ttk doctor` |
| Official docs page / one parameter / headings only | `ttk docs show grid` · `ttk docs show text -s font` · `ttk docs show page --outline` |
| Search all docs (regex) | `ttk docs search 'first-line-indent'` · `--within guides` · `--files` |
| Symbol by Typst name, LaTeX cmd or Unicode words | `ttk docs sym '\mathbb'` · `ttk docs sym arrow` |
| Guides worth knowing | `ttk docs show for-latex-users` · `page-setup` · `tables` · `reference/styling` · `reference/context` |
| Mirror dir (grep/Read freely) | `ttk docs path` (refresh: `ttk docs sync`; one page live: `ttk docs fetch <url>`) |
| Find packages | `ttk pkg search diagram arrows` |
| Package overview (versions, links, exports, files) | `ttk pkg info cetz:0.3.4` |
| README / signature+doc comments / grep source | `ttk pkg readme X` · `ttk pkg api X <symbol>` · `ttk pkg grep X '<regex>'` |
| Full generated API docs (tinymist) | `ttk pkg docs X` → writes a .md you grep/Read |
| Project packages: cached? outdated? mixed versions? | `ttk pkg deps [dir]` |
| Project map: root, entrypoints, include/import tree | `ttk project [path]` |
| Compile + tinymist lint + LaTeX scan | `ttk check [file-or-dir] [--main m.typ]` |
| Headings/figures/labels with page numbers | `ttk outline <file>` (or `--expr '<typst query>'`) |
| Render pages → PNG | `ttk render <file> [-p 3-4] [--ppi 110]` |
| Many pages at a glance / before-after | `ttk render <file> --sheet` · `ttk render <file> -p 2 --compare` |
| Zoom into a region (fine detail) | `ttk render <file> -p 2 --region 0,0.5,1,1` (fractions x0,y0,x1,y1) |
| Iterate on one figure / code fragment | `ttk snippet figures/arch.typ` · `ttk snippet -e '#table(...)'` |

Outputs go to `<root>/.typst-preview/` (self-gitignored). Package specs accept `cetz`, `cetz:0.3.4`,
`@preview/cetz:0.3.4`; without a version, the latest is used — prefer the project's pinned one.

## Workflows

**Before writing Typst you're unsure about** → `ttk docs show <fn>` (parameters, types, defaults, examples).
Set/show rules, `context`, introspection and counters are the usual traps — read
`ttk docs show reference/styling` and `reference/context` before writing non-trivial show rules.

**Multi-file projects**
1. `ttk project` first: it shows the entrypoint(s) and which files are `include`d/`import`ed.
   Included files are compiled only through their entrypoint — never "fix" errors by compiling a chapter alone.
2. Path rules: `"x.typ"` is relative to the *current file*; `"/x.typ"` is relative to the project root
   (`--root`). Files outside the root can't be read. `import` brings definitions; `include` inserts content.
   **Write relative paths** (`"../figures/a.typ"`). Root-absolute paths break whenever a tool picks a
   different root (tinymist in VS Code uses the workspace folder). `ttk check` warns when this can happen.
3. Show/set rules in an included file don't leak back into the parent; put global styling in the template
   (`#show: template.with(...)`) applied in the entrypoint.
4. If entrypoints are ambiguous (several unreferenced .typ files), create `typst-toolkit.toml` at the root:
   `main = ["main.typ"]` (also supports `root`, `font-paths`, `ppi`, `[inputs]`).

**Using a package**
1. `ttk pkg search` → `ttk pkg info name` (check `compiler` min version vs `ttk doctor`).
2. Read `ttk pkg readme name:ver` for idioms, then `ttk pkg api name:ver <symbol>` for exact parameters
   (or LSP hover on the symbol in a file that imports it: same doc comments, resolved for the pinned version).
   For large packages, `ttk pkg docs` writes the full API to a file: grep it, don't Read it whole.
   Big packages ship a manual elsewhere: `info` prints `homepage`/`repository`; fetch those pages when the
   README is thin (e.g. cetz → cetz-package.github.io). Never rely on remembered APIs of cetz/fletcher/etc.
   — they changed a lot between versions.
3. Write a minimal snippet first (`ttk snippet -e '#import "@preview/x:v": *  ...'`), confirm it renders,
   then integrate.

**Templates & figures (visual work)** → follow `references/visual-loop.md`: build in small steps, render
after each meaningful change, inspect at the right zoom, compare before/after, and state what you checked.

**Errors you can't resolve quickly** → read the hint lines in the diagnostic; search the docs for the
message (`ttk docs search '<key phrase>'`); check the changelog for renames (`ttk docs search <name>
--within changelog`); minimize to a snippet and bisect.

## Typst essentials (0.15) — quick self-check

- Modes: markup (default), code after `#` (`#let`, `#set`, `#show`, calls), math in `$...$` (`$ x $` with
  spaces = display block). In code blocks `{ }` no `#` needed; content blocks are `[ ]`.
- Style with `#set fn(param: v)`; transform with `#show sel: it => ...` or `#show sel: set fn(...)`.
  A `set` inside `{ }`/`[ ]` only affects that block (lint warns "doesn't take effect").
- Anything that reads document state (`counter(..).get()/display()`, `query`, `here()`, `measure`) must be
  inside `context`.
- Labels `<intro>` after an element; references `@intro`; citations `@key` / `#cite(<key>)` with `#bibliography("refs.bib")`.
- Lengths need units (`12pt`, `1cm`, `1em`, `1fr`, `50%`). Colors: `red`, `rgb("#1f77b4")`, `luma(230)`, `color.mix`.
- Function args: named `f(x, size: 2pt)`; trailing content block `f(..)[body]`; spread `..args`.
