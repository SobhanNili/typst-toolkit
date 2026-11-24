"""Shared helpers for the typst toolkit (stdlib only)."""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
CACHE = Path(os.environ.get("TTK_CACHE") or (Path(os.environ.get("XDG_CACHE_HOME") or HOME / ".cache") / "typst-toolkit"))
PREVIEW_DIR = ".typst-preview"
CONFIG_NAME = "typst-toolkit.toml"
SKIP_DIRS = {".git", PREVIEW_DIR, "node_modules", ".venv", "__pycache__", "target", "dist"}


def die(msg: str, code: int = 1):
    print(msg, file=sys.stderr)
    sys.exit(code)


# --------------------------------------------------------------------------- binaries

def _version_key(p: str):
    m = re.search(r"tinymist-(\d+)\.(\d+)\.(\d+)", p)
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def find_tinymist() -> str | None:
    env = os.environ.get("TTK_TINYMIST")
    if env and os.access(env, os.X_OK):
        return env
    w = shutil.which("tinymist")
    if w:
        return w
    cands = []
    for base in ("~/.vscode-server/extensions", "~/.vscode/extensions", "~/.cursor-server/extensions",
                 "~/.cursor/extensions", "~/.vscode-oss/extensions", "~/.windsurf-server/extensions"):
        cands += glob.glob(os.path.expanduser(f"{base}/myriad-dreamin.tinymist-*/out/tinymist"))
    cands = [c for c in cands if os.access(c, os.X_OK)]
    return max(cands, key=_version_key) if cands else None


def find_typst() -> str | None:
    env = os.environ.get("TTK_TYPST")
    if env and os.access(env, os.X_OK):
        return env
    return shutil.which("typst")


def snap_can_read(path: Path) -> bool:
    """Snap-confined typst can only read non-hidden paths under $HOME."""
    try:
        rel = path.resolve().relative_to(HOME.resolve())
    except ValueError:
        return False
    return not (rel.parts and rel.parts[0].startswith("."))


def pick_compiler(root: Path) -> tuple[str, str]:
    """Return (kind, path) where kind is 'typst' or 'tinymist'."""
    typst, tiny = find_typst(), find_tinymist()
    is_snap = bool(typst) and (typst.startswith("/snap/") or os.path.realpath(typst).endswith("/snap"))
    if typst and not (is_snap and not snap_can_read(root)):
        return "typst", typst
    if tiny:
        return "tinymist", tiny
    if typst:
        return "typst", typst
    die("Neither `typst` nor `tinymist` found. Install typst or set TTK_TYPST / TTK_TINYMIST.")


def run(cmd, cwd=None, timeout=180, env=None):
    e = dict(os.environ)
    e.setdefault("TINYMIST_LOG", "error")
    if env:
        e.update(env)
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, errors="replace", timeout=timeout, env=e)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s: {' '.join(map(str, cmd))}"


def typst_version() -> str | None:
    t = find_typst()
    if not t:
        return None
    _, out, _ = run([t, "--version"])
    m = re.search(r"(\d+\.\d+\.\d+)", out)
    return m.group(1) if m else None


# --------------------------------------------------------------------------- project model

def load_toml(path: Path) -> dict:
    import tomllib
    try:
        return tomllib.loads(path.read_text())
    except Exception as ex:  # noqa: BLE001
        print(f"warning: could not parse {path}: {ex}", file=sys.stderr)
        return {}


def find_project_root(start: Path) -> Path:
    start = start.resolve()
    d = start if start.is_dir() else start.parent
    fallback = None
    for cur in [d, *d.parents]:
        if (cur / CONFIG_NAME).exists():
            return cur
        if fallback is None and ((cur / "typst.toml").exists() or (cur / ".git").exists()):
            fallback = cur
        if cur == HOME or cur == cur.parent:
            break
    if fallback:
        return fallback
    # No marker: climb (max 4 levels) to the highest directory whose top-level .typ files
    # include/import this file, so chapter files resolve to the real entrypoint.
    best = d
    if start.suffix == ".typ":
        for cur in list(d.parents)[:4]:
            if cur == HOME or cur == cur.parent:
                break
            tops = list(cur.glob("*.typ"))
            if not tops:
                continue
            proj = Project(cur)
            if any(t.resolve() != start and proj.reaches(t.resolve(), start) for t in tops):
                best = cur
    return best


