"""Project analysis, compile checks, rendering and visual inspection helpers."""
from __future__ import annotations

import json
import re
import shutil
import sys
import time
from pathlib import Path

from ttk_common import (Project, compile_doc, die, find_project_root, find_tinymist, format_diag, parse_diagnostics,
                        pick_compiler, run)


# --------------------------------------------------------------------------- LaTeX-ism scanner

LATEX_CMDS = (r"textbf|textit|texttt|emph|underline|section|subsection|subsubsection|chapter|paragraph|begin|end|"
              r"item|cite|citep|citet|ref|eqref|label|usepackage|documentclass|includegraphics|caption|centering|"
              r"hline|newpage|clearpage|vspace|hspace|footnote|url|href|newcommand|renewcommand|maketitle|"
              r"tableofcontents|noindent|small|large|Large|bf|it|tt|item")
MATH_HINTS = {
    "frac": "a/b or frac(a, b)", "sqrt": "sqrt(x)", "mathbb": "RR, NN, ZZ, QQ, CC or bb(X)", "mathcal": "cal(X)",
    "mathbf": "bold(x)", "mathrm": "upright(x)", "text": '"text" in quotes', "left": "lr(...) or nothing (auto-scaling)",
    "right": "lr(...)", "cdot": "dot.op or dot", "times": "times", "leq": "<= or lt.eq", "geq": ">= or gt.eq",
    "neq": "!= or eq.not", "infty": "infinity or oo", "partial": "partial", "nabla": "nabla", "ldots": "...",
    "cdots": "dots.c", "qquad": "wide", "quad": "quad", "dd": "dif", "mathrm{d}": "dif", "sum": "sum_(i=1)^n", "int": "integral", "prod": "product", "to": "-> or arrow.r",
    "rightarrow": "->", "Rightarrow": "=>", "hat": "hat(x)", "bar": "overline(x) or macron(x)", "vec": "arrow(x)",
    "operatorname": 'op("name")', "begin": "mat(...), cases(...), or & alignment",
}


def _symmap() -> dict:
    try:
        from ttk_docs import latex_symbol_map
        return latex_symbol_map()
    except Exception:  # noqa: BLE001
        return {}


def scan_latex(path: Path) -> list[str]:
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return []
    # blank out raw blocks/inline raw and comments, keep line numbers
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    t = re.sub(r"```.*?```", blank, text, flags=re.S)
    t = re.sub(r"`[^`\n]*`", blank, t)
    t = re.sub(r"/\*.*?\*/", blank, t, flags=re.S)
    t = re.sub(r"(?m)(^|[^:\\])//.*$", lambda m: m.group(1) + " " * (len(m.group(0)) - len(m.group(1))), t)
    t = re.sub(r'"(?:[^"\\\n]|\\.)*"', blank, t)  # string literals
    issues = []
    symmap = None
    math_spans = [(m.start(), m.end()) for m in re.finditer(r"\$[^$]*\$", t, flags=re.S)]

    def in_math(pos):
        return any(a <= pos < b for a, b in math_spans)

    def lineno(pos):
        return t.count("\n", 0, pos) + 1

    for m in re.finditer(r"\\([A-Za-z]{2,})", t):
        cmd = m.group(1)
        ln = lineno(m.start())
        if in_math(m.start()):
            hint = MATH_HINTS.get(cmd)
            if not hint:
                if symmap is None:
                    symmap = _symmap()
                names = symmap.get(cmd)
                hint = (" or ".join(names[:3]) + " (from the official symbol table)") if names else \
                    f"no direct symbol; check `ttk docs sym {cmd}` / `ttk docs search {cmd}`"
            issues.append(f"line {ln}: LaTeX math `\\{cmd}` → Typst: {hint}")
        elif re.fullmatch(LATEX_CMDS, cmd):
            issues.append(f"line {ln}: LaTeX command `\\{cmd}` renders as literal text. "
                          "Typst: *bold*, _emph_, = Heading, - item, @label, <label>, #image(), #figure(), #pagebreak()")
        else:
            issues.append(f"line {ln}: `\\{cmd}` in markup only escapes the next char (prints '{cmd}')")
    for m in re.finditer(r"\$\$", t):
        issues.append(f"line {lineno(m.start())}: `$$` — Typst display math is `$ x $` (spaces inside), not `$$`")
    for m in re.finditer(r"[_^]\{", t):
        if in_math(m.start()):
            issues.append(f"line {lineno(m.start())}: `{m.group(0)}` — Typst groups with parentheses: x^(2n), "
                          "braces render literally")
    for m in re.finditer(r"(?m)^\s*%(?!\s*\d)", t):
        issues.append(f"line {lineno(m.start())}: `%` comment — Typst comments are `//` or `/* */`")
    for m in re.finditer(r"``|''", t):
        issues.append(f"line {lineno(m.start())}: LaTeX quotes — just type \"...\" (smart quotes are automatic)")
    for m in re.finditer(r"\\\\\s*$", t, flags=re.M):
        issues.append(f"line {lineno(m.start())}: `\\\\` prints a backslash — a Typst line break is a single `\\`")
    seen, out = set(), []
    for i in issues:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


