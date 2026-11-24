# typst-toolkit

A Claude Code plugin that makes Claude reliable at Typst. It:

- grounds syntax in the official docs instead of memory or LaTeX habits;
- reads package APIs from the exact version a project imports;
- checks every edit with the compiler and tinymist's linter;
- verifies visual work by rendering it and looking at the result.

---

## 1. Setup

### Prerequisites

| Tool | Needed for | Notes |
|---|---|---|
| Claude Code | everything | CLI or the VS Code extension |
| `python3` ≥ 3.11 | the `ttk` CLI and hooks | standard library only, nothing to `pip install` |
| `typst` CLI | compiling, rendering, `ttk outline` | snap, cargo, or a release binary all work |
| tinymist | lint, package docs, language server, fallback compiler | a `tinymist` on PATH **or** the VS Code extension "Tinymist Typst" (its bundled binary is found automatically) |

Network access is used only for `typst.app` (docs mirror) and `packages.typst.org` (package index and downloads).

### Install from the git repository

```bash
# 1. Get the code
git clone <repo-url> ~/typst-toolkit        # or use your existing checkout

# 2. Register the repo as a local plugin marketplace, then install the plugin from it
claude plugin marketplace add ~/typst-toolkit
claude plugin install typst-toolkit@typst-toolkit

# 3. Restart Claude Code (or run /reload-plugins inside a session)

# 4. Verify
~/typst-toolkit/bin/ttk doctor
~/typst-toolkit/bin/ttk docs sync           # optional; the SessionStart hook does it in the background
```

If the repo is hosted on GitHub, `claude plugin marketplace add <owner>/<repo>` also works without cloning.
To update after pulling new commits, run `claude plugin update typst-toolkit@typst-toolkit` and restart.

`ttk doctor` should show something like:

```
typst:    /snap/bin/typst  0.15.1
tinymist: ~/.vscode-server/extensions/myriad-dreamin.tinymist-0.15.12-linux-x64/out/tinymist  (bundles typst 0.15.1)
packages: data ~/.local/share/typst/packages | cache ~/.cache/typst/packages
docs mirror: ~/.cache/typst-toolkit/docs/0.15.1 | version 0.15.1 | 218 pages | 0 days old
```

### How the tools are found

- **typst:** `$TTK_TYPST`, otherwise `typst` on PATH. A snap-confined typst can only read non-hidden
  paths under `$HOME`. For projects elsewhere (`/tmp`, `/mnt/c/...`), ttk switches to tinymist
  automatically, since tinymist bundles the same compiler.
- **tinymist:** `$TTK_TINYMIST`, then `tinymist` on PATH, then the newest VS Code/Cursor extension bundle.
  This keeps working when the extension updates.
- **Cache:** `~/.cache/typst-toolkit`. It holds the docs mirror (about 2 MB), the package index,
  generated package docs and hook state. Override it with `$TTK_CACHE`.

---

## 2. What you get

| Component | What it does |
|---|---|
| **Skill** `typst` | The workflow Claude follows for Typst work. It loads automatically when Claude touches `.typ` files or you ask about Typst. Two references load on demand: a LaTeX→Typst table, and the visual-loop playbook. |
| **`ttk` CLI** | On Claude's PATH while the plugin is enabled. You can run it yourself at `~/typst-toolkit/bin/ttk`. |
| **PostToolUse hook** | After any Edit or Write to a Typst project (`.typ`, `.bib`, data files), it compiles the affected **entrypoint**, runs tinymist lint, and scans the edited file for LaTeX-isms. Errors go back to Claude straight away; warnings only when they change, to avoid noise. |
| **Stop hook** | Claude can't finish with a broken build in any project it edited. It blocks once, so Claude must either fix the build or explain why it's left broken. |
| **SessionStart hook** | Creates or refreshes the offline docs mirror in the background (at most 30 days old). |
| **LSP server** | tinymist as Claude's Typst language server: hover docs, go-to-definition and references, including inside packages. |

---

## 3. Using it

You mostly don't call anything yourself. Ask Claude for Typst work as usual ("add a results chapter",
"make this table match the template", "draw the pipeline with cetz"). The skill makes Claude:

