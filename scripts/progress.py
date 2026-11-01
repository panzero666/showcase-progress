#!/usr/bin/env python3
"""showcase-progress: a progress bar for AI agents that cannot lie.

Split the task into subtasks and estimate how long each one takes.
Progress = estimated time of finished subtasks / estimated time of all subtasks.
So the percentage *is* a time percentage, and "time left" falls out for free.

Commands
    init     create the ledger (from plan.json or inline JSON)
    update   move subtasks forward; optionally record how long one actually took
    replan   change the plan mid-way without losing finished work
    check    self-check (exit 1 only when the numbers cannot be trusted)
    render   print the bar / status block
    history  replay every recorded step
    export   write progress.json + PROGRESS.md

Standard library only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from datetime import datetime, timedelta

SCHEMA = 3

# ---------------------------------------------------------------------------
# Messages (en / zh)
# ---------------------------------------------------------------------------

MESSAGES = {
    "en": {
        "no_duration": "no duration given",
        "bad_duration": "can't read duration {value!r} (use 30m / 2h / 1h30m)",
        "bad_time": "can't read time {value!r} (use ISO, e.g. 2026-10-31T09:00:00)",
        "no_ledger": "no ledger at {path} - run `progress.py init` first",
        "bad_ledger": "ledger is not valid JSON ({path}): {exc}",
        "ambiguous": "{key!r} matches several subtasks: {ids}",
        "no_subtask": "no subtask {key!r}; have: {ids}",
        "no_reason": "no reason given",
        "next_none": "Next: nothing left - ready to deliver.",
        "next_blocked": "Next: {id} \"{title}\" is blocked - {note}",
        "next": "Next: {id} \"{title}\" est {est}",
        "next_count": " · {k}/{n} counted",
        "next_done_when": " · done when: {cond}",
        "still_blocked": " ({ids} still blocked: {note})",
        "left": "{t} left",
        "left_pace": "{t} left at current pace",
        "head": "Progress {pct} [{bar}] plan {plan} · {rest}",
        "eta": " · ETA {hhmm}",
        "elapsed": "elapsed {t}",
        "drift": "running {pct}% {dir} than estimated",
        "slower": "slower",
        "faster": "faster",
        "over_plan": "past the planned total - the plan itself needs re-estimating",
        "n_blocked": "{n} blocked",
        "n_dropped": "{n} dropped",
        "sep": "; ",
        "n_done": "{d}/{n} done",
        "empty_plan_err": "empty-plan: no subtasks, the bar has no denominator",
        "dup_err": "duplicate-id: {id} appears more than once",
        "no_est_err": "no-est: {id} has no estimate and cannot count toward progress",
        "inconsistent_err": "inconsistent: progress is 100% but there are still todo items",
        "bad_count_err": "bad-count: {id} counts {k}/{n}",
        "lopsided_warn": "lopsided: {id} is {pct}% of the remaining time - the bar will jump; consider splitting",
        "no_evidence_warn": "no-evidence: {id} is done but has no evidence for \"{cond}\"",
        "count_full_warn": "count-complete: {id} counted {n}/{n} but is not marked done",
        "plan_no_subtasks": "the plan has no subtasks - the bar needs at least one",
        "bad_state": "subtask {id}: unknown state {state!r} (use: {states})",
        "sub_err": "subtask {id}: {exc}",
        "sub_actual_err": "subtask {id} actual time: {exc}",
        "old_schema": "existing ledger {path} uses the old weight-based format, which is incompatible.\n"
                      "  Use --force to rebuild it, or pick another --state path.",
        "overwrite_warn": "warning: overwriting existing ledger (was {pct}); use replan to keep progress\n",
        "not_move": "{chunk!r} is not ID=state (separate moves with commas, put notes in parentheses)",
        "unknown_state": "unknown state {state!r} (use: {states})",
        "single_only": "{flag} works only when updating exactly one subtask",
        "bad_count": "--count wants k/n with 0 <= k <= n, got {value!r}",
        "flag_err": "{flag}: {exc}",
        "replan_needs": "replan needs the full new subtask list (--plan or --subtasks)",
        "no_history": "no history yet",
        "check_ok": "OK",
        "check_n": "{n} to review",
        "wrote": "wrote {a} and {b}",
        "md_plan": "Planned total",
        "md_done": "Done",
        "md_left": "Remaining",
        "md_pace": "Actual pace: {pct}% {dir} than estimated",
        "md_head": "| Subtask | State | Est | Actual | Evidence / note |",
        "subtask": "subtask {i}",
    },
    "zh": {
        "no_duration": "没有填耗时",
        "bad_duration": "看不懂的耗时 {value!r}（用 30m / 2h / 1h30m 这种写法）",
        "bad_time": "时间格式看不懂：{value!r}（用 ISO 格式，如 2026-10-31T09:00:00）",
        "no_ledger": "没有账本：{path} —— 先跑 `progress.py init`",
        "bad_ledger": "账本不是合法 JSON（{path}）：{exc}",
        "ambiguous": "{key!r} 同时匹配多个子任务：{ids}",
        "no_subtask": "没有子任务 {key!r}；现有：{ids}",
        "no_reason": "没写原因",
        "next_none": "下一步：没有剩余子任务，可以交付了。",
        "next_blocked": "下一步：{id}「{title}」卡住了 —— {note}",
        "next": "下一步：{id}「{title}」计划 {est}",
        "next_count": " · 已数到 {k}/{n}",
        "next_done_when": " · 验收：{cond}",
        "still_blocked": "（{ids} 仍卡着：{note}）",
        "left": "剩 {t}",
        "left_pace": "按当前速度剩 {t}",
        "head": "进度 {pct} [{bar}] 计划 {plan} · {rest}",
        "eta": " · 约 {hhmm} 完成",
        "elapsed": "已开工 {t}",
        "drift": "实际比预估{dir} {pct}%",
        "slower": "慢",
        "faster": "快",
        "over_plan": "已超过计划总耗时，计划本身该重估了",
        "n_blocked": "卡住 {n} 项",
        "n_dropped": "已砍掉 {n} 项",
        "sep": "；",
        "n_done": "{d}/{n} 完成",
        "empty_plan_err": "empty-plan: 没有子任务，进度条没有分母",
        "dup_err": "duplicate-id: {id} 出现了多次",
        "no_est_err": "no-est: {id} 没有预计耗时，没法参与进度",
        "inconsistent_err": "inconsistent: 进度已经 100% 却还有 todo",
        "bad_count_err": "bad-count: {id} 的计数是 {k}/{n}",
        "lopsided_warn": "lopsided: {id} 占了剩余时间的 {pct}%，进度条会一跳一大步，考虑再拆",
        "no_evidence_warn": "no-evidence: {id} 标了 done，但没给「{cond}」的证据",
        "count_full_warn": "count-complete: {id} 已数到 {n}/{n}，却还没标 done",
        "plan_no_subtasks": "计划里没有子任务 —— 进度条至少需要一个",
        "bad_state": "子任务 {id} 的状态不认识：{state!r}（可用：{states}）",
        "sub_err": "子任务 {id}：{exc}",
        "sub_actual_err": "子任务 {id} 的实际耗时：{exc}",
        "old_schema": "已有账本 {path} 是旧版格式（按权重算进度），和当前版本不兼容。\n"
                      "  确认要丢掉它就用 --force 重建，或换个 --state 路径。",
        "overwrite_warn": "warning: 覆盖已有账本（原进度 {pct}）；不想丢进度请用 replan\n",
        "not_move": "{chunk!r} 不是 ID=状态 的形式（多个动作用逗号分隔，备注写在括号里）",
        "unknown_state": "状态不认识：{state!r}（可用：{states}）",
        "single_only": "{flag} 只能在一次只更新一个子任务时用",
        "bad_count": "--count 要写成 k/n，且 0 <= k <= n，收到 {value!r}",
        "flag_err": "{flag}：{exc}",
        "replan_needs": "replan 需要完整的新子任务列表（--plan 或 --subtasks）",
        "no_history": "还没有历史记录",
        "check_ok": "OK",
        "check_n": "{n} 条待看",
        "wrote": "已写出 {a} 和 {b}",
        "md_plan": "计划总耗时",
        "md_done": "已完成",
        "md_left": "预计剩余",
        "md_pace": "实际速度：比预估{dir} {pct}%",
        "md_head": "| 子任务 | 状态 | 预计 | 实际 | 证据 / 备注 |",
        "subtask": "子任务 {i}",
    },
}

def env(name: str):
    """SP_<name>, falling back to the AGP_<name> used by agent-progress."""
    return os.environ.get("SP_" + name) or os.environ.get("AGP_" + name)


LANG = "en"
CJK_RE = re.compile(r"[一-鿿]")


def pick_lang(explicit=None, text: str = "") -> str:
    """--lang > SP_LANG > language of the task title > English."""
    for choice in (explicit, env("LANG")):
        if choice and choice.lower()[:2] in MESSAGES:
            return choice.lower()[:2]
    return "zh" if CJK_RE.search(text or "") else "en"


def T(key: str, **kw) -> str:
    return MESSAGES[LANG][key].format(**kw)


# ---------------------------------------------------------------------------
# Time
# ---------------------------------------------------------------------------

#: unit -> minutes; a bare number means minutes
UNITS = {"h": 60, "hr": 60, "hour": 60, "hours": 60, "小时": 60, "时": 60,
         "m": 1, "min": 1, "mins": 1, "minute": 1, "minutes": 1, "分钟": 1, "分": 1,
         "s": 1 / 60, "sec": 1 / 60, "秒": 1 / 60}

DURATION_RE = re.compile(r"(\d+(?:\.\d+)?)\s*([a-zA-Z一-鿿]*)")
COUNT_RE = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")


def parse_minutes(value) -> float:
    """'1h30m' / '90' / '2小时' / '45m' -> minutes (float)."""
    if value is None:
        raise ValueError(T("no_duration"))
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower()
    if not text:
        raise ValueError(T("no_duration"))
    total, seen = 0.0, False
    for number, unit in DURATION_RE.findall(text):
        unit = unit.strip()
        if unit in UNITS:
            factor = UNITS[unit]
        elif unit == "":
            factor = 1.0
        else:
            raise ValueError(T("bad_duration", value=value))
        total += float(number) * factor
        seen = True
    if not seen:
        raise ValueError(T("bad_duration", value=value))
    return total


def fmt_minutes(minutes: float) -> str:
    """minutes -> '2h10m' / '45m' / '<1m'."""
    minutes = max(0.0, float(minutes))
    if minutes <= 0:
        return "0m"
    if minutes < 1:
        # Work is still open; "0m left" would read as finished.
        return "<1m"
    if minutes < 60:
        return "%dm" % int(round(minutes))
    hours = int(minutes // 60)
    rest = int(round(minutes - hours * 60))
    if rest == 0:
        return "%dh" % hours
    if rest == 60:
        return "%dh" % (hours + 1)
    return "%dh%02dm" % (hours, rest)


def now() -> datetime:
    return datetime.now().astimezone()


def parse_time(value) -> datetime:
    """Parse ISO time; a value without a timezone is read as local time.

    Without that, a naive datetime minus now() raises
    "can't subtract offset-naive and offset-aware datetimes".
    """
    if not value:
        return now()
    try:
        moment = datetime.fromisoformat(str(value))
    except ValueError:
        die(T("bad_time", value=value))
        raise AssertionError
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=now().tzinfo)
    return moment


def stamp(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

STATES = ["todo", "doing", "done", "blocked", "dropped"]

#: Only done earns credit. doing earns 0 on purpose: half-done work is not
#: progress. The one exception is a *counted* doing (--count k/n), because a
#: count is evidence, not an opinion.
ACTIVE = ("todo", "doing", "done", "blocked")

BAR_FULL, BAR_EMPTY = "■", "□"
if env("ASCII"):
    BAR_FULL, BAR_EMPTY = "#", "-"

DEFAULT_WIDTH = 20
DEFAULT_STATE = ".showcase-progress/state.json"


def safe_stdout() -> None:
    """Windows consoles are often GBK; replace what can't be encoded instead of crashing."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass


