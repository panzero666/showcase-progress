# Rendering

The output is plain text and works in any terminal or markdown view.

## Modes

```bash
progress.py update "Q2=done" --brief   # one line, right after an update
progress.py render                     # full block (default)
progress.py render --mode bar          # ■■■■□□□□ 20.5% · 4h50m left
progress.py render --mode live --label "all done"
progress.py render --mode next         # Next: Q3 "..." est 3h
```

- **one line** (`--brief`, `live`, `bar`): live updates inside a reply
- **block**: start, "where are we", hand-off, end
- **next**: when the user only wants to know what's left

Full block:

```
Progress 57.1% [■■■■■■■■■■■□□□□□□□□□] plan 4h40m · 2h45m left at current pace · ETA 15:05
· elapsed 3h20m; running 38% slower than estimated
Next: Q3 "Migrate 6 handlers" est 2h · 2/6 counted
```

## Three rules about time

1. **The ETA is an extrapolation, not a promise**: now + time left. If the user
   checks back later and nothing moved, say "still on Q3", don't repost.
2. **"plan X" and "Y left at current pace" are different things.** Don't
   shorten the second to "Y left"; the user would think the plan changed.
3. **Past the planned total, say so.** The block prints a note; respond with
   `replan` or `--est`, not with the same percentage again.

## Fallbacks

| Environment | Symptom | Fix |
|---|---|---|
| Windows console (GBK) | boxes become `?` | the script already replaces unencodable chars; or `SP_ASCII=1` → `##--` |
| No CJK font | Chinese is garbled | `--lang en`, `SP_ASCII=1` |
| Narrow screen (< 60 cols) | lines wrap | `--width 12` or `--mode bar` |
| Proportional font chat UI | bar misaligned | wrap it in a code block |

## Export

`export` writes `PROGRESS.md` (paste into a PR, report or README) and
`progress.json` (for tools). In the JSON, `percent` is a string ("69.9%"),
`fraction` is 0–1, minutes are numbers.

## What this skill doesn't do

A bar that animates by itself, background monitoring and periodic refresh all
need a resident process that an agent doesn't have. If your host has a
scheduler, have it call `render`; the skill never pretends to run in the
background.