1. look up anything it's unsure of in the docs or the package source before writing it;
2. let the hook compile after each edit, and fix what comes back;
3. render and inspect pages or figures for anything visual, iterating until the stated goal is met.

Prompts that work well:

- *"Design a title page for the template; render it and iterate until it looks right."*
- *"Convert `paper.tex` to Typst; check every math command against the symbol table."*
- *"Upgrade cetz to the latest version; check what changed in the API before editing the figures."*
- *"The figure on page 4 has overlapping labels — zoom in and fix it."*

### `ttk` command reference

```bash
# Official docs (local mirror of typst.app/docs, matched to the latest Typst release)
ttk docs show grid                 # whole page
ttk docs show text -s font         # one parameter/section
ttk docs show page --outline       # headings only
ttk docs search 'first-line-indent' [--within guides] [--files]
ttk docs sym '\leq'                # LaTeX command / Typst name / Unicode words → symbol
ttk docs show for-latex-users      # official migration guide
ttk docs sync | status | path | fetch <url>

# Packages (Typst Universe)
ttk pkg search slides presentation
ttk pkg info touying               # versions, compiler min, repo/homepage, exports, local path
ttk pkg readme cetz:0.3.4
ttk pkg api cetz:0.3.4 rect        # signature + doc comments from source
ttk pkg grep touying:0.8.0 'config-info'
ttk pkg docs touying:0.8.0         # full generated API docs (tinymist) → a .md file to grep
ttk pkg deps .                     # imports in this project: cached? outdated? mixed versions?

# Project, checking, rendering
ttk project [path]                 # root, entrypoints, include/import tree, packages
ttk check [file|dir] [--main m.typ] [--no-lint] [--no-latex]
ttk outline main.typ               # headings/figures/labels with page numbers
ttk render main.typ [-p 2-3] [--ppi 110]
ttk render main.typ --sheet        # contact sheet of all pages
ttk render main.typ -p 2 --compare # before/after vs the previous render
ttk render main.typ -p 2 --region 0,0.5,1,1   # zoomed crop (x0,y0,x1,y1 as page fractions)
ttk snippet figures/arch.typ       # one figure on an auto-sized page
ttk snippet -e '#table(columns: 2, [a], [b])'
ttk latex-scan chapters/*.typ
```

Renders go to `<project root>/.typst-preview/`, which contains its own `.gitignore`.

---

## 4. Third-party packages (touying, cetz, fletcher, …)

Claude's memory of package APIs is the least reliable thing of all, because these packages change faster
than Typst itself. cetz 0.2 → 0.3 → 0.4 and touying 0.5 → 0.8 all had breaking changes. So the toolkit
never lets Claude rely on memory. Here's how a package's syntax and docs are determined:

1. **The version comes from the project.** `ttk pkg deps` / `ttk project` read the
   `#import "@preview/name:x.y.z"` lines. Everything below uses that exact version; the latest is used
   only for new imports. `ttk pkg info` also shows the package's minimum `compiler` version and the
   newer versions available.
2. **The source is local.** Packages live in typst's package cache (`~/.cache/typst/packages/preview/<name>/<ver>`),
   and ttk downloads them there if needed, the same place typst itself uses. That gives Claude:
   - `pkg readme`: the author's usage guide and idioms for that version;
   - `pkg api <symbol>`: the real `#let` definition, with parameter names, defaults and `///` doc comments;
   - `pkg grep`: examples, themes, internals (e.g. how a touying theme builds its title slide);
   - `pkg docs`: tinymist's full generated API reference (types, defaults, docs for every public symbol).
3. **Hover/definition via the LSP.** In a file that imports the package, tinymist resolves symbols against
   the pinned version. Hovering `canvas` shows cetz 0.3.4's signature and parameter docs.
4. **External manuals.** Some packages keep their main docs outside the package (cetz: cetz-package.github.io;
   touying: touying-typ.github.io; many ship a `manual.pdf` in their repo). `pkg info` prints the
   `homepage`/`repository` links and Claude fetches those pages when the README is thin. These are often
   written for the *latest* version, so the local source stays the source of truth when they disagree.