# --------------------------------------------------------------------------- lint

def lint(proj: Project, main: Path) -> list[dict]:
    tiny = find_tinymist()
    if not tiny:
        return []
    rc, so, se = run([tiny, "lint", "--root", str(proj.compile_root), str(main)], cwd=proj.compile_root, timeout=60)
    diags = [d for d in parse_diagnostics(se + "\n" + so) if d["severity"] == "warning"]
    for d in diags:
        d["lint"] = True
    return diags


# --------------------------------------------------------------------------- check

def check(target: Path, mains_override: list[str] | None = None, do_lint: bool = True, latex: bool = True,
          max_diags: int = 12) -> tuple[bool, str, dict]:
    root = find_project_root(target)
    proj = Project(root)
    if mains_override:
        mains = [Path(m).resolve() for m in mains_override]
    else:
        mains = proj.mains_for(target)
    if not mains:
        return True, f"no .typ entrypoint found under {root}", {}
    lines, all_ok, stats = [], True, {"errors": 0, "warnings": 0, "mains": [proj.rel(m) for m in mains]}
    for main in mains:
        t0 = time.time()
        ok, diags, kind = compile_doc(proj, main, str(proj.preview_dir() / f"{main.stem}.pdf"), fmt="pdf")
        if do_lint:
            seen = {(d["message"], d["file"], d["line"]) for d in diags}
            diags += [d for d in lint(proj, main) if (d["message"], d["file"], d["line"]) not in seen]
        errs = [d for d in diags if d["severity"] == "error"]
        warns = [d for d in diags if d["severity"] == "warning"]
        stats["errors"] += len(errs)
        stats["warnings"] += len(warns)
        all_ok &= ok
        status = "OK" if ok and not warns else ("OK with warnings" if ok else "FAILED")
        lines.append(f"── {proj.rel(main)}: {status} ({len(errs)} errors, {len(warns)} warnings, "
                     f"{time.time() - t0:.1f}s, {kind})")
        for d in (errs + warns)[:max_diags]:
            lines.append(format_diag(d, proj.compile_root) + (" [tinymist lint]" if d.get("lint") else ""))
        if len(errs) + len(warns) > max_diags:
            lines.append(f"... {len(errs) + len(warns) - max_diags} more diagnostics")
    warn = root_mismatch_warning(proj)
    if warn:
        lines.append(warn)
        stats["warnings"] += 1
    if latex and target.suffix == ".typ" and target.exists():
        issues = scan_latex(target)
        if issues:
            stats["latex"] = len(issues)
            lines.append(f"── LaTeX-isms in {proj.rel(target)} (these compile silently but render wrong):")
            lines += ["  " + i for i in issues[:10]]
    return all_ok, "\n".join(lines), stats


def root_mismatch_warning(proj: Project) -> str | None:
    """Root-absolute paths ("/x.typ") resolve against --root, which editors choose differently
    (tinymist in VS Code defaults to the workspace folder). Warn when that can diverge."""
    ws = next((d for d in [proj.compile_root, *proj.compile_root.parents] if (d / ".git").exists()), None)
    if ws is None or ws == proj.compile_root:
        return None
    hits = []
    for f in proj.typ_files():
        try:
            text = f.read_text(errors="replace")
        except OSError:
            continue
        for kind, ref in Project.DEP_RE.findall(text):
            if ref.startswith("/"):
                hits.append(f"{proj.rel(f)}: {kind} \"{ref}\"")
    if not hits:
        return None
    return ("── warning: root-absolute paths depend on the compile root. ttk uses "
            f"{proj.compile_root}, but an editor opened at {ws} (tinymist's default root) resolves them "
            f"there and fails. Prefer relative paths, or set tinymist's rootPath. Found: "
            + "; ".join(hits[:5]) + (" ..." if len(hits) > 5 else ""))


