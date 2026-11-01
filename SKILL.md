---
name: showcase-progress
description: >
  A progress bar for long agent tasks that can't be faked. Split the work into
  subtasks with time estimates; a script computes progress = finished estimated
  time / total estimated time, reports time left and an ETA, and corrects the
  ETA from real durations. Use it whenever a task will take more than ~15
  minutes or has 3+ deliverable steps (features, refactors, migrations, bulk
  fixes, long reports, multi-part analyses), when the user asks "how long will
  this take", "where are we", "what's left", "ETA", or wants a progress bar, and
  when resuming interrupted multi-step work. Also triggers on 进度条, 还要多久,
  到哪一步了, 什么时候能好, 剩多少. Skip it for one- or two-step tasks.
license: MIT
compatibility: Needs Python 3.8+ (standard library only) to run scripts/progress.py.
metadata:
  version: "1.1.0"
---

# showcase-progress

An agent's progress bar usually lies in two places: **how big the job is** and
**how much is left**. This skill puts both on the table and lets a script do the
arithmetic, so the number you post comes from a ledger, not from a feeling.

- Denominator = sum of every subtask's estimated time (visible, editable)
- Numerator = estimated time of the subtasks that are actually done
- Time left = open estimate × measured pace (only once there is real data)

Run the script as `python3 <this-skill-dir>/scripts/progress.py` (`python` on
Windows). The ledger lives in `.showcase-progress/state.json` in the project, so
the task survives restarts and can be resumed by another session or agent.

## When to use it

Use it when the task has 3+ subtasks and will take a while, when the user asks
how long / where are we, or when picking up interrupted work.

Don't use it for a two-minute fix or a pure discussion. Rule of thumb: if the
user would ask "how much longer?", use it; if they'd ask "you made a progress
bar for *this*?", don't.

## Step 1 — estimate before you start

Plan first, don't code yet. Produce 5–9 subtasks. Each one needs:

- an id and a title that names a **deliverable**, not an action
  ("token endpoint returns a JWT", not "write code")
- an estimate: `30m`, `1h30m`, `2h`, `45分钟` all work
- optionally `done_when`: one sentence that would prove it's finished

Estimate **your own** time as the agent doing the work, not how long a human
developer would take — writing a small module may take you two minutes, while
waiting on builds, installs or the user can take far longer. Estimate how long
it will really take, not how long it takes if nothing goes wrong. Uneven numbers (15m / 40m / 1h20m) mean you thought about each step; a
column of `1h, 1h, 1h` means you guessed. Spend a few minutes looking at the
code or material first — investigating is often its own first subtask.
See `references/estimating.md` for sizing rules and worked examples.

## Step 2 — create the ledger

```bash
python3 scripts/progress.py init --plan plan.json
```

```json
{
  "title": "Add password reset",
  "subtasks": [
    {"id": "Q1", "title": "Map the current auth flow", "est": "25m"},
    {"id": "Q2", "title": "Reset-token endpoint works", "est": "1h10m",
     "done_when": "POST /reset returns 202 and a token row exists"},
    {"id": "Q3", "title": "Reset page and form", "est": "1h20m"}
  ]
}
```

You can also pass `--subtasks '<json array>'` and `--title` inline. Output is
ready to paste:

```
Progress  0.0% [□□□□□□□□□□□□□□□□□□□□] plan 2h55m · 2h55m left · ETA 11:55
Next: Q1 "Map the current auth flow" est 25m
```

Output language follows the task title (a Chinese title gives Chinese output);
override with `--lang en|zh` or `SP_LANG`.

## Step 3 — move it forward at subtask boundaries

```bash
python3 scripts/progress.py update "Q1=doing"                     # starts the clock for Q1
python3 scripts/progress.py update "Q1=done" --brief              # stops it
python3 scripts/progress.py update "Q2=done" --evidence "curl returned 202, row id 17" --brief
python3 scripts/progress.py update "Q3=doing" --count 2/6 --brief
python3 scripts/progress.py update "Q4=blocked(waiting for staging access)"
python3 scripts/progress.py update "Q5=dropped(out of scope)"
```