class Project:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.cfg = load_toml(root / CONFIG_NAME) if (root / CONFIG_NAME).exists() else {}
        # compiler --root may differ from where the config lives
        self.compile_root = (self.root / self.cfg.get("root", ".")).resolve()
        self._files = None
        self._graph = None

    # -- files & graph
    def typ_files(self) -> list[Path]:
        if self._files is None:
            out = []
            for dirpath, dirnames, filenames in os.walk(self.root):
                dirnames[:] = [x for x in dirnames if x not in SKIP_DIRS and not x.startswith(".")]
                for f in filenames:
                    if f.endswith(".typ"):
                        out.append(Path(dirpath) / f)
                if len(out) > 3000:
                    break
            self._files = sorted(out)
        return self._files

    DEP_RE = re.compile(
        r"""\b(include|import|image|read|json|yaml|toml|csv|xml|cbor|bibliography|plugin)\s*\(?\s*"([^"@][^"]*)\"""")

    def resolve_ref(self, src: Path, ref: str) -> Path:
        if ref.startswith("/"):
            return (self.compile_root / ref.lstrip("/")).resolve()
        return (src.parent / ref).resolve()

    def deps_of(self, f: Path) -> list[tuple[str, Path]]:
        try:
            text = f.read_text(errors="replace")
        except OSError:
            return []
        text = strip_comments(text)
        res = []
        for kind, ref in self.DEP_RE.findall(text):
            res.append((kind, self.resolve_ref(f, ref)))
        return res

    def graph(self) -> dict[Path, list[tuple[str, Path]]]:
        if self._graph is None:
            self._graph = {f.resolve(): self.deps_of(f) for f in self.typ_files()}
        return self._graph

    def mains(self) -> list[Path]:
        m = self.cfg.get("main")
        if m:
            m = [m] if isinstance(m, str) else m
            return [(self.root / x).resolve() for x in m]
        tt = self.root / "typst.toml"
        if tt.exists():
            t = load_toml(tt)
            outs = []
            tpl = t.get("template")
            if tpl and tpl.get("path") and tpl.get("entrypoint"):
                outs.append((self.root / tpl["path"] / tpl["entrypoint"]).resolve())
            pkg = t.get("package", {})
            if pkg.get("entrypoint"):
                outs.append((self.root / pkg["entrypoint"]).resolve())
            if outs:
                return [o for o in outs if o.exists()]
        g = self.graph()
        referenced = {p for deps in g.values() for _, p in deps}
        roots = [f for f in g if f not in referenced]
        prio = ("main.typ", "thesis.typ", "paper.typ", "document.typ", "report.typ", "index.typ")
        roots.sort(key=lambda p: (p.name not in prio, len(p.relative_to(self.root).parts), str(p)))
        return roots

    def reaches(self, main: Path, target: Path) -> bool:
        g = self.graph()
        seen, stack = set(), [main]
        while stack:
            cur = stack.pop()
            if cur == target:
                return True
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(p for _, p in g.get(cur, []))
        return False

    def mains_for(self, target: Path, limit: int = 6) -> list[Path]:
        target = target.resolve()
        mains = self.mains()
        if target.suffix == ".typ":
            hits = [m for m in mains if self.reaches(m, target)]
            if hits:
                return hits[:limit]
            if target in self.graph() or target.exists():
                return [target]
        return mains[:limit]

    # -- compiler args
    def compile_args(self) -> list[str]:
        args = ["--root", str(self.compile_root)]
        for k, v in (self.cfg.get("inputs") or {}).items():
            args += ["--input", f"{k}={v}"]
        fps = self.cfg.get("font-paths") or []
        if fps:
            args += ["--font-path", os.pathsep.join(str((self.root / p).resolve()) for p in fps)]
        return args

    def preview_dir(self) -> Path:
        d = self.compile_root / PREVIEW_DIR
        d.mkdir(parents=True, exist_ok=True)
        gi = d / ".gitignore"
        if not gi.exists():
            gi.write_text("*\n")
        return d

    def rel(self, p: Path) -> str:
        try:
            return str(p.resolve().relative_to(self.root))
        except ValueError:
            return str(p)


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"(?m)(^|[^:\\])//.*$", r"\1", text)


