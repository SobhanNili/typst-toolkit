"""Local mirror of the official Typst documentation (typst.app/docs) as Markdown."""
from __future__ import annotations

import concurrent.futures as cf
import json
import re
import sys
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from ttk_common import CACHE, die, typst_version

BASE = "https://typst.app"
UA = "typst-toolkit-docs-mirror/1.0 (+local cache for offline reference)"
DOCS = CACHE / "docs"


def http_get(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as ex:  # noqa: BLE001
            last = ex
            time.sleep(1 + attempt)
    raise RuntimeError(f"GET {url} failed: {last}")


# --------------------------------------------------------------------------- HTML -> Markdown

class DocConverter(HTMLParser):
    SKIP_CLASSES = {"tooltip-context", "preview", "copy", "page-end-buttons", "sources-link"}
    VOID = {"img", "br", "hr", "input", "meta", "link", "source", "wbr", "col", "area", "base", "embed", "track"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.active = False
        self.done = False
        self.skip_depth = 0
        self.stack: list[tuple[str, bool]] = []  # (tag, started_skip)
        self.in_pre = False
        self.in_code = 0
        self.list_depth = 0
        self.last_pill = False
        self.title = ""
        self.in_h1 = False
        self.cell_count = 0
        self.links: set[str] = set()
        self.head_colon = False

    def w(self, s: str):
        self.out.append(s)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        href = a.get("href") or ""
        if tag == "a" and href.startswith("/docs/"):
            self.links.add(href.split("#")[0])
        if self.done:
            return
        if not self.active:
            if tag == "h1":
                self.active = True
            else:
                return
        cls = set((a.get("class") or "").split())
        void = tag in self.VOID
        starts_skip = bool(cls & self.SKIP_CLASSES) or tag in ("button", "svg", "script", "style")
        if tag == "li" and a.get("data-codex-name") and not self.skip_depth:
            # symbol tables (sym/emoji): one greppable line per symbol incl. its LaTeX name
            parts = [f"`{a['data-codex-name']}`", a.get("data-value") or ""]
            if a.get("data-unic-name"):
                parts.append(a["data-unic-name"])
            if a.get("data-latex-name"):
                parts.append(f"LaTeX: `{a['data-latex-name']}`")
            if a.get("data-math-class"):
                parts.append(f"math class: {a['data-math-class']}")
            self.w("\n- " + " — ".join(p for p in parts if p))
            starts_skip = True
        if "page-end-buttons" in cls:
            self.done = True
            return
        if not void:
            self.stack.append((tag, starts_skip))
        if starts_skip:
            self.skip_depth += 1
            if void:
                self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        is_pill = tag == "a" and "pill" in cls
        if is_pill and self.last_pill:
            self.w(" | ")
        if tag != "a":
            self.last_pill = False
        if tag in ("h1", "h2", "h3", "h4", "h5"):
            lvl = int(tag[1])
            self.w("\n\n" + "#" * lvl + " ")
            self.head_colon = False
            if tag == "h1":
                self.in_h1 = True
        elif tag == "pre":
            self.in_pre = True
            self.w("\n\n```typ\n")
        elif tag == "code":
            if not self.in_pre:
                self.in_code += 1
                self.w("`")
        elif tag == "p":
            if not (self.out and self.out[-1].endswith("- ")):
                self.w("\n\n")
        elif tag in ("ul", "ol"):
            self.list_depth += 1
            self.w("\n")
        elif tag == "li":
            self.w("\n" + "  " * max(self.list_depth - 1, 0) + "- ")
        elif tag == "tr":
            self.w("\n|")
            self.cell_count = 0
        elif tag in ("td", "th"):
            self.w(" ")
        elif tag == "br":
            self.w("\n")
        elif tag == "div" and "code-definition" in cls:
            self.w("\n\n```typc\n")
            self.in_pre = True
            self._def_div = len(self.stack)
        elif tag == "small":
            self.w(" ")
        elif tag == "span" and "overview-param" in cls:
            self.w("\n  ")
        elif tag == "summary":
            self.w("\n\n")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.done or not self.active:
            return
        if tag in self.VOID or not any(t == tag for t, _ in self.stack):
            return
        while self.stack:
            t, sk = self.stack.pop()
            if sk:
                self.skip_depth -= 1
            if t == tag:
                break
        else:
            return
        if self.skip_depth:
            return
        if tag == "a":
            pass
        if tag in ("h1", "h2", "h3", "h4", "h5"):
            if tag == "h1":
                self.in_h1 = False
            self.w("\n")
        elif tag == "pre":
            self.in_pre = False
            self.w("\n```\n")
        elif tag == "code" and not self.in_pre:
            self.in_code = max(0, self.in_code - 1)
            self.w("`")
            if any(t in ("h3", "h4") for t, _ in self.stack) and not self.head_colon:
                self.head_colon = True
                self.w(": ")
        elif tag in ("ul", "ol"):
            self.list_depth = max(0, self.list_depth - 1)
            self.w("\n")
        elif tag in ("td", "th"):
            self.w(" |")
        elif tag == "div" and getattr(self, "_def_div", None) == len(self.stack) + 1:
            self._def_div = None
            self.in_pre = False
            self.w("\n```\n")

    def handle_data(self, data):
        if self.done or not self.active or self.skip_depth:
            return
        if self.in_h1:
            self.title += data
        top = self.stack[-1] if self.stack else None
        if top and top[0] == "a":
            # pills are inside <a class="pill">; track for "|" separation
            self.last_pill = True
        elif data.strip():
            self.last_pill = False
        if self.in_pre:
            self.w(data)
        else:
            self.w(re.sub(r"\s+", " ", data))

    def markdown(self) -> str:
        md = "".join(self.out)
        md = re.sub(r"[ \t]+\n", "\n", md)
        md = re.sub(r"\n{3,}", "\n\n", md)
        return md.strip() + "\n"


def convert(html: str) -> tuple[str, str, set[str]]:
    c = DocConverter()
    c.feed(html)
    return c.title.strip(), c.markdown(), c.links


def url_to_rel(url_path: str) -> str:
    p = url_path.strip("/")
    assert p.startswith("docs")
    p = p[len("docs"):].strip("/")
    return (p or "index") + ".md"


# --------------------------------------------------------------------------- mirror

def current_dir() -> Path | None:
    link = DOCS / "current"
    if link.exists():
        return link.resolve()
    vers = sorted([d for d in DOCS.glob("*") if d.is_dir()], key=lambda d: d.stat().st_mtime)
    return vers[-1] if vers else None


def sync(force: bool = False, workers: int = 8):
    DOCS.mkdir(parents=True, exist_ok=True)
    tmp = DOCS / ".partial"
    tmp.mkdir(exist_ok=True)
    seen: set[str] = set()
    queue = ["/docs/"]
    index = {}
    t0 = time.time()

    def fetch(path):
        html = http_get(BASE + path)
        return path, *convert(html)

    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        while queue:
            batch = [p for p in queue if p not in seen]
            queue = []
            seen.update(batch)
            for fut in cf.as_completed([ex.submit(fetch, p) for p in batch]):
                try:
                    path, title, md, links = fut.result()
                except Exception as e:  # noqa: BLE001
                    print(f"  ! {e}", file=sys.stderr)
                    continue
                rel = url_to_rel(path)
                out = tmp / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(f"<!-- source: {BASE}{path} -->\n{md}")
                index[rel] = {"title": title, "url": BASE + path}
                for l in links:
                    if l not in seen:
                        queue.append(l)
            print(f"  fetched {len(index)} pages...", file=sys.stderr)
    vers = [k.split("/")[1][:-3] for k in index if k.startswith("changelog/") and re.match(r"changelog/\d", k)]
    vers.sort(key=lambda v: tuple(int(x) for x in re.findall(r"\d+", v)))
    version = vers[-1] if vers else time.strftime("%Y%m%d")
    (tmp / "index.json").write_text(json.dumps(index, indent=1, sort_keys=True))
    (tmp / "VERSION").write_text(version + "\n")
    dest = DOCS / version
    if dest.exists():
        import shutil
        shutil.rmtree(dest)
    tmp.rename(dest)
    link = DOCS / "current"
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(dest.name)
    print(f"Mirrored {len(index)} pages of Typst {version} docs to {dest} in {time.time() - t0:.0f}s")
    tv = typst_version()
    if tv and tv != version:
        print(f"note: installed typst is {tv}, docs are for {version} (typst.app only serves the latest docs).")


def need_mirror() -> Path:
    d = current_dir()
    if not d:
        die("Docs mirror not found. Run: ttk docs sync   (one-time, ~1 min)  — or use: ttk docs fetch <url>")
    return d


def load_index(d: Path) -> dict:
    return json.loads((d / "index.json").read_text())


def resolve(name: str, d: Path) -> list[Path]:
    name = name.strip().strip("/")
    name = re.sub(r"^https?://typst\.app/docs/?", "", name)
    name = name.removesuffix(".md")
    cands = [d / f"{name}.md"]
    if cands[0].exists():
        return cands
    stem = name.split("/")[-1].lower()
    hits = [p for p in d.rglob("*.md") if p.stem.lower() == stem]
    if not hits:
        idx = load_index(d)
        hits = [d / k for k, v in idx.items() if v["title"].lower().replace("`", "") == stem]
    hits.sort(key=lambda p: (not str(p.relative_to(d)).startswith("reference/"), len(str(p))))
    return hits


def cmd_show(name: str, section: str | None, outline: bool):
    d = need_mirror()
    hits = resolve(name, d)
    if not hits:
        die(f"No docs page matches '{name}'. Try: ttk docs search '{name}'")
    if len(hits) > 1 and hits[0].stem.lower() == hits[1].stem.lower() and not section:
        print(f"(several pages named '{name}', showing first; others: "
              + ", ".join(str(h.relative_to(d))[:-3] for h in hits[1:6]) + ")\n")
    text = hits[0].read_text()
    print(f"[{hits[0].relative_to(d)}]  (docs version {(d / 'VERSION').read_text().strip()})")
    if outline:
        for ln in text.splitlines():
            if ln.startswith("#"):
                print(ln[:140])
        return
    if section:
        print(extract_section(text, section) or f"(no section '{section}'; use --outline to list headings)")
        return
    print(text)


def extract_section(text: str, section: str) -> str | None:
    lines = text.splitlines()
    sec = section.lower().strip()
    for i, ln in enumerate(lines):
        m = re.match(r"^(#+)\s+(.*)", ln)
        if not m:
            continue
        head = m.group(2).strip().strip("`").lower()
        first = re.split(r"[\s`(]", head)[0] if head else ""
        if first == sec or head == sec or head.startswith(sec + " "):
            lvl = len(m.group(1))
            out = [ln]
            for ln2 in lines[i + 1:]:
                m2 = re.match(r"^(#+)\s", ln2)
                if m2 and len(m2.group(1)) <= lvl:
                    break
                out.append(ln2)
            return "\n".join(out)
    return None


def cmd_search(pattern: str, limit: int, files_only: bool, ignore_case: bool, section: str | None):
    d = need_mirror()
    flags = re.I if ignore_case else 0
    try:
        rx = re.compile(pattern, flags)
    except re.error:
        rx = re.compile(re.escape(pattern), flags)
    idx = load_index(d)
    results = []
    for p in sorted(d.rglob("*.md")):
        rel = str(p.relative_to(d))
        if section and not rel.startswith(section):
            continue
        lines = p.read_text().splitlines()
        hits = [(i + 1, ln) for i, ln in enumerate(lines) if rx.search(ln)]
        title = idx.get(rel, {}).get("title", "")
        title_hit = bool(rx.search(title) or rx.search(p.stem))
        if hits or title_hit:
            score = (title_hit * 100) + (rel.startswith("reference/") * 5) + min(len(hits), 20) \
                - (rel.startswith("changelog/") * 50)
            results.append((score, rel, title, hits))
    results.sort(key=lambda r: -r[0])
    if not results:
        print("no matches")
        return
    shown = 0
    for score, rel, title, hits in results:
        if files_only:
            print(f"{rel[:-3]:55s} {title}  ({len(hits)} hits)")
            shown += 1
        else:
            print(f"== {rel[:-3]}  [{title}]  ({len(hits)} hits)")
            for n, ln in hits[:4]:
                print(f"  {n}: {ln.strip()[:200]}")
            shown += 1
        if shown >= limit:
            print(f"... {len(results) - shown} more pages (use -n or --files)")
            break


def cmd_fetch(url: str):
    if not url.startswith("http"):
        url = BASE + "/docs/" + url.strip("/") + "/"
    title, md, _ = convert(http_get(url))
    print(f"<!-- source: {url} -->\n{md}")


def latex_symbol_map() -> dict[str, list[str]]:
    """LaTeX command (without backslash) -> Typst symbol names, from the mirrored sym page."""
    d = current_dir()
    out: dict[str, list[str]] = {}
    if not d or not (d / "reference/symbols/sym.md").exists():
        return out
    for ln in (d / "reference/symbols/sym.md").read_text().splitlines():
        m = re.match(r"- `([^`]+)` .*LaTeX: `\\([A-Za-z]+)`", ln)
        if m:
            out.setdefault(m.group(2), []).append(m.group(1))
            name = m.group(1)
            if "." not in name:
                out.setdefault(name, []).append(name)  # LaTeX \alpha -> Typst alpha
    # unicode-math style names: \mitvarepsilon, \mupalpha, \BbbR ... -> also index without prefix
    for k, v in list(out.items()):
        for pre in ("mit", "mup", "Bbb", "up", "mbf", "mscr", "mfrak"):
            if k.startswith(pre) and len(k) > len(pre) + 1:
                out.setdefault(k[len(pre):], v)
    return out


def cmd_sym(query: str, n: int):
    d = need_mirror()
    q = query.lstrip("\\").lower()
    lines = []
    for page in ("reference/symbols/sym.md", "reference/symbols/emoji.md"):
        for ln in (d / page).read_text().splitlines():
            if not ln.startswith("- `"):
                continue
            name = ln.split("`")[1].lower()
            latex = re.search(r"LaTeX: `\\([^`]+)`", ln)
            exact = name == q or (latex and latex.group(1).lower() == q)
            if exact or q in ln.lower():
                lines.append((0 if exact else 1, ln))
    lines.sort(key=lambda x: x[0])
    for _, ln in lines[:n]:
        print(ln[2:])
    if not lines:
        print(f"no symbol matches '{query}' (try a word from its Unicode name, e.g. 'arrow', 'integral')")
    print("(in math use the name directly: $a lt.eq b$; in markup use #sym.name)")


def cmd_status():
    d = current_dir()
    if not d:
        print("docs mirror: missing (run `ttk docs sync`)")
        return
    n = len(list(d.rglob("*.md")))
    age = (time.time() - (d / "index.json").stat().st_mtime) / 86400
    print(f"docs mirror: {d} | version {(d / 'VERSION').read_text().strip()} | {n} pages | {age:.0f} days old")


def main(args):
    if args.dcmd == "sync":
        sync(args.force)
    elif args.dcmd == "show":
        cmd_show(args.name, args.section, args.outline)
    elif args.dcmd == "search":
        cmd_search(args.pattern, args.n, args.files, not args.case, args.within)
    elif args.dcmd == "fetch":
        cmd_fetch(args.url)
    elif args.dcmd == "sym":
        cmd_sym(args.query, args.n)
    elif args.dcmd == "status":
        cmd_status()
    elif args.dcmd == "path":
        print(need_mirror())