**`doing` earns nothing.** Half-finished work isn't progress — the file exists
but doesn't run, the migration is stuck at table 200. Only `done` earns its
full estimate. The bar will jump in steps; that's what real progress looks
like.

**The one exception is a count.** If the subtask has countable units — 3 of 6
handlers migrated, 12 of 20 tests passing — `--count k/n` earns that share.
Only use it when you can point at the k things; a count is evidence, a guessed
"60%" is not, so there is no flag for that.

**Let the script time it — don't report times from memory.** When a subtask
goes `done`, the script records how long it took: from when you marked it
`doing`, or else since the previous update. Agents asked "how long did that
take?" answer in human time; this skill's own author-agent once reported 2h35m
for ten minutes of wall clock. So update **one subtask at a time, as it
happens**: mark `doing` when you start, `done` when you finish. Batching
updates at the end of a turn ruins the timing (a batch `done` isn't timed at
all). Pass `--took 40m` only when you have a real number from elsewhere — the
user told you, or a command printed its runtime.

Measured times turn the plan into a forecast: once two finished subtasks with
real durations cover 20%+ of the plan and the pace is off by more than 15%,
time left is rescaled and labelled "at current pace".

**Give `--evidence` for subtasks with `done_when`.** What did you run or see
that proves it? `check` warns about done subtasks that have a condition but no
evidence. Planning, doing and verifying are different steps — writing a plan
is not finishing the work.

## Post it, or it didn't happen

The user can't see tool output. Running `update` without pasting the result
into your reply means the skill did nothing.

1. **Each time a subtask finishes, paste the one line** that `--brief` prints,
   next to a sentence about what was done. Don't batch three updates into the
   end of the turn.
2. **When resuming or asked "where are we", post the status first**
   (`render`), then continue.
3. **At the end, post the export** — the estimate-vs-actual table is the most
   useful thing this skill produces.
4. **Never repost an unchanged number.** If nothing moved, say "still on Q3".

Use the full block (`render`) only at start, on request, and at the end; use
one line for live updates. If the user says "stop reporting, just do it",
do that.

## Changing the plan

Plans change. Use `replan`, never `init` (which starts over):

```bash
python3 scripts/progress.py replan --plan plan-v2.json --reason "split Q4: staging access pending"
python3 scripts/progress.py update "Q3=doing" --est 2h30m      # one estimate was wrong
```

Done subtasks keep their state, actual time and evidence. Adding work lowers
the percentage — that's correct, and the reason is recorded in history. Never
quietly shrink the denominator to make the bar look better.

## Finishing

```bash
python3 scripts/progress.py check      # exit 1 only when numbers can't be trusted
python3 scripts/progress.py export     # .showcase-progress/progress.json + PROGRESS.md
python3 scripts/progress.py history    # replay every step
```

## Anti-patterns

| Don't | Why | Instead |
|---|---|---|
| Run `update` but not paste the line | The user sees nothing | Paste after every done |
| Type a percentage yourself | Drifts from the ledger | Only post script output |
| Give `doing` partial credit by feel | Inflates the bar; the last 10% takes forever | `--count k/n` or nothing |
| 15 subtasks of exactly 1h each | Obviously invented, no information | 5–9 uneven, honest estimates |
| Split work finer to "make progress" | Weights are time, so it can't inflate — it only adds noise | Split by deliverable |
| Quietly edit estimates down | Destroys trust in "time left" | `--est` or `replan --reason` |
| Guess `--took` from memory | Agents report human-scale times; the ETA goes wrong | Mark `doing`/`done` as it happens; the script times it |
| Batch several `done`s at the end | No timing, and the user saw nothing live | One update per finished subtask |

## Status line (Claude Code)

If the user wants the bar always visible, `scripts/statusline.py` prints it in
Claude Code's status line from the nearest `.showcase-progress/state.json`. Set
it up only when asked, since it edits the user's settings: point `statusLine`
at `python <skill-dir>/scripts/statusline.py`, and if they already have a
status line, keep it with `--chain "<their existing command>"`.

## References

- `references/estimating.md` — sizing, splitting, worked examples
- `references/states.md` — states, counts, evidence, replanning, check rules
- `references/rendering.md` — output modes, narrow screens, GBK consoles
- `PROMPT.md` — a no-script version for chat-only models
