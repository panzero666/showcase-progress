# States, counts, evidence and checks

## Five states

| State | Credit | Meaning | How |
|---|---|---|---|
| `todo` | 0 | not started | `init` / `replan` |
| `doing` | 0 (or k/n with `--count`) | in progress | `update Q1=doing` |
| `done` | full estimate | finished | `update Q1=done --took 40m` |
| `blocked` | 0 | stuck on something outside your control | `update Q1=blocked(reason)` |
| `dropped` | 0, **and leaves the denominator** | decided not to do it | `update Q1=dropped(reason)` |

Paused work is just `doing` or `blocked` with a note; the ledger is on disk, so
"resume" means reading it back with `render`.

**`doing` earns 0** is the least intuitive and most important rule. Nearly all
inflated progress comes from "started counts as progress". Users care whether
it works, not whether a file exists.

## Countable partial progress

```bash
python3 scripts/progress.py update "Q3=doing" --count 3/6
```

Earns 3/6 of Q3's estimate. Use it only for real, countable units (files
converted, tests passing, tables migrated, pages written). The count is cleared
when the subtask becomes `done`, `todo` or `dropped`. `check` warns if a count
reaches n/n but the subtask isn't marked done — finishing the units and
verifying the whole are different things.

## Acceptance and evidence

Put `done_when` on a subtask in the plan; pass `--evidence` when you mark it
done:

```bash
python3 scripts/progress.py update "Q2=done" --evidence "POST /reset -> 202, token row 17"
```

Evidence shows up in `export`. `check` warns (doesn't fail) when a subtask with
`done_when` is done without evidence.

When resuming someone else's ledger, don't trust `done` blindly: spot-check the
evidence against the real files before building on it.

## Transitions

Any state can move to any other — reality jumps around. Moving `done` back to
`todo` lowers the percentage; say why when you post it.

## Replanning

```bash
python3 scripts/progress.py replan --plan plan-v2.json --reason "Q4 needs ops access; split out local part"
```

Kept for subtasks with the same id: `done`/`dropped` state, actual time, note,
finish time, evidence, count. A finished subtask that disappears from the new
plan is recorded in history as `removed_done`, never silently lost.

Adding work makes the percentage go down. That's honest. Correct a single
estimate with `update "Q3=doing" --est 4h`.

## Check rules

`check` exits 1 only on **errors** (numbers can't be trusted):

| Code | Trigger |
|---|---|
| `empty-plan` | no subtasks |
| `duplicate-id` | an id appears twice |
| `no-est` | a live subtask has no estimate |
| `bad-count` | count outside 0..n |
| `inconsistent` | 100% but there are still todo items |

**Warnings** don't block:

| Code | Trigger |
|---|---|
| `lopsided` | one open subtask is > 50% of remaining time (3+ open) |
| `no-evidence` | done with `done_when` but no evidence |
| `count-complete` | counted n/n but still doing |

Why two levels: warnings that block get ignored by habit.

## Time base

`started_at` (plan field or `--started`) sets "elapsed"; elapsed is wall-clock
time and includes waiting. The script does not claim to know how long the model
spent "thinking". Every command accepts `--now <ISO>` for replays and tests.
