# showcase-progress

**A progress bar for AI agents that can't be faked.**

[![test](https://github.com/panzero666/showcase-progress/actions/workflows/test.yml/badge.svg)](https://github.com/panzero666/showcase-progress/actions/workflows/test.yml)
![python](https://img.shields.io/badge/python-3.8%2B-blue)
![deps](https://img.shields.io/badge/dependencies-none-brightgreen)
![license](https://img.shields.io/badge/license-MIT-green)

[中文说明](README.zh-CN.md)

<p align="center"><img src="assets/demo.svg" alt="showcase-progress demo" width="820"></p>

Look at the demo again: after Q2, **time left went up** (4h10m → 4h16m). Q1 and
Q2 both took longer than estimated, so the script stopped trusting the plan and
rescaled the rest. Most agent progress reports would have said "35% done,
almost there".

## The problem

Ask an AI agent how far along it is and you get a feeling, not a number:

- "70% done" — based on what?
- Split the work into 20 tiny steps and finish the easy ones → instant 50%.
- "Just a few more minutes" — for the last hour.
- A file exists, so the step counts as done. Does it run?

## What this skill does

showcase-progress is an [Agent Skill](https://agentskills.io) — a `SKILL.md` plus
a small, dependency-free Python script. The agent plans, the script keeps the
books:

1. **Progress is weighted by estimated time, not by step count.**
   `progress = estimated time of done subtasks / estimated time of all subtasks`.
   Splitting work into more pieces can't inflate it.
2. **"In progress" earns nothing.** Only `done` counts. The one exception is a
   real count (`--count 3/6` handlers migrated) — a count is evidence, a guessed
   "60%" is not.
3. **The ETA corrects itself.** Record how long finished subtasks really took
   (`--took 40m`); once there are two real samples covering 20%+ of the plan and
   the pace is off by more than 15%, time left is rescaled and labelled
   "at current pace".
4. **Done needs evidence.** Subtasks can carry a `done_when` condition;
   `check` flags anything marked done without proof.
5. **Nothing is lost.** The ledger is a JSON file in your project. Close the
   session, come back tomorrow, `render`, continue. `replan` keeps finished work
   and records why the plan changed.

## Install

The skill is one folder. Put it where your agent looks for skills.

| Agent | Where | Status |
|---|---|---|
| **Claude Code** | `~/.claude/skills/showcase-progress` (or `.claude/skills/` in a repo) | ✅ tested on a real multi-step task |
| **Codex** (CLI / IDE / app) | `~/.agents/skills/showcase-progress` (or `.agents/skills/` in a repo) | ☑️ layout checked against docs |
| **Gemini CLI** | `~/.agents/skills/` or `~/.gemini/skills/` | ⚪ follows the spec, untested |
| **OpenClaw** | `~/.agents/skills/`, or `openclaw skills install git:panzero666/showcase-progress` | ⚪ follows the spec, untested |
| **Other Agent Skills tools** | their skills folder | ⚪ follows the spec, untested |
| **ChatGPT / DeepSeek / Gemini web / Kimi …** | paste [`PROMPT.md`](PROMPT.md) into custom instructions | 📝 prompt-only, numbers are estimates |

**macOS / Linux**

```bash
git clone https://github.com/panzero666/showcase-progress.git
cd showcase-progress && ./install.sh          # copies to ~/.claude/skills and ~/.agents/skills
```

**Windows (PowerShell)**

```powershell
git clone https://github.com/panzero666/showcase-progress.git
cd showcase-progress; .\install.ps1
```

Or copy the folder by hand. Requires Python 3.8+ on `PATH`; nothing else.

Tried it on an agent marked untested? [Open an issue](https://github.com/panzero666/showcase-progress/issues)
and tell us what happened — that's the most useful contribution right now.

## Use

You don't have to name the skill. Give your agent a task that takes a while —
"add password reset to the app", "migrate these 40 tables", "write the
quarterly report" — or ask "how long will this take?". The agent will:

1. split the work into 5–9 subtasks with honest estimates,
2. create the ledger and show the starting bar,
3. post one line each time a subtask finishes,
4. finish with an estimate-vs-actual table.

You can also call it directly: `/showcase-progress` in Claude Code,
`$showcase-progress` in Codex.

<details>
<summary><b>Script reference</b></summary>

```bash
python3 scripts/progress.py init --plan plan.json            # create the ledger
python3 scripts/progress.py update "Q1=done" --took 40m --brief
python3 scripts/progress.py update "Q2=done" --evidence "curl -> 202" --brief
python3 scripts/progress.py update "Q3=doing" --count 3/6 --brief
python3 scripts/progress.py update "Q4=blocked(waiting for access)"
python3 scripts/progress.py update "Q3=doing" --est 2h30m    # fix one estimate
python3 scripts/progress.py replan --plan v2.json --reason "split Q4"
python3 scripts/progress.py render [--mode block|bar|live|next]
python3 scripts/progress.py check                            # exit 1 if numbers can't be trusted
python3 scripts/progress.py export                           # progress.json + PROGRESS.md
python3 scripts/progress.py history                          # replay every step
```

Plan file:

```json
{
  "title": "Add password reset",
  "subtasks": [
    {"id": "Q1", "title": "Map the current auth flow", "est": "25m"},
    {"id": "Q2", "title": "Reset-token endpoint works", "est": "1h10m",
     "done_when": "POST /reset returns 202 and a token row exists"}
  ]
}
```

Durations: `40s`, `30m`, `1h30m`, `1.5h`, `90` (minutes), `45分钟`, `2小时`.

Environment: `SP_STATE` (ledger path, default `.showcase-progress/state.json`),
`SP_LANG` (`en` / `zh`; default follows the task title), `SP_ASCII=1` (`#-`
instead of `■□` for old consoles).

</details>

## FAQ

**Why does "in progress" count as zero?**
Because that's where almost all inflated progress comes from. The bar moves in
steps; that's what real progress looks like. Countable work (`--count`) is the
honest way to show movement inside a step.

**Why not three-point (PERT) estimates?**
Asking a model for optimistic / likely / pessimistic numbers triples the
guesswork and looks more precise than it is. One honest estimate, corrected by
measured pace, gets better with every finished subtask.

**Does it measure how long the model spends thinking?**
No, and it won't pretend to. "Elapsed" is wall-clock time from the ledger's
start. Real per-subtask durations come from `--took`.

**Does it update in the background?**
No. Agents don't have a resident process, so the bar is a snapshot posted at
subtask boundaries. If your host has a scheduler, have it call `render`.

**Multiple agents?**
The ledger is a plain file, so a hand-off between sessions or agents just works:
the next one runs `render` and carries on. Concurrent writers aren't supported
yet; have one coordinator do the updates.

## Contributing

Bug reports, tests on more agents, and translations are welcome. See
[CONTRIBUTING.md](CONTRIBUTING.md). Run the tests with:

```bash
python -m unittest discover -s tests
```

## License

[MIT](LICENSE)