def die(message: str, code: int = 1):
    sys.stderr.write("showcase-progress: %s\n" % message)
    raise SystemExit(code)


def load(path: str) -> dict:
    if not os.path.exists(path):
        die(T("no_ledger", path=path))
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except ValueError as exc:
        die(T("bad_ledger", path=path, exc=exc))
    raise AssertionError


def save(path: str, state: dict) -> None:
    state["updated_at"] = stamp(now())
    folder = os.path.dirname(os.path.abspath(path))
    if folder and not os.path.isdir(folder):
        os.makedirs(folder, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(tmp, path)


def find(state: dict, key: str) -> dict:
    key = key.strip().lower()
    for sub in state["subtasks"]:
        if sub["id"].lower() == key:
            return sub
    hits = [s for s in state["subtasks"] if key in s["title"].lower()]
    if len(hits) == 1:
        return hits[0]
    ids = ", ".join(s["id"] for s in (hits or state["subtasks"]))
    if hits:
        die(T("ambiguous", key=key, ids=ids))
    die(T("no_subtask", key=key, ids=ids))


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------


def active_subs(state: dict) -> list:
    return [s for s in state["subtasks"] if s["state"] in ACTIVE]


def credit(sub: dict) -> float:
    """Share of a subtask's estimate that counts as finished (0..1)."""
    if sub["state"] == "done":
        return 1.0
    count = sub.get("count")
    if sub["state"] == "doing" and count and count[1] > 0:
        return max(0.0, min(1.0, count[0] / float(count[1])))
    return 0.0


def totals(state: dict) -> dict:
    """The planned books + the actual books."""
    subs = state["subtasks"]
    living = active_subs(state)
    plan = sum(s["est"] for s in living)
    done = sum(s["est"] * credit(s) for s in living)
    open_plan = plan - done

    with_actual = [s for s in subs if s.get("actual") and s["state"] == "done"]
    factor = None
    # One sample is not a sample: only correct the remaining time once at least
    # two subtasks have real durations covering 20%+ of the plan. Otherwise we
    # just amplify noise into an "ETA".
    if len(with_actual) >= 2:
        est_sum = sum(s["est"] for s in with_actual)
        act_sum = sum(s["actual"] for s in with_actual)
        if est_sum > 0 and (plan <= 0 or est_sum / plan >= 0.2):
            measured = act_sum / est_sum
            # Within 15% is noise. Showing it would make every number look like
            # a precise forecast.
            if abs(measured - 1.0) > 0.15:
                factor = measured

    remaining = open_plan * (factor if factor else 1.0)
    fraction = 1.0 if plan <= 0 else done / plan
    return {
        "plan": plan,
        "done": done,
        "open": open_plan,
        "fraction": fraction,
        "factor": factor,
        "remaining": remaining,
        "blocked": sum(s["est"] for s in living if s["state"] == "blocked"),
    }


def wall_clock(state: dict, moment: datetime) -> timedelta:
    return moment - parse_time(state.get("started_at"))


def make_bar(fraction: float, width: int) -> str:
    fraction = max(0.0, min(1.0, fraction))
    filled = int(math.floor(fraction * width + 0.5))
    if 0 < filled < width:
        # Barely started shouldn't look empty; almost done shouldn't look full.
        filled = max(1, min(width - 1, filled))
    elif filled == width and fraction < 1.0:
        filled = width - 1
    elif filled == 0 and fraction > 0:
        filled = 1
    return BAR_FULL * filled + BAR_EMPTY * (width - filled)


def pct(fraction: float) -> str:
    return "%.1f%%" % (fraction * 100)


def rest_text(info: dict) -> str:
    # Once real durations rescale the remaining time, say so - otherwise
    # "plan 6h · 7h30m left" looks self-contradictory.
    if info["factor"]:
        return T("left_pace", t=fmt_minutes(info["remaining"]))
    return T("left", t=fmt_minutes(info["remaining"]))


def next_sub(state: dict):
    living = active_subs(state)
    for wanted in ("doing", "todo", "blocked"):
        for sub in living:
            if sub["state"] == wanted:
                return sub
    return None


def next_hint(state: dict) -> str:
    sub = next_sub(state)
    blocked = [s for s in state["subtasks"] if s["state"] == "blocked"]
    if sub is None:
        return T("next_none")
    if sub["state"] == "blocked":
        return T("next_blocked", id=sub["id"], title=sub["title"],
                 note=sub.get("note") or T("no_reason"))
    hint = T("next", id=sub["id"], title=sub["title"], est=fmt_minutes(sub["est"]))
    if sub.get("count") and sub["state"] == "doing":
        hint += T("next_count", k=sub["count"][0], n=sub["count"][1])
    if sub.get("done_when"):
        hint += T("next_done_when", cond=sub["done_when"])
    # Other work can move, but the blocked item still holds planned time.
    # If we don't say so, the user assumes it vanished from the plan.
    if blocked:
        hint += T("still_blocked", ids=", ".join(s["id"] for s in blocked),
                  note=blocked[0].get("note") or T("no_reason"))
    return hint


def render_bar(state: dict, width: int, moment: datetime) -> str:
    info = totals(state)
    head = T("head", pct="%5s" % pct(info["fraction"]),
             bar=make_bar(info["fraction"], width),
             plan=fmt_minutes(info["plan"]), rest=rest_text(info))
    if info["fraction"] < 1.0:
        eta = moment + timedelta(minutes=info["remaining"])
        head += T("eta", hhmm=eta.strftime("%H:%M"))
    return head


def drift_text(factor: float, key: str = "drift") -> str:
    return T(key, pct=round(abs(factor - 1.0) * 100),
             dir=T("slower") if factor > 1 else T("faster"))


def render_block(state: dict, width: int, moment: datetime) -> str:
    info = totals(state)
    lines = [render_bar(state, width, moment)]

    notes = []
    elapsed_min = wall_clock(state, moment).total_seconds() / 60.0
    if elapsed_min >= 1:
        notes.append(T("elapsed", t=fmt_minutes(elapsed_min)))
        if info["factor"]:
            notes.append(drift_text(info["factor"]))
        if info["plan"] > 0 and elapsed_min > info["plan"] * 1.5:
            notes.append(T("over_plan"))
    blocked = [s for s in state["subtasks"] if s["state"] == "blocked"]
    if blocked:
        notes.append(T("n_blocked", n=len(blocked)))
    dropped = [s for s in state["subtasks"] if s["state"] == "dropped"]
    if dropped:
        notes.append(T("n_dropped", n=len(dropped)))
    if notes:
        lines.append("· " + T("sep").join(notes))

    lines.append(next_hint(state))
    return "\n".join(lines)


def render_line(state: dict, moment: datetime, width: int = DEFAULT_WIDTH, label: str = "") -> str:
    """One-line progress, made for "post it every time a subtask finishes".

    A full block is too heavy for live updates. This line has to stand alone:
    how far, how much is left, and what just happened.
    """
    info = totals(state)
    done = [s for s in state["subtasks"] if s["state"] == "done"]
    parts = [make_bar(info["fraction"], width), pct(info["fraction"])]
    if label:
        parts.append(label)
    elif done:
        parts.append(T("n_done", d=len(done), n=len(active_subs(state) or state["subtasks"])))
    parts.append(rest_text(info))
    return " · ".join(parts)


# ---------------------------------------------------------------------------
# Self-check: only block on numbers that can't be trusted
# ---------------------------------------------------------------------------


def check(state: dict) -> dict:
    errors, warnings = [], []
    subs = state.get("subtasks") or []
    if not subs:
        return {"errors": [T("empty_plan_err")], "warnings": []}

    ids = [s["id"] for s in subs]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        errors.append(T("dup_err", id=dup))

    for sub in subs:
        if sub["state"] in ACTIVE and sub["est"] <= 0:
            errors.append(T("no_est_err", id=sub["id"]))
        count = sub.get("count")
        if count:
            k, n = count
            if n <= 0 or k < 0 or k > n:
                errors.append(T("bad_count_err", id=sub["id"], k=k, n=n))
            elif k == n and sub["state"] == "doing":
                warnings.append(T("count_full_warn", id=sub["id"], n=n))
        if sub["state"] == "done" and sub.get("done_when") and not sub.get("evidence"):
            warnings.append(T("no_evidence_warn", id=sub["id"], cond=sub["done_when"]))

    info = totals(state)
    if info["fraction"] >= 1.0 and any(s["state"] == "todo" for s in subs):
        errors.append(T("inconsistent_err"))

    living = [s for s in active_subs(state) if s["state"] in ("todo", "doing", "blocked")]
    if len(living) >= 3 and info["open"] > 0:
        for sub in living:
            share = sub["est"] * (1 - credit(sub)) / info["open"]
            if share > 0.5:
                warnings.append(T("lopsided_warn", id=sub["id"], pct=round(share * 100)))
    return {"errors": errors, "warnings": warnings}


# ---------------------------------------------------------------------------
# Parsing plans and moves
# ---------------------------------------------------------------------------


def read_plan(args: argparse.Namespace) -> dict:
    payload = {}
    if getattr(args, "plan", None):
        with open(args.plan, "r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    if getattr(args, "subtasks", None):
        payload["subtasks"] = json.loads(args.subtasks)
    return payload


def build(payload: dict) -> list:
    raw = payload.get("subtasks") or []
    if not raw:
        die(T("plan_no_subtasks"))
    subs = []
    for index, item in enumerate(raw, start=1):
        sub = dict(item)
        sub.setdefault("id", "Q%d" % index)
        sub.setdefault("title", T("subtask", i=index))
        sub.setdefault("state", "todo")
        sub["state"] = str(sub["state"]).lower().strip()
        if sub["state"] not in STATES:
            die(T("bad_state", id=sub["id"], state=sub["state"], states=", ".join(STATES)))
        try:
            sub["est"] = parse_minutes(sub.get("est", sub.get("effort", sub.get("hours"))))
        except ValueError as exc:
            die(T("sub_err", id=sub["id"], exc=exc))
        if "actual" in sub and sub["actual"] not in (None, ""):
            try:
                sub["actual"] = parse_minutes(sub["actual"])
            except ValueError as exc:
                die(T("sub_actual_err", id=sub["id"], exc=exc))
        sub.setdefault("note", "")
        subs.append(sub)
    return subs


def split_top_level(raw: str) -> list:
    """Split on commas, except commas inside parentheses.

    Notes are free text and naturally contain commas:
    `Q4=done(title, sidebar, narrow screens)`. The parentheses stay in the
    chunk, otherwise the depth of `(a,b)` would never return to zero.
    """
    chunks, buf, depth = [], [], 0
    for ch in raw:
        if ch in "(（":
            depth += 1
        elif ch in ")）":
            depth = max(0, depth - 1)
        if ch in ",，" and depth == 0:
            chunks.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    chunks.append("".join(buf))
    return [c.strip() for c in chunks if c.strip()]


def parse_moves(raw: str) -> list:
    if raw.strip().startswith("["):
        return [
            (str(m["id"]), str(m["state"]).lower(), m.get("note") or "")
            for m in json.loads(raw)
        ]
    moves = []
    for chunk in split_top_level(raw):
        if "=" not in chunk:
            die(T("not_move", chunk=chunk))
        key, rest = chunk.split("=", 1)
        note = ""
        rest = rest.replace("（", "(").replace("）", ")")
        if "(" in rest and rest.rstrip().endswith(")"):
            rest, note = rest.split("(", 1)
            note = note.rstrip().rstrip(")").strip()
        moves.append((key.strip(), rest.strip().lower(), note))
    return moves


def parse_count(value: str) -> list:
    match = COUNT_RE.match(str(value))
    if not match:
        die(T("bad_count", value=value))
    k, n = int(match.group(1)), int(match.group(2))
    if n <= 0 or k > n:
        die(T("bad_count", value=value))
    return [k, n]


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


def snapshot(state: dict, moment: datetime, event: str, detail) -> dict:
    """Record what the bar looked like at this moment.

    Without snapshots you can't reconstruct "what should have been posted
    then" - you could only guess from estimates. With them, `history` replays
    every step exactly.
    """
    info = totals(state)
    return {
        "at": stamp(moment),
        "event": event,
        "detail": detail,
        "percent": round(info["fraction"] * 100, 1),
        "remaining": round(info["remaining"], 1),
        "plan": round(info["plan"], 1),
        "factor": round(info["factor"], 3) if info["factor"] else None,
        "states": {s["id"]: s["state"] for s in state["subtasks"]},
    }


def remember(state: dict, moment: datetime, event: str, detail) -> None:
    state.setdefault("history", []).append(snapshot(state, moment, event, detail))
    if len(state["history"]) > 200:      # don't let long tasks bloat the ledger
        state["history"] = state["history"][-200:]


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_init(args: argparse.Namespace) -> int:
    global LANG
    payload = read_plan(args)
    if args.title:
        payload["title"] = args.title
    if args.started:
        payload["started_at"] = stamp(parse_time(args.started))
    LANG = pick_lang(args.lang or payload.get("lang"), payload.get("title", ""))

    subs = build(payload)
    started = payload.get("started_at") or stamp(now())

    previous = None
    if os.path.exists(args.state):
        try:
            previous = load(args.state)
        except SystemExit:
            previous = None
        # schema 1 was the "weights + evidence" ledger; converting it would miscount
        if (previous and previous.get("schema") not in (2, SCHEMA)
                and previous.get("subtasks") and not args.force):
            die(T("old_schema", path=args.state))
        if previous and previous.get("subtasks") and not args.force:
            sys.stderr.write(T("overwrite_warn", pct=pct(totals(previous)["fraction"])))

    state = {
        "schema": SCHEMA,
        "title": payload.get("title") or "task",
        "lang": LANG,
        "started_at": started,
        "subtasks": subs,
        "history": (previous or {}).get("history") or [],
    }
    remember(state, parse_time(args.now), "init", "")
    save(args.state, state)
    if not args.quiet:
        print(render_block(state, args.width, parse_time(args.now)))
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    state = load_with_lang(args)
    moment = parse_time(args.now)
    moved = []
    for key, new_state, note in parse_moves(args.moves):
        if new_state not in STATES:
            die(T("unknown_state", state=new_state, states=", ".join(STATES)))
        sub = find(state, key)
        old = sub["state"]
        sub["state"] = new_state
        if note:
            sub["note"] = note
        if new_state == "done":
            sub["finished_at"] = stamp(moment)
        if new_state in ("done", "todo", "dropped"):
            sub.pop("count", None)       # a count only means something while doing
        if new_state == "todo":
            sub.pop("finished_at", None)
        moved.append({"id": sub["id"], "from": old, "to": new_state})

    def only_one(flag: str) -> dict:
        if len(moved) != 1:
            die(T("single_only", flag=flag))
        return find(state, moved[0]["id"])

    if args.took:
        try:
            only_one("--took")["actual"] = parse_minutes(args.took)
        except ValueError as exc:
            die(T("flag_err", flag="--took", exc=exc))
    if args.est:
        try:
            only_one("--est")["est"] = parse_minutes(args.est)
        except ValueError as exc:
            die(T("flag_err", flag="--est", exc=exc))
    if args.count:
        target = only_one("--count")
        target["count"] = parse_count(args.count)
        moved[0]["count"] = "%d/%d" % tuple(target["count"])
    if args.evidence:
        only_one("--evidence")["evidence"] = args.evidence

    remember(state, moment, "update", moved)
    save(args.state, state)
    if args.brief:
        # One call returns the updated line - no extra round trip to render.
        label = " ".join(
            "%s %s" % (m["id"], m.get("count") or m["to"]) for m in moved
        )
        print(render_line(state, moment, args.width, label))
    elif not args.quiet:
        print(render_block(state, args.width, moment))
    return 0


def cmd_replan(args: argparse.Namespace) -> int:
    state = load_with_lang(args)
    moment = parse_time(args.now)
    before = {s["id"]: dict(s) for s in state["subtasks"]}
    before_pct = pct(totals(state)["fraction"])

    payload = read_plan(args)
    if not payload.get("subtasks"):
        die(T("replan_needs"))

    subs = build(payload)
    # Replanning never zeroes out finished work.
    for sub in subs:
        old = before.get(sub["id"])
        if not old:
            continue
        if old["state"] in ("done", "dropped"):
            sub["state"] = old["state"]
        for field in ("note", "actual", "finished_at", "evidence", "count"):
            if old.get(field) and not sub.get(field):
                sub[field] = old[field]
    removed_done = [
        sid for sid, old in before.items()
        if old["state"] == "done" and sid not in {s["id"] for s in subs}
    ]

    state["subtasks"] = subs
    remember(state, moment, "replan",
             {"before": before_pct, "removed_done": removed_done, "reason": args.reason or ""})
    save(args.state, state)
    print(render_block(state, args.width, moment))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    state = load_with_lang(args)
    findings = check(state)
    info = totals(state)
    report = {
        "title": state.get("title"),
        "percent": pct(info["fraction"]),
        "plan_minutes": round(info["plan"], 1),
        "remaining_minutes": round(info["remaining"], 1),
        "speed_factor": round(info["factor"], 3) if info["factor"] else None,
        "subtasks": [
            {"id": s["id"], "state": s["state"], "est": round(s["est"], 1),
             "actual": round(s["actual"], 1) if s.get("actual") else None,
             "count": s.get("count")}
            for s in state["subtasks"]
        ],
        "errors": findings["errors"],
        "warnings": findings["warnings"],
        "ok": not findings["errors"],
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        rows = findings["errors"] + findings["warnings"]
        print("%s  %s" % (report["percent"], T("check_ok") if not rows else T("check_n", n=len(rows))))
        for row in rows:
            print(" - %s" % row)
    return 0 if not findings["errors"] else 1


def cmd_history(args: argparse.Namespace) -> int:
    state = load_with_lang(args)
    history = state.get("history") or []
    if not history:
        print(T("no_history"))
        return 0
    rows = history[-int(args.limit or 20):]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    for item in rows:
        when = item.get("at", "")
        short = when[11:16] if len(when) >= 16 else when
        if "percent" not in item:
            # very old ledgers kept events without snapshots
            print("%s  %-8s %s" % (short, item.get("event", ""), item.get("detail", "")))
            continue
        print("%s  %s %5.1f%%  %-6s %s" % (
            short, make_bar(item["percent"] / 100.0, args.width), item["percent"],
            item.get("event", ""), T("left", t=fmt_minutes(item.get("remaining", 0))),
        ))
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    state = load_with_lang(args)
    moment = parse_time(args.now)
    if args.mode == "bar":
        info = totals(state)
        print("%s %s · %s" % (make_bar(info["fraction"], args.width),
                              pct(info["fraction"]), rest_text(info)))
    elif args.mode == "next":
        print(next_hint(state))
    elif args.mode == "live":
        print(render_line(state, moment, args.width, args.label or ""))
    else:
        print(render_block(state, args.width, moment))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    state = load_with_lang(args)
    info = totals(state)
    payload = {
        "title": state.get("title"),
        "percent": pct(info["fraction"]),
        "fraction": round(info["fraction"], 4),
        "plan_minutes": round(info["plan"], 1),
        "plan_human": fmt_minutes(info["plan"]),
        "done_minutes": round(info["done"], 1),
        "remaining_minutes": round(info["remaining"], 1),
        "remaining_human": fmt_minutes(info["remaining"]),
        "speed_factor": round(info["factor"], 3) if info["factor"] else None,
        "started_at": state.get("started_at"),
        "updated_at": state.get("updated_at"),
        "subtasks": [
            {
                "id": s["id"],
                "title": s["title"],
                "state": s["state"],
                "est_minutes": round(s["est"], 1),
                "est_human": fmt_minutes(s["est"]),
                "actual_minutes": round(s["actual"], 1) if s.get("actual") else None,
                "count": s.get("count"),
                "done_when": s.get("done_when", ""),
                "evidence": s.get("evidence", ""),
                "note": s.get("note", ""),
            }
            for s in state["subtasks"]
        ],
        "check": check(state),
    }
    for path in (args.json_out, args.md_out):
        folder = os.path.dirname(os.path.abspath(path))
        if folder and not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)
    with open(args.json_out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    lines = [
        "# %s" % payload["title"],
        "",
        "**%s**  %s" % (payload["percent"], make_bar(info["fraction"], 20)),
        "",
        "- %s: %s" % (T("md_plan"), payload["plan_human"]),
        "- %s: %s" % (T("md_done"), fmt_minutes(info["done"])),
        "- %s: %s" % (T("md_left"), payload["remaining_human"]),
    ]
    if payload["speed_factor"]:
        lines.append("- " + drift_text(payload["speed_factor"], "md_pace"))
    lines += ["", T("md_head"), "|---|---|---|---|---|"]
    for sub in payload["subtasks"]:
        state_text = sub["state"]
        if sub["count"] and sub["state"] == "doing":
            state_text += " %d/%d" % tuple(sub["count"])
        detail = " · ".join(x for x in (sub["evidence"], sub["note"]) if x) or "—"
        lines.append("| %s %s | %s | %s | %s | %s |" % (
            sub["id"], sub["title"], state_text, sub["est_human"],
            fmt_minutes(sub["actual_minutes"]) if sub["actual_minutes"] else "—",
            detail.replace("|", "\\|"),
        ))
    lines += ["", next_hint(state), ""]
    with open(args.md_out, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    print(T("wrote", a=args.json_out, b=args.md_out))
    return 0


def load_with_lang(args: argparse.Namespace) -> dict:
    global LANG
    state = load(args.state)
    LANG = pick_lang(args.lang or state.get("lang"), state.get("title", ""))
    return state


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="progress.py",
        description="A progress bar for AI agents whose denominator is estimated time.",
    )
    parser.add_argument("--state", default=env("STATE") or DEFAULT_STATE,
                        help="ledger path (env SP_STATE overrides the default)")
    parser.add_argument("--lang", choices=sorted(MESSAGES),
                        help="output language (env SP_LANG; default follows the task title)")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--width", type=int, default=DEFAULT_WIDTH, help="bar width, default 20")
    common.add_argument("--now", help="treat this ISO time as now (for replays and tests)")

    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("init", parents=[common], help="create the ledger")
    p.add_argument("--plan", help="path to plan.json")
    p.add_argument("--subtasks", help="inline JSON array of subtasks")
    p.add_argument("--title")
    p.add_argument("--started", help="start time (ISO), default now")
    p.add_argument("--force", action="store_true", help="overwrite an incompatible ledger")
    p.add_argument("--quiet", action="store_true", help="create the ledger without printing")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("update", parents=[common], help="move subtasks forward")
    p.add_argument("moves", help="Q2=done,Q3=blocked(reason) or a JSON array")
    p.add_argument("--took", help="how long this subtask actually took, e.g. 40m")
    p.add_argument("--est", help="correct this subtask's estimate")
    p.add_argument("--count", help="countable partial progress while doing, e.g. 3/6")
    p.add_argument("--evidence", help="what proves this subtask is done")
    p.add_argument("--brief", action="store_true", help="print one line (for live posting)")
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("replan", parents=[common], help="change the plan, keep finished work")
    p.add_argument("--plan")
    p.add_argument("--subtasks")
    p.add_argument("--reason")
    p.set_defaults(func=cmd_replan)

    p = sub.add_parser("check", help="self-check; exit 1 when numbers can't be trusted")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("history", parents=[common], help="replay every recorded step")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_history)

    p = sub.add_parser("render", parents=[common], help="print the bar or status block")
    p.add_argument("--mode", choices=["bar", "block", "next", "live"], default="block",
                   help="live = one line, for posting after each finished subtask")
    p.add_argument("--label", help="extra text for live mode, e.g. 'Q2 done'")
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("export", parents=[common], help="write progress.json + PROGRESS.md")
    p.add_argument("--json-out", default=".showcase-progress/progress.json")
    p.add_argument("--md-out", default=".showcase-progress/PROGRESS.md")
    p.set_defaults(func=cmd_export)

    return parser


def main(argv=None) -> int:
    global LANG
    safe_stdout()
    LANG = pick_lang(None)
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "cmd", None):
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
