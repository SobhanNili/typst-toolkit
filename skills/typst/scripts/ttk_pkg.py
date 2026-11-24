"""Typst package tools: search the Universe index, fetch, inspect API and docs."""
from __future__ import annotations

import io
import json
import os
import re
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

from ttk_common import CACHE, HOME, Project, die, find_project_root, find_tinymist, run, strip_comments

INDEX_URL = "https://packages.typst.org/preview/index.json"
UA = "typst-toolkit/1.0"


def data_dir() -> Path:
    return Path(os.environ.get("TYPST_PACKAGE_PATH") or (Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local/share") / "typst/packages"))


def cache_dir() -> Path:
    return Path(os.environ.get("TYPST_PACKAGE_CACHE_PATH") or (Path(os.environ.get("XDG_CACHE_HOME") or HOME / ".cache") / "typst/packages"))


def vkey(v: str):
    return tuple(int(x) if x.isdigit() else 0 for x in re.split(r"[.\-+]", v))


# --------------------------------------------------------------------------- index

def load_index(max_age_h: float = 24) -> list[dict]:
    p = CACHE / "universe-index.json"
    if not p.exists() or time.time() - p.stat().st_mtime > max_age_h * 3600:
        try:
            req = urllib.request.Request(INDEX_URL, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        except Exception as ex:  # noqa: BLE001
            if not p.exists():
                die(f"cannot download package index: {ex}")
            print(f"(offline: using cached index, {ex})", file=sys.stderr)
    return json.loads(p.read_text())


def latest_versions(index: list[dict]) -> dict[str, dict]:
    best: dict[str, dict] = {}
    for e in index:
        cur = best.get(e["name"])
        if cur is None or vkey(e["version"]) > vkey(cur["version"]):
            best[e["name"]] = e
    return best


def parse_spec(spec: str) -> tuple[str, str, str | None]:
    """'@preview/cetz:0.3.4' | 'cetz:0.3.4' | 'cetz' -> (namespace, name, version|None)."""
    m = re.match(r"^(?:@([\w-]+)/)?([\w-]+)(?::([\w.\-+]+))?$", spec.strip())
    if not m:
        die(f"bad package spec: {spec}")
    return m.group(1) or "preview", m.group(2), m.group(3)


def local_versions(ns: str, name: str) -> dict[str, Path]:
    out = {}
    for base in (data_dir(), cache_dir()):
        d = base / ns / name
        if d.is_dir():
            for v in d.iterdir():
                if (v / "typst.toml").exists():
                    out.setdefault(v.name, v)
    return out


def resolve(spec: str, fetch: bool = True) -> tuple[str, str, str, Path | None]:
    ns, name, ver = parse_spec(spec)
    local = local_versions(ns, name)
    if ver is None:
        if ns == "preview":
            try:
                latest = latest_versions(load_index()).get(name)
            except SystemExit:
                latest = None
            if latest:
                ver = latest["version"]
        if ver is None and local:
            ver = max(local, key=vkey)
        if ver is None:
            die(f"package {ns}/{name} not found in index or locally. Try: ttk pkg search {name}")
    path = local.get(ver)
    if path is None and fetch and ns == "preview":
        path = download(name, ver)
    return ns, name, ver, path


def download(name: str, ver: str) -> Path:
    dest = cache_dir() / "preview" / name / ver
    if (dest / "typst.toml").exists():
        return dest
    url = f"https://packages.typst.org/preview/{name}-{ver}.tar.gz"
    print(f"downloading {url}", file=sys.stderr)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
    except Exception as ex:  # noqa: BLE001
        die(f"download failed: {ex}")
    tmp = dest.with_name(dest.name + ".partial")
    tmp.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        tf.extractall(tmp, filter="data")
    tmp.rename(dest)
    return dest


# --------------------------------------------------------------------------- commands

def cmd_search(query: str, n: int):
    idx = latest_versions(load_index())
    terms = [t.lower() for t in query.split()]
    scored = []
    for name, e in idx.items():
        hay_name = name.lower()
        desc = (e.get("description") or "").lower()
        kw = " ".join(e.get("keywords") or []).lower() + " " + " ".join(e.get("categories") or []).lower()
        score = 0
        for t in terms:
            if t == hay_name:
                score += 50
            elif t in hay_name:
                score += 20
            if t in kw:
                score += 8
            if t in desc:
                score += 5
        if score and all(t in hay_name or t in desc or t in kw for t in terms):
            scored.append((score, name, e))
    scored.sort(key=lambda x: (-x[0], x[1]))
    if not scored:
        print("no packages match")
        return
    for score, name, e in scored[:n]:
        local = "  [cached]" if local_versions("preview", name) else ""
        print(f"@preview/{name}:{e['version']}{local}\n    {e.get('description', '')[:160]}")
    if len(scored) > n:
        print(f"... {len(scored) - n} more (-n to show more)")


def manifest(path: Path) -> dict:
    import tomllib
    return tomllib.loads((path / "typst.toml").read_text())


def cmd_info(spec: str):
    ns, name, ver, path = resolve(spec)
    print(f"@{ns}/{name}:{ver}")
    if ns == "preview":
        try:
            idx = load_index()
            vers = sorted({e["version"] for e in idx if e["name"] == name}, key=vkey)
            if vers:
                print(f"  versions: {', '.join(vers[-8:])}  (latest {vers[-1]})")
        except SystemExit:
            pass
    if not path:
        return
    m = manifest(path)
    pkg = m.get("package", {})
    for k in ("description", "entrypoint", "compiler", "repository", "homepage", "license"):
        if pkg.get(k):
            print(f"  {k}: {pkg[k]}")
    print(f"  universe page: https://typst.app/universe/package/{name}/")
    if m.get("template"):
        print(f"  template: {m['template']}")
    print(f"  local path: {path}")
    files = sorted(str(p.relative_to(path)) for p in path.rglob("*") if p.is_file())
    docs = [f for f in files if re.search(r"(readme|manual|docs?/|doc\.|guide|example|\.md$)", f, re.I)]
    print(f"  files: {len(files)} total; docs/examples: {', '.join(docs[:15]) or '-'}")
    exports = top_level_exports(path, pkg.get("entrypoint", "lib.typ"))
    if exports:
        print(f"  entrypoint exports ({len(exports)}): {', '.join(exports[:60])}")


def top_level_exports(path: Path, entry: str) -> list[str]:
    """Best-effort list of names reachable via `#import "@preview/x:v": *`."""
    seen_files, names = set(), []

    def walk(f: Path, depth=0):
        if f in seen_files or depth > 4 or not f.exists():
            return
        seen_files.add(f)
        text = strip_comments(f.read_text(errors="replace"))
        for m in re.finditer(r"(?m)^#?let\s+([A-Za-z][\w-]*)", text):
            if not m.group(1).startswith("_"):
                names.append(m.group(1))
        for m in re.finditer(r'(?m)^#?import\s+"([^"@]+)"\s*:\s*(.+)$', text):
            target = (f.parent / m.group(1)).resolve()
            items = m.group(2).strip()
            if items.startswith("*"):
                walk(target, depth + 1)
            else:
                for it in re.split(r"[,\s()]+", items):
                    if it and it != "as" and not it.startswith("_"):
                        names.append(it.split(".")[-1])
        for m in re.finditer(r'(?m)^#?import\s+"([^"@]+)"\s*$', text):
            names.append(Path(m.group(1)).stem + " (module)")

    walk((path / entry).resolve())
    out, seen = [], set()
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def cmd_readme(spec: str):
    _, name, ver, path = resolve(spec)
    if not path:
        die("package not available locally")
    for cand in ("README.md", "readme.md", "README.typ", "README"):
        if (path / cand).exists():
            print(f"[{path / cand}]\n")
            print((path / cand).read_text(errors="replace"))
            return
    die(f"no README in {path}")


def find_definitions(path: Path, symbol: str) -> list[tuple[Path, int, str]]:
    rx = re.compile(rf"(?m)^[ \t]*#?let\s+{re.escape(symbol)}\b\s*(\(|=)")
    hits = []
    for f in sorted(path.rglob("*.typ")):
        text = f.read_text(errors="replace")
        for m in rx.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            hits.append((f, line, text))
    return hits


def definition_snippet(text: str, line: int, max_lines: int = 60) -> str:
    lines = text.splitlines()
    i = line - 1
    # doc comments directly above
    j = i
    while j > 0 and re.match(r"^\s*///", lines[j - 1]):
        j -= 1
    doc = lines[j:i]
    # signature until balanced parens, then the body head
    sig, depth, started = [], 0, False
    for k in range(i, min(len(lines), i + max_lines)):
        ln = lines[k]
        sig.append(ln)
        for ch in ln:
            if ch == "(":
                depth += 1
                started = True
            elif ch == ")":
                depth -= 1
        if started and depth <= 0:
            break
        if not started and "=" in ln and "(" not in ln:
            break
    return "\n".join(doc + sig)


def cmd_api(spec: str, symbol: str | None, body: bool):
    _, name, ver, path = resolve(spec)
    if not path:
        die("package not available locally")
    if not symbol:
        m = manifest(path)
        ex = top_level_exports(path, m.get("package", {}).get("entrypoint", "lib.typ"))
        print(f"@preview/{name}:{ver} exports: {', '.join(ex)}")
        print("\nUse `ttk pkg api <spec> <symbol>` for a signature, or `ttk pkg docs <spec>` for generated docs.")
        return
    sym = symbol.split(".")[-1]
    hits = find_definitions(path, sym)
    if not hits:
        die(f"no `let {sym}` found in {path}. Try: ttk pkg grep {spec} '{sym}'")
    for f, line, text in hits[:6]:
        print(f"── {f.relative_to(path)}:{line}")
        print(definition_snippet(text, line, 200 if body else 60))
        print()
    if len(hits) > 6:
        print(f"... {len(hits) - 6} more definitions")


def cmd_grep(spec: str, pattern: str, n: int):
    _, name, ver, path = resolve(spec)
    if not path:
        die("package not available locally")
    rx = re.compile(pattern)
    shown = 0
    for f in sorted(path.rglob("*")):
        if not f.is_file() or f.suffix not in (".typ", ".md", ".toml", ".txt"):
            continue
        for i, ln in enumerate(f.read_text(errors="replace").splitlines(), 1):
            if rx.search(ln):
                print(f"{f.relative_to(path)}:{i}: {ln.strip()[:220]}")
                shown += 1
                if shown >= n:
                    print(f"... (limit {n}; raise with -n)")
                    return


def cmd_docs(spec: str):
    ns, name, ver, path = resolve(spec)
    if not path:
        die("package not available locally")
    tiny = find_tinymist()
    if not tiny:
        die("tinymist not found (needed for generated package docs); use `ttk pkg api` / `readme` instead")
    out_dir = CACHE / "pkgdocs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{ns}-{name}-{ver}.md"
    if not out.exists():
        stub_dir = CACHE / "stub"
        stub_dir.mkdir(parents=True, exist_ok=True)
        stub = stub_dir / "stub.typ"
        stub.write_text(f'#import "@{ns}/{name}:{ver}": *\n')
        raw = out.with_suffix(".raw.md")
        rc, so, se = run([tiny, "query", "packageDocs", "--id", f"@{ns}/{name}:{ver}", "--output", str(raw),
                          "--root", str(stub_dir), str(stub)], timeout=300)
        if not raw.exists():
            die(f"tinymist packageDocs failed:\n{se[-2000:]}")
        out.write_text(clean_pkgdocs(raw.read_text()))
        raw.unlink()
    text = out.read_text()
    syms = re.findall(r"(?m)^### (\w+): (\S+)", text)
    print(f"Generated docs: {out}  ({len(text) // 1024} KiB, {len(syms)} public symbols)")
    print("Read/grep that file; symbols: " + ", ".join(f"{n}" for _, n in syms[:120]))


def clean_pkgdocs(md: str) -> str:
    md = re.sub(r"<!--.*?-->\n?", "", md, flags=re.S)
    # drop private symbols (leading underscore) sections
    parts = re.split(r"(?m)^(?=### )", md)
    keep = [p for p in parts if not re.match(r"### \w+: _", p)]
    md = "".join(keep)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md


def cmd_deps(path: str):
    root = find_project_root(Path(path))
    proj = Project(root)
    uses: dict[str, list[str]] = {}
    for f in proj.typ_files():
        text = strip_comments(f.read_text(errors="replace"))
        for m in re.finditer(r'"@([\w-]+)/([\w-]+):([\w.\-+]+)"', text):
            uses.setdefault(f"@{m.group(1)}/{m.group(2)}:{m.group(3)}", []).append(proj.rel(f))
    if not uses:
        print(f"no package imports found under {root}")
        return
    try:
        latest = latest_versions(load_index())
    except SystemExit:
        latest = {}
    by_name: dict[str, set[str]] = {}
    for spec in sorted(uses):
        ns, name, ver = parse_spec(spec)
        by_name.setdefault(name, set()).add(ver)
        local = "cached" if ver in local_versions(ns, name) else "NOT cached"
        lv = latest.get(name, {}).get("version") if ns == "preview" else None
        upd = f", latest {lv}" if lv and lv != ver else (", latest" if lv else "")
        files = sorted(set(uses[spec]))
        print(f"{spec}  ({local}{upd})  used in: {', '.join(files[:5])}{' ...' if len(files) > 5 else ''}")
    for name, vs in by_name.items():
        if len(vs) > 1:
            print(f"warning: {name} imported at multiple versions: {', '.join(sorted(vs, key=vkey))}")


def main(args):
    c = args.pcmd
    if c == "search":
        cmd_search(" ".join(args.query), args.n)
    elif c == "info":
        cmd_info(args.spec)
    elif c == "fetch":
        ns, name, ver, path = resolve(args.spec)
        print(f"@{ns}/{name}:{ver} -> {path}")
    elif c == "readme":
        cmd_readme(args.spec)
    elif c == "api":
        cmd_api(args.spec, args.symbol, args.body)
    elif c == "grep":
        cmd_grep(args.spec, args.pattern, args.n)
    elif c == "docs":
        cmd_docs(args.spec)
    elif c == "deps":
        cmd_deps(args.path)
    elif c == "path":
        _, _, _, p = resolve(args.spec)
        print(p)