def cmd_check(args):
    target = Path(args.path or ".").resolve()
    if target.is_dir():
        target_for_root = target
        proj = Project(find_project_root(target))
        mains = args.main or [str(m) for m in proj.mains()[:6]]
        ok, text, _ = check(target_for_root, mains, not args.no_lint, False)
    else:
        ok, text, _ = check(target, args.main, not args.no_lint, not args.no_latex)
    print(text)
    sys.exit(0 if ok else 1)


# --------------------------------------------------------------------------- project overview

def cmd_project(args):
    root = find_project_root(Path(args.path or ".").resolve())
    proj = Project(root)
    print(f"project root: {root}")
    print(f"compile --root: {proj.compile_root}")
    print(f"config: {'typst-toolkit.toml' if proj.cfg else '(none; heuristics)'}")
    kind, exe = pick_compiler(proj.compile_root)
    print(f"compiler: {kind} ({exe})")
    mains = proj.mains()
    print(f"entrypoints: {', '.join(proj.rel(m) for m in mains) or '-'}")
    g = proj.graph()
    printed = set()

    def tree(f: Path, depth: int):
        for kindd, dep in g.get(f, []):
            mark = "" if dep.exists() else "  (MISSING)"
            print("  " * depth + f"└ {kindd}: {proj.rel(dep)}{mark}")
            if dep in g and dep not in printed and depth < 8:
                printed.add(dep)
                tree(dep, depth + 1)

    for m in mains[:10]:
        print(f"\n{proj.rel(m)}")
        printed.add(m)
        tree(m, 1)
    orphans = [f for f in g if f not in printed and f not in mains]
    if orphans:
        print(f"\nother .typ files not reached from entrypoints: {', '.join(proj.rel(o) for o in orphans[:20])}")
    pkgs = set()
    for f in g:
        pkgs.update(re.findall(r'"(@[\w-]+/[\w-]+:[\w.\-+]+)"', f.read_text(errors="replace")))
    if pkgs:
        print(f"\npackages: {', '.join(sorted(pkgs))}")


# --------------------------------------------------------------------------- render

def page_files(d: Path, stem: str) -> list[Path]:
    return sorted(d.glob(f"{stem}-p*.png"), key=lambda p: int(re.search(r"-p(\d+)\.png$", p.name).group(1)))


