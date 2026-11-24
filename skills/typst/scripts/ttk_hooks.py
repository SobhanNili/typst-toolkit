"""Claude Code hook handlers.

post: after Edit/Write on Typst-related files, compile the affected entrypoint(s) and feed
      errors / new warnings / LaTeX-isms back to Claude.
stop: before Claude finishes, re-check every project touched in this session and block
      the stop once if it still has compile errors.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from ttk_common import CACHE, find_project_root
from ttk_build import check

RELEVANT = {".typ", ".bib", ".yml", ".yaml", ".csv", ".json", ".toml", ".svg", ".xml"}


def state_path(session: str) -> Path:
    d = CACHE / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{session or 'default'}.json"


def load_state(session: str) -> dict:
    p = state_path(session)
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return {"touched": {}, "last": {}}


def save_state(session: str, st: dict):
    state_path(session).write_text(json.dumps(st))


def edited_paths(payload: dict) -> list[Path]:
    ti = payload.get("tool_input") or {}
    paths = []
    for k in ("file_path", "notebook_path", "path"):
        if ti.get(k):
            paths.append(ti[k])
    for e in ti.get("edits") or []:
        if isinstance(e, dict) and e.get("file_path"):
            paths.append(e["file_path"])
    cwd = Path(payload.get("cwd") or os.getcwd())
    return [(cwd / p).resolve() if not os.path.isabs(p) else Path(p) for p in paths]


def is_typst_related(p: Path) -> bool:
    if p.suffix == ".typ":
        return True
    if p.suffix not in RELEVANT or ".typst-preview" in p.parts:
        return False
    root = find_project_root(p)
    # only data files inside a project that actually has .typ files
    return any(root.glob("*.typ")) or any(root.glob("*/*.typ"))


def post(payload: dict):
    paths = [p for p in edited_paths(payload) if is_typst_related(p)]
    if not paths:
        return
    session = payload.get("session_id", "")
    st = load_state(session)
    msgs, any_err = [], False
    for p in paths:
        ok, text, stats = check(p, do_lint=True, latex=p.suffix == ".typ")
        root = str(find_project_root(p))
        st["touched"][root] = str(p)
        digest = hashlib.sha1(text.encode()).hexdigest()
        if not ok:
            any_err = True
            msgs.append(text)
        elif stats.get("warnings") or stats.get("latex"):
            # only re-report warnings when they changed, to avoid noise on every edit
            if st["last"].get(root) != digest:
                msgs.append(text)
        st["last"][root] = digest
    save_state(session, st)
    if not msgs:
        return
    body = "\n".join(msgs)
    if any_err:
        body += ("\n\nTypst compile FAILED after this edit. Fix these before moving on "
                 "(if you are mid-way through a multi-file change, finish it, then re-check with `ttk check`).")
        out = {"decision": "block", "reason": body}
    else:
        out = {"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                      "additionalContext": "Typst check after edit:\n" + body}}
    print(json.dumps(out))


def stop(payload: dict):
    if payload.get("stop_hook_active"):
        return
    session = payload.get("session_id", "")
    st = load_state(session)
    failures = []
    for root, last_file in list(st.get("touched", {}).items()):
        p = Path(last_file)
        if not p.exists():
            p = Path(root)
        ok, text, _ = check(p, do_lint=False, latex=False)
        if not ok:
            failures.append(text)
    if failures:
        print(json.dumps({"decision": "block", "reason": "Typst project(s) you edited still fail to compile:\n"
                          + "\n".join(failures) + "\nFix them (or explain to the user why they are left broken)."}))


def session(payload: dict):
    """Make sure the docs mirror exists / is fresh, without blocking session start."""
    import subprocess
    import time
    from ttk_docs import current_dir
    d = current_dir()
    stale = d is None or time.time() - (d / "index.json").stat().st_mtime > 30 * 86400
    lock = CACHE / "sync.lock"
    if stale and not (lock.exists() and time.time() - lock.stat().st_mtime < 600):
        CACHE.mkdir(parents=True, exist_ok=True)
        lock.write_text(str(time.time()))
        ttk = Path(__file__).with_name("ttk")
        log = open(CACHE / "sync.log", "w")
        subprocess.Popen([sys.executable, str(ttk), "docs", "sync"], stdout=log, stderr=log,
                         stdin=subprocess.DEVNULL, start_new_session=True)


def main(kind: str):
    try:
        payload = json.load(sys.stdin)
    except Exception:  # noqa: BLE001
        payload = {}
    try:
        {"post": post, "stop": stop, "session": session}[kind](payload)
    except Exception as ex:  # noqa: BLE001  never break the session because of the hook
        print(f"typst-toolkit hook error: {ex}", file=sys.stderr)
