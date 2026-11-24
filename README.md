# typst-toolkit

A Claude Code plugin that makes Claude reliable at Typst. It:

- looks up syntax in the official docs instead of guessing or falling back on LaTeX habits;
- reads package APIs from the exact version a project imports;
- compiles and lints after every edit;
- renders pages and figures and inspects them for visual work.

**Contents:** [Install](#install) · [Update](#update) · [Use](#use) · [Packages](#packages) ·
[Multi-file projects](#multi-file-projects) · [Commands](#commands) · [Develop](#develop) ·
[Troubleshooting](#troubleshooting)

---

## Install

**Prerequisites**

| Tool | Notes |
|---|---|
| Claude Code | CLI or VS Code extension |
| `python3` ≥ 3.11 | standard library only |
| `typst` | any install method (snap, cargo, release binary) |
| tinymist | `tinymist` on PATH, or the VS Code extension "Tinymist Typst" (found automatically) |

**Install from GitHub** (the `main` branch is the single source of truth; no clone needed):

```bash
claude plugin marketplace add SobhanNili/typst-toolkit
claude plugin install typst-toolkit@typst-toolkit
```

Then restart Claude Code. To check the setup, ask Claude to run `ttk doctor`. It should list typst, tinymist
and the docs mirror (built in the background on first start).

---

## Update

`/reload-plugins` does **not** fetch anything. It only reloads the copy already installed on your machine
(`~/.claude/plugins/cache/typst-toolkit/`). Getting a new version from GitHub takes these steps:

| Step | Who | Command |
|---|---|---|
| 1. Publish | maintainer | bump `version` in `.claude-plugin/plugin.json`, commit, push to `main` |
| 2. Fetch | each machine | `claude plugin marketplace update typst-toolkit` |
| 3. Install | each machine | `claude plugin update typst-toolkit@typst-toolkit` |
| 4. Load | each machine | `/reload-plugins` in running sessions, or restart Claude Code |

Always bump the version in step 1: it is how `claude plugin update` reliably sees a new release, and it
tells you which release each machine runs. Check the installed version with `claude plugin list`.

> **Switching from an old local-folder install?** Run `claude plugin marketplace remove typst-toolkit` first
> (both sources share the name), then the two install commands above.

---

## Use

Ask Claude for Typst work as usual. The plugin works in the background:

| Part | What it does |
|---|---|
| **Skill** | Loads for any Typst work. Tells Claude to look things up before writing them, never write LaTeX, compile after edits and inspect renders. Loads three references on demand: LaTeX→Typst table, visual-loop playbook, curated package list. |
| **After-edit hook** | Compiles the affected entrypoint, runs tinymist lint and scans for LaTeX-isms after every edit. Errors go straight back to Claude. |
| **Stop hook** | Claude can't finish with a broken build without fixing it or explaining why. |
| **Session-start hook** | Keeps an offline copy of typst.app/docs up to date (refreshed every 30 days). |
| **Language server** | tinymist gives Claude hover docs and go-to-definition, including inside packages. |
| **`ttk` CLI** | The commands behind all of this; on Claude's PATH (see [Commands](#commands)). |

Prompts that work well:

- *"Design a title page for the template; render it and iterate until it looks right."*
- *"Convert `paper.tex` to Typst; check every math command against the symbol table."*
- *"Upgrade cetz to the latest version; check what changed in the API before editing the figures."*
- *"The figure on page 4 has overlapping labels. Zoom in and fix it."*

**Examples** in this repo, each a working reference:

| Folder | Shows |
|---|---|
| `examples/report/` | multi-file document: template, chapters, cetz figure, bibliography |
| `examples/slides/` | touying deck (metropolis theme): reveals, animated cetz, math, speaker notes |
| `examples/verify/` | compiles every construct the LaTeX→Typst reference recommends |

---

## Packages

### How Claude gets a package's API right

Package APIs change faster than Typst itself (cetz and touying both had breaking releases recently), so
Claude never uses them from memory:

1. **Version from the project.** The version in the project's `#import "@preview/name:x.y.z"` is the one
   used everywhere. The latest version is only used for new imports.
2. **Docs from the package source.** ttk reads the package from typst's own cache (downloading it if
   needed): `pkg readme` for usage, `pkg api <symbol>` for exact signatures and doc comments, `pkg grep` for
   examples, `pkg docs` for the full generated reference.
3. **Language server.** Hover in a file that imports the package shows that version's docs.
4. **Online manuals** (e.g. cetz, touying) are read when the README is thin. The local source wins if they
   disagree, since manuals often describe only the latest version.
5. **Compiler and renders.** Wrong parameters fail at compile time; layout problems show in the render.

### Curated package list

So Claude uses an existing package instead of building everything by hand,
[`skills/typst/references/packages.md`](skills/typst/references/packages.md) lists the recommended packages
per task:

| Task | Packages |
|---|---|
| Figures and diagrams | `cetz`, `fletcher`, `diagraph`, `neural-netz` |
| Plots | `lilaq`, `cetz-plot` |
| Algorithms and code | `algorithmic`, `lovelace`, `codly` |
| Math and scientific writing | `physica`, `unify` / `zero`, `equate`, `numera`, `theorion` / `ctheorems`, `subpar` |
| Slides and posters | `touying`, `peace-of-posters` |

It also lists domain-specific packages (circuits, chemistry, quantum, automata, paper templates) and some
to avoid. The list has no version numbers, so it doesn't go stale. Edit that file to change the selection.

---

## Multi-file projects

- **Entrypoints are found automatically** from the include/import graph. An edited chapter is always compiled
  through its main file, so there are no false "unknown label" errors.
- **Use relative paths** (`#include "../figures/a.typ"`). Paths starting with `/` depend on the compile
  root, which VS Code's tinymist and the CLI may choose differently. `ttk check` warns when this can happen.
- **Fonts:** for documents that must also look right on typst.app, put font files in the project
  (e.g. `fonts/`) and list that folder under `font-paths` (see below).
- **Optional `typst-toolkit.toml`** at the project root, when the automatic guess is wrong:

```toml
main = ["main.typ"]      # entrypoint(s)
root = "."               # compile root, for "/..." paths
font-paths = ["fonts"]
ppi = 110                # default render resolution
[inputs]                 # sys.inputs
draft = "true"
```

---

## Commands

Claude runs these itself; they are listed here for reference and for your own use. From your shell, run
`bin/ttk` inside a clone of this repo.

```bash
# Official docs (offline mirror of typst.app/docs)
ttk docs show grid                 # a page;  -s font for one parameter;  --outline for headings
ttk docs search 'first-line-indent'
ttk docs sym '\leq'                # LaTeX command / Typst name / Unicode words → symbol
ttk docs sync                      # refresh the mirror

# Packages
ttk pkg search diagram arrows
ttk pkg info touying               # versions, minimum compiler, links
ttk pkg readme cetz:0.5.2
ttk pkg api cetz:0.5.2 content     # signature + doc comments from source
ttk pkg grep touying:0.8.0 'config-info'
ttk pkg docs touying:0.8.0         # full API reference → .md file
ttk pkg deps .                     # project imports: cached? outdated? mixed versions?

# Checking and rendering  (output goes to <project>/.typst-preview/, git-ignored)
ttk check [file|dir]               # compile + lint + LaTeX scan
ttk project                        # entrypoints and include/import tree
ttk outline main.typ               # headings, figures, labels with page numbers
ttk render main.typ -p 2           # page → PNG
ttk render main.typ --sheet        # all pages on one image
ttk render main.typ -p 2 --compare # before / after
ttk render main.typ -p 2 --region 0,0.5,1,1   # zoomed crop (page fractions)
ttk snippet figures/arch.typ       # one figure on an auto-sized page
ttk snippet -e '#table(columns: 2, [a], [b])'
```

---

## Develop

Changes are made in a local clone, tested locally, then pushed to `main` and installed on each machine as in
[Update](#update).

```bash
git clone https://github.com/SobhanNili/typst-toolkit ~/typst-toolkit
```

### Test locally before pushing

Pick the lightest level that covers the change:

**1. The CLI only.** For changes in `skills/typst/scripts/`:

```bash
~/typst-toolkit/bin/ttk check path/to/project
echo '{"tool_name":"Edit","tool_input":{"file_path":"/abs/path/main.typ"},"session_id":"t"}' \
  | ~/typst-toolkit/bin/ttk hook post          # simulate the after-edit hook
```

**2. The whole plugin from your clone.** For changes to the skill, references or hooks. Nothing is
installed; edits apply after `/reload-plugins`:

```bash
claude plugin disable typst-toolkit@typst-toolkit    # avoid running two copies
cd ~/some-typst-project && claude --plugin-dir ~/typst-toolkit
claude plugin enable typst-toolkit@typst-toolkit     # when done
```

**3. The install itself.** For changes to `plugin.json`, `marketplace.json`, `hooks.json` or `.lsp.json`.
Install from the clone (uncommitted changes included), then switch back to GitHub:

```bash
claude plugin marketplace remove typst-toolkit
claude plugin marketplace add ~/typst-toolkit && claude plugin install typst-toolkit@typst-toolkit
# ...test in a restarted session, then:
claude plugin marketplace remove typst-toolkit
claude plugin marketplace add SobhanNili/typst-toolkit && claude plugin install typst-toolkit@typst-toolkit
```

### Release checklist

1. When the toolkit misbehaves elsewhere, record it with a minimal reproduction:
   `gh issue create -R SobhanNili/typst-toolkit`.
2. Fix it in the clone; add the reproduction under `examples/verify/`.
3. Check:
   ```bash
   claude plugin validate .
   bin/ttk check examples/report && bin/ttk check examples/slides && bin/ttk check examples/verify
   ```
4. Bump `version` in `.claude-plugin/plugin.json`, commit, push to `main`.
5. On each machine: steps 2–4 of [Update](#update).

After upgrading typst itself: `ttk docs sync`, then `ttk check examples/verify`.

### Repository layout

```
.claude-plugin/        plugin.json, marketplace.json, icon
.lsp.json              tinymist language server
hooks/hooks.json       after-edit, stop and session-start hooks
bin/                   ttk and ttk-tinymist wrappers
skills/typst/          SKILL.md, references/, scripts/ (the ttk implementation)
examples/              report, slides, verify, icon
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| A change on GitHub isn't active | `/reload-plugins` doesn't fetch. Run steps 2–4 of [Update](#update), and check that the version was bumped. |
| Hooks don't run | Plugin not enabled or Claude Code not restarted. Check `claude plugin list`. |
| VS Code says `file not found` but `ttk check` passes | A `/...` path resolved against a different root. Use relative paths. |
| `input file not found` for a project in `/tmp` or `/mnt/...` | Snap-installed typst can't read there. ttk falls back to tinymist automatically. |
| `unknown font family` | Font not installed. Check `typst fonts`, or add a `font-paths` folder in `typst-toolkit.toml`. |
| `docs mirror not found` | Run `ttk docs sync`, or wait for the background sync (log: `~/.cache/typst-toolkit/sync.log`). |
| Wrong entrypoint | Set `main = [...]` in `typst-toolkit.toml`. |

Tool lookup, if something isn't found: typst from `$TTK_TYPST` or PATH; tinymist from `$TTK_TINYMIST`, PATH,
or the newest VS Code extension; cache in `~/.cache/typst-toolkit` (override with `$TTK_CACHE`).