def render_pages(proj: Project, main: Path, pages: str | None, ppi: int, out_dir: Path, stem: str,
                 keep_prev: bool = True) -> tuple[bool, list[Path], str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    prev = out_dir / "prev"
    if keep_prev:
        old = page_files(out_dir, stem)
        if old:
            prev.mkdir(exist_ok=True)
            for p in page_files(prev, stem):
                p.unlink()
            for p in old:
                shutil.move(str(p), prev / p.name)
    else:
        for p in page_files(out_dir, stem):
            p.unlink()
    ok, diags, kind = compile_doc(proj, main, str(out_dir / f"{stem}-p{{p}}.png"), fmt="png", pages=pages, ppi=ppi)
    msg = "\n".join(format_diag(d, proj.compile_root) for d in diags[:10])
    return ok, page_files(out_dir, stem), msg


def write_sheet(proj: Project, out_dir: Path, images: list[Path], labels: list[str], cols: int, name: str,
                img_width_pt: float, ppi: int) -> Path | None:
    rel = lambda p: "/" + str(p.resolve().relative_to(proj.compile_root))  # noqa: E731
    cells = ",\n".join(
        f'  stack(spacing: 3pt, box(stroke: 0.5pt + gray, image("{rel(p)}", width: {img_width_pt}pt)), '
        f'text(8pt, fill: rgb("#555"))[{l}])' for p, l in zip(images, labels))
    src = (f"#set page(width: auto, height: auto, margin: 8pt, fill: white)\n"
           f"#set text(font: \"DejaVu Sans\", fallback: true)\n"
           f"#grid(columns: {cols}, gutter: 8pt,\n{cells}\n)\n")
    sheet_typ = out_dir / f"{name}.typ"
    sheet_typ.write_text(src)
    out = out_dir / f"{name}.png"
    ok, diags, _ = compile_doc(proj, sheet_typ, str(out), fmt="png", ppi=ppi)
    if not ok:
        print("\n".join(format_diag(d, proj.compile_root) for d in diags[:5]), file=sys.stderr)
        return None
    return out


def crop(proj: Project, out_dir: Path, page_png: Path, region: list[float], ppi: int, name: str) -> Path | None:
    """Crop a fractional region (x0,y0,x1,y1 in 0..1) of a page PNG rendered at `ppi`, 1:1 pixels."""
    w, h = png_size(page_png)
    x0, y0, x1, y1 = region
    px = 72.0 / ppi  # pt per pixel
    cw, ch = (x1 - x0) * w * px, (y1 - y0) * h * px
    rel = "/" + str(page_png.resolve().relative_to(proj.compile_root))
    # Give the image an explicit width AND height: with only a width, `image` is sized to the
    # available region and its default fit ("cover") crops the centre instead of the region we want.
    src = (f"#set page(width: auto, height: auto, margin: 0pt)\n"
           f"#box(width: {cw:.3f}pt, height: {ch:.3f}pt, clip: true, "
           f"place(top + left, dx: {-x0 * w * px:.3f}pt, dy: {-y0 * h * px:.3f}pt, "
           f"image(\"{rel}\", width: {w * px:.3f}pt, height: {h * px:.3f}pt, fit: \"stretch\")))\n")
    t = out_dir / f"{name}.typ"
    t.write_text(src)
    out = out_dir / f"{name}.png"
    ok, diags, _ = compile_doc(proj, t, str(out), fmt="png", ppi=ppi)
    if not ok:
        print("\n".join(format_diag(d, proj.compile_root) for d in diags[:5]), file=sys.stderr)
        return None
    return out


def png_size(p: Path) -> tuple[int, int]:
    with open(p, "rb") as f:
        head = f.read(24)
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def cmd_render(args):
    target = Path(args.file).resolve()
    proj = Project(find_project_root(target))
    main = target
    if args.main:
        main = Path(args.main).resolve()
    elif target.suffix == ".typ":
        ms = proj.mains_for(target)
        if ms and ms[0] != target:
            main = ms[0]
            print(f"(rendering entrypoint {proj.rel(main)} which includes {proj.rel(target)}; pass --main to override)")
    out_dir = proj.preview_dir()
    stem = main.stem
    cfg_ppi = proj.cfg.get("ppi")
    ppi = args.ppi or (200 if args.region else (cfg_ppi or 110))
    pages = args.pages
    if args.region and not pages:
        pages = "1"
    ok, files, msg = render_pages(proj, main, pages, ppi, out_dir, stem, keep_prev=not args.region)
    if msg:
        print(msg)
    if not ok:
        print("render FAILED (fix the errors above; `ttk check` for full diagnostics)")
        sys.exit(1)
    if args.region:
        region = [float(x) for x in args.region.split(",")]
        if len(region) != 4 or not all(0 <= v <= 1 for v in region) or region[0] >= region[2] or region[1] >= region[3]:
            die("--region must be x0,y0,x1,y1 fractions of the page, e.g. 0,0,1,0.5 for the top half")
        out = crop(proj, out_dir, files[0], region, ppi, f"{stem}-zoom")
        print(f"zoomed region of page {pages} at {ppi} ppi: {out}")
        return
    total = len(files)
    print(f"rendered {total} page(s) at {ppi} ppi → {out_dir}")
    if args.sheet or (total > args.max_pages and not args.pages):
        cols = args.cols or min(6, max(2, int(total ** 0.5 + 0.99)))
        labels = [f"p{re.search(r'-p(\d+)', p.name).group(1)}" for p in files]
        sheet = write_sheet(proj, out_dir, files, labels, cols, f"{stem}-sheet", 160, 72)
        print(f"contact sheet ({total} pages, {cols} cols): {sheet}")
        if total > args.max_pages and not args.sheet:
            print(f"(more than {args.max_pages} pages — view the sheet first, then individual pages with --pages)")
            return
    for p in files[: args.max_pages]:
        print(p)
    if args.compare:
        prev = out_dir / "prev"
        pairs = [(prev / p.name, p) for p in files if (prev / p.name).exists()]
        if not pairs:
            print("(no previous render to compare against)")
            return
        imgs, labels = [], []
        for a, b in pairs[: args.max_pages]:
            imgs += [a, b]
            n = re.search(r"-p(\d+)", b.name).group(1)
            labels += [f"p{n} before", f"p{n} after"]
        cmp_png = write_sheet(proj, out_dir, imgs, labels, 2, f"{stem}-compare", 260, 96)
        print(f"before/after comparison: {cmp_png}")


# --------------------------------------------------------------------------- snippet

def cmd_snippet(args):
    base = Path(args.dir or ".").resolve()
    proj = Project(find_project_root(base))
    out_dir = proj.preview_dir()
    name = args.name or "snippet"
    margin = args.margin
    preamble = (f"#set page(width: {args.width}, height: auto, margin: {margin}, fill: {args.fill})\n")
    if args.file:
        f = Path(args.file).resolve()
        try:
            rel = "/" + str(f.relative_to(proj.compile_root))
        except ValueError:
            die(f"{f} is outside the project root {proj.compile_root}")
        body = f'#include "{rel}"\n'
        name = args.name or f.stem
    else:
        code = args.code if args.code is not None else sys.stdin.read()
        body = code + "\n"
    src = preamble + (args.preamble + "\n" if args.preamble else "") + body
    t = out_dir / f"{name}.typ"
    t.write_text(src)
    out = out_dir / f"{name}.png"
    ok, diags, _ = compile_doc(proj, t, str(out), fmt="png", ppi=args.ppi, pages="1")
    for d in diags[:10]:
        print(format_diag(d, proj.compile_root))
    if not ok:
        print(f"snippet FAILED (source: {t})")
        sys.exit(1)
    w, h = png_size(out)
    print(f"{out}  ({w}x{h}px at {args.ppi} ppi; source {t})")
    if not args.file:
        print("note: relative paths in snippets resolve from .typst-preview/ — use root-absolute paths like \"/fig/x.typ\"")


# --------------------------------------------------------------------------- outline / query

OUTLINE_EXPR = r"""
{
  let plain(it) = {
    if type(it) == str { it }
    else if it == none { "" }
    else if it.has("text") { it.text }
    else if it.has("children") { it.children.map(plain).join("") }
    else if it.has("body") { plain(it.body) }
    else if it.func() == [ ].func() { " " }
    else { "" }
  }
  let lbl(it) = if it.has("label") { str(it.label) } else { none }
  (
    headings: query(heading).map(h => (level: h.level, title: plain(h.body), page: h.location().page(), label: lbl(h))),
    figures: query(figure).map(f => (kind: repr(f.kind), caption: if f.caption != none { plain(f.caption.body) } else { none }, page: f.location().page(), label: lbl(f))),
    equations: query(math.equation.where(block: true)).filter(e => e.has("label")).map(e => (page: e.location().page(), label: lbl(e))),
  )
}
"""


def cmd_outline(args):
    target = Path(args.file).resolve()
    proj = Project(find_project_root(target))
    main = Path(args.main).resolve() if args.main else (proj.mains_for(target) or [target])[0]
    kind, exe = pick_compiler(proj.compile_root)
    if kind != "typst":
        die("outline needs the `typst` CLI (typst eval) with access to this path")
    expr = args.expr or OUTLINE_EXPR
    rc, so, se = run([exe, "--color", "never", "eval", *proj.compile_args(), "--in", str(main), expr],
                     cwd=proj.compile_root)
    if rc != 0:
        print(se[-3000:])
        sys.exit(1)
    if args.expr:
        print(so)
        return
    data = json.loads(so)
    last = max([h["page"] for h in data["headings"]] + [f["page"] for f in data["figures"]] + [0])
    print(f"{proj.rel(main)}: (last heading/figure on page {last})")
    for h in data["headings"]:
        lab = f"  <{h['label']}>" if h.get("label") else ""
        print(f"{'  ' * (h['level'] - 1)}{'=' * h['level']} {h['title'][:90]}  (p{h['page']}){lab}")
    if data["figures"]:
        print("\nfigures:")
        for f in data["figures"]:
            lab = f"<{f['label']}>" if f.get("label") else "(no label)"
            print(f"  p{f['page']} {f['kind']:8s} {lab}  {(f['caption'] or '')[:80]}")
    if data["equations"]:
        print("\nlabelled equations: " + ", ".join(f"<{e['label']}> p{e['page']}" for e in data["equations"]))
