# Changelog

## 1.1.0 — 2026-11-02

- **The script times subtasks itself.** `done` records the time since the subtask went
  `doing` (or since the previous update). `--took` is now an override, not the source.
  Building this repo showed why: the agent reported 2h20m for 10 minutes of wall clock.
- **Status line for Claude Code** (`scripts/statusline.py`): the bar stays on screen,
  finds the nearest ledger, fades out after the task ends, and `--chain`s an existing
  status line.
- **Claude Code plugin**: `/plugin install showcase-progress --marketplace panzero666/showcase-progress`
- 50 tests (timing and status line added)

## 1.0.0 — 2026-11-01

First public release, grown out of a private skill called `agent-progress`.

- Time-weighted progress: done estimated time / total estimated time
- `doing` earns nothing; `--count k/n` gives credit for countable units
- `done_when` acceptance conditions and `--evidence`; `check` warns on done-without-evidence
- Self-correcting ETA from `--took` (2+ samples, 20%+ coverage, >15% drift)
- `replan` keeps finished work and records why
- English and Chinese output (follows the task title, or `--lang` / `SP_LANG`)
- Seconds in durations (`--took 40s`); "<1m" instead of "0m" while work is open
- Ledger at `.showcase-progress/state.json`; reads `agent-progress` schema-2 ledgers
- `PROMPT.md` / `PROMPT.zh-CN.md` for chat-only models
- Install scripts for Claude Code and `~/.agents/skills` (Codex, Gemini CLI, OpenClaw)
- 36 unit tests, CI on Linux / Windows / macOS
