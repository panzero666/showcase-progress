#!/usr/bin/env python3
"""Claude Code status line for showcase-progress.

Keeps the progress bar visible at the bottom of Claude Code, so the user sees
it even when the agent forgets to paste it.

Claude Code pipes session JSON to this script on stdin; we look for a ledger
in the session's directory (or any parent) and print one line:

    ◆ Add password reset ■■■■■■■□□□□□ 60.6% · Q4 1/3 · 2h23m left at current pace

Prints nothing when there's no ledger, or when the task finished a while ago.

settings.json:
    "statusLine": {"type": "command",
                   "command": "python ~/.claude/skills/showcase-progress/scripts/statusline.py"}

Already have a status line? Chain it; its output is printed first:
    python .../statusline.py --chain "<your existing status line command>"

Env: SP_STATE (explicit ledger path), NO_COLOR / SP_NO_COLOR (plain output).
Standard library only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("progress", os.path.join(HERE, "progress.py"))
progress = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(progress)

LEDGERS = (
    os.path.join(".showcase-progress", "state.json"),
    os.path.join(".agent-progress", "progress-state.json"),   # agent-progress ledgers
)
WIDTH = 12
TITLE_MAX = 28
#: a finished task stays on the status line this long, then disappears
SHOW_DONE_FOR = timedelta(minutes=30)
#: show "idle 3h" once the ledger hasn't moved for this long
IDLE_AFTER = timedelta(hours=2)

GREEN, YELLOW, DIM, RESET = "\033[32m", "\033[33m", "\033[2m", "\033[0m"


def find_ledger(start: str):
    explicit = progress.env("STATE")
    if explicit:
        return explicit if os.path.exists(explicit) else None
    folder = os.path.abspath(start or os.getcwd())
    while True:
        for rel in LEDGERS:
            candidate = os.path.join(folder, rel)
            if os.path.exists(candidate):
                return candidate
        parent = os.path.dirname(folder)
        if parent == folder:
            return None
        folder = parent


def session_dir(data: dict) -> str:
    workspace = data.get("workspace") or {}
    return workspace.get("current_dir") or data.get("cwd") or workspace.get("project_dir") or ""


def status_text(data: dict, moment=None, color: bool = True) -> str:
    """The status line for this session, or '' when there's nothing to show."""
    path = find_ledger(session_dir(data))
    if not path:
        return ""
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            state = json.load(handle)
    except (OSError, ValueError):
        return ""
    if not state.get("subtasks"):
        return ""
    # A status line must never crash the UI, even on a hand-edited ledger.
    try:
        for index, sub in enumerate(state["subtasks"], start=1):
            sub.setdefault("id", "Q%d" % index)
            sub.setdefault("title", sub["id"])
            sub["state"] = str(sub.get("state") or "todo").lower()
            sub["est"] = progress.parse_minutes(sub.get("est", 0))
    except (TypeError, ValueError, AttributeError):
        return ""
    progress.LANG = progress.pick_lang(state.get("lang"), state.get("title", ""))
    moment = moment or progress.now()
    updated = progress.parse_time(state.get("updated_at") or state.get("started_at"))
    since = moment - updated

    info = progress.totals(state)
    finished = info["fraction"] >= 1.0
    if finished and since > SHOW_DONE_FOR:
        return ""

    def paint(code: str, text: str) -> str:
        return code + text + RESET if color else text

    title = str(state.get("title") or "task")
    if len(title) > TITLE_MAX:
        title = title[:TITLE_MAX - 1] + "…"
    bar = progress.make_bar(info["fraction"], WIDTH)
    filled = bar.count(progress.BAR_FULL)
    bar = paint(GREEN, bar[:filled]) + paint(DIM, bar[filled:])
    parts = [paint(GREEN if finished else YELLOW, "◆") + " " + title + " " + bar,
             progress.pct(info["fraction"])]

    current = progress.next_sub(state)
    if finished:
        parts.append("✓")
    elif current is not None:
        label = current["id"]
        if current.get("count") and current["state"] == "doing":
            label += " %d/%d" % tuple(current["count"])
        elif current["state"] == "blocked":
            label += " blocked"
        parts.append(label)
        parts.append(progress.rest_text(info))
    blocked = sum(1 for s in state["subtasks"] if s["state"] == "blocked")
    if blocked and (current is None or current["state"] != "blocked"):
        parts.append(paint(YELLOW, progress.T("n_blocked", n=blocked)))
    if not finished and since > IDLE_AFTER:
        parts.append(paint(DIM, "idle " + progress.fmt_minutes(since.total_seconds() / 60)))
    return " · ".join(parts)


def read_stdin() -> str:
    # Claude Code sends UTF-8. On Windows the locale is often GBK, which would
    # garble non-ASCII paths and the ledger would never be found.
    if sys.stdin is None or sys.stdin.isatty():
        return ""
    stream = getattr(sys.stdin, "buffer", None)
    if stream is None:
        return sys.stdin.read()
    return stream.read().decode("utf-8", "replace")


def chain_command(command: str):
    # Claude Code runs status lines through Git Bash on Windows, so existing
    # commands are bash syntax; cmd.exe (shell=True) would choke on them.
    bash = shutil.which("bash") if os.name == "nt" else None
    if bash:
        return [bash, "-c", command], False
    return command, True


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description="Claude Code status line for showcase-progress")
    parser.add_argument("--chain", help="another status line command to run first (gets the same stdin)")
    args = parser.parse_args(argv)

    raw = read_stdin()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except ValueError:
        data = {}

    if args.chain:
        try:
            command, shell = chain_command(args.chain)
            done = subprocess.run(command, shell=shell, input=raw.encode("utf-8"),
                                  stdout=subprocess.PIPE, timeout=10)
            chained = done.stdout.decode("utf-8", "replace").rstrip("\n")
            if chained:
                print(chained)
        except (OSError, subprocess.SubprocessError):
            pass

    color = not (os.environ.get("NO_COLOR") or progress.env("NO_COLOR"))
    line = status_text(data, color=color)
    if line:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