# --------------------------------------------------------------------------- diagnostics

DIAG_HEAD = re.compile(r"^(error|warning)(?:\[[^\]]*\])?: (.*)$")
LOC_RE = re.compile(r"^\s*┌─ (.+?):(\d+):(\d+)\s*$")


def parse_diagnostics(output: str) -> list[dict]:
    """Parse typst/tinymist long-form diagnostics into blocks."""
    diags, cur = [], None
    for line in output.splitlines():
        if re.match(r"^\[\d{4}-\d\d-\d\dT", line):  # tinymist log lines
            continue
        m = DIAG_HEAD.match(line)
        if m:
            cur = {"severity": m.group(1), "message": m.group(2), "file": None, "line": None, "col": None,
                   "lines": [line]}
            diags.append(cur)
            continue
        if cur is None:
            # free-form lines before any diagnostic: progress output ("downloading @preview/x",
            # "12 KiB / 20 KiB") is noise; anything else that looks like a failure is kept.
            low = line.strip().lower()
            if low.startswith(("error", "fatal", "failed")) or "not found" in low:
                diags.append({"severity": "error", "message": line.strip(), "file": None, "line": None,
                              "col": None, "lines": [line]})
            continue
        lm = LOC_RE.match(line)
        if lm and cur["file"] is None:
            cur["file"], cur["line"], cur["col"] = lm.group(1), int(lm.group(2)), int(lm.group(3))
        cur["lines"].append(line)
    for d in diags:
        while d["lines"] and not d["lines"][-1].strip():
            d["lines"].pop()
    return diags


def format_diag(d: dict, root: Path) -> str:
    out = []
    for ln in d["lines"]:
        if str(root) in ln:
            ln = ln.replace(str(root) + os.sep, "")
        if ln.strip() == "│":
            continue
        out.append(ln)
    return "\n".join(out)


def dedupe(diags: list[dict]) -> list[dict]:
    seen, out = set(), []
    for d in diags:
        k = (d["severity"], d["message"], d["file"], d["line"], d["col"])
        if k not in seen:
            seen.add(k)
            out.append(d)
    return out


def compile_doc(proj: Project, main: Path, out: str, fmt: str | None = None, pages: str | None = None,
                ppi: int | None = None, extra: list[str] | None = None) -> tuple[bool, list[dict], str]:
    kind, exe = pick_compiler(proj.compile_root)
    cmd = [exe, "--color", "never", "compile"] if kind == "typst" else [exe, "compile"]
    cmd += proj.compile_args()
    if fmt:
        cmd += ["--format", fmt]
    if pages:
        cmd += ["--pages", pages]
    if ppi:
        cmd += ["--ppi", str(ppi)]
    cmd += extra or []
    cmd += [str(main), out]
    rc, so, se = run(cmd, cwd=proj.compile_root)
    text = se + ("\n" + so if so else "")
    diags = dedupe(parse_diagnostics(text))
    if rc == 124:
        diags.append({"severity": "error", "message": se.strip(), "file": None, "line": None, "col": None,
                      "lines": ["error: " + se.strip()]})
    has_err = any(d["severity"] == "error" for d in diags)
    # tinymist exits 0 even on errors, so trust the parsed diagnostics; typst's exit code is reliable.
    ok = not has_err and (rc == 0 or kind == "tinymist")
    if not ok and not has_err:
        diags.append({"severity": "error", "message": f"compiler exited with {rc}", "file": None, "line": None,
                      "col": None, "lines": [f"error: compiler exited with {rc}: {se.strip()[:500]}"]})
    return ok, diags, kind


def emit(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))