5. **The compiler is the final check.** Wrong parameter names fail immediately ("unexpected argument"),
   the hook reports them, and the visual loop catches anything that compiles but looks wrong.
   The skill also has Claude prototype new package usage in a `ttk snippet` before adding it to the document.

Local packages (`@local/...`, in `~/.local/share/typst/packages`) work the same way, without the download.

---

### Example: the slides deck

`examples/slides/` was built with exactly this workflow and is a good template for decks:

- `touying:0.8.0` with the metropolis theme; it needs Typst ≥ 0.15 (`ttk pkg info touying` shows the `compiler` field).
- The README showed that 0.8 animates cetz through `touying-reduce.with(cetz)` (the old `touying-reducer`
  API changed), and that it pairs with `cetz:0.5.2`. Theme options came from `ttk pkg api touying:0.8.0 metropolis-theme`.
- `figures/architecture.typ` is a static cetz figure that sizes its boxes from their labels.
  The first render showed the labels overflowing fixed-size boxes; that was fixed with `content(..., frame: "rect")`
  after checking `ttk pkg api cetz:0.5.2 content`, and then sized on the slide with `--compare` renders.
- Every animation step is a separate PDF page. Use `ttk render examples/slides/main.typ --sheet` to see the
  whole deck at once, then `-p N` for individual slides.

## 5. Multi-file projects

- **Entrypoints** are inferred from the include/import graph (`.typ` files nobody references). `typst.toml`
  template and package entrypoints are also recognised. Edits to a chapter are checked **through its
  entrypoint**, so you never get false "unknown label" errors from compiling a chapter alone.
- **Use relative paths** (`#include "../figures/a.typ"`). A path starting with `/` is relative to the
  compile root, and tools choose that root differently: ttk uses the folder with `typst-toolkit.toml` or
  `typst.toml`, while tinymist in VS Code uses the workspace folder. `ttk check` warns when root-absolute
  paths could resolve differently in your editor. If you want `/` paths, make the roots agree (open the
  project folder itself in VS Code, or set tinymist's `rootPath`).
- **Optional config** `typst-toolkit.toml` at the project root, for when the guess is ambiguous:

```toml
main = ["main.typ"]          # one or more entrypoints
root = "."                   # compiler --root (for "/..." paths)
font-paths = ["fonts"]
ppi = 110                    # default render resolution
[inputs]                     # sys.inputs
draft = "true"
```

---

## 6. Repository layout

```
.claude-plugin/{plugin,marketplace}.json, icon.png
.lsp.json                         tinymist language server registration
hooks/hooks.json                  PostToolUse / Stop / SessionStart
bin/ttk, bin/ttk-tinymist         wrappers (on Claude's PATH)
skills/typst/SKILL.md             workflow + command reference
skills/typst/references/          latex-to-typst.md, visual-loop.md
skills/typst/scripts/             ttk + ttk_{common,docs,pkg,build,hooks}.py
examples/report/                  multi-file demo: template, chapters, cetz figure, bibliography
examples/slides/                  touying 0.8 deck (metropolis theme): reveals, animated cetz, math, notes
examples/verify/                  compiles every construct the LaTeX→Typst reference recommends
examples/icon/                    source of the plugin icon
```

### Maintenance

- After upgrading typst, run `ttk docs sync`, then `ttk check examples/verify/cheatsheet-test.typ`.
  If something in the reference was renamed, this fails.
- After editing the plugin, run `claude plugin validate ~/typst-toolkit`.

## 7. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `input file not found` from typst for a project in `/tmp` or `/mnt/...` | Snap confinement. ttk falls back to tinymist automatically; for your own shell use a non-snap typst. |
| VS Code shows `file not found (searched at <workspace>/...)` but `ttk check` passes | A root-absolute `"/..."` path with a different editor root. Use relative paths (see §5). |
| `unknown font family` warning | The font isn't installed. Check `typst fonts`; add a `font-paths` entry in `typst-toolkit.toml`. |
| Hook didn't run | The plugin must be enabled and Claude Code restarted (`/reload-plugins`). |
| `docs mirror not found` | `ttk docs sync`, or wait for the SessionStart background sync (log: `~/.cache/typst-toolkit/sync.log`). |
| Wrong entrypoint picked | Add `main = [...]` to `typst-toolkit.toml`. |
