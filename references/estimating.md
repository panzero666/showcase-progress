# Estimating

The estimate is the bar's only denominator, so it decides whether the bar
means anything. Good news: it doesn't have to be right the first time. Record
`--took` and the script corrects the pace for you. The first estimate has to be
**honest**, not **correct**.

## Accepted formats

```
"30m"  "45min"  "1h"  "2h30m"  "1.5h"  "90"     # bare number = minutes
"40s"  "1m30s"                                  # seconds, for fast agent steps
"45分钟"  "2小时"  "1.5小时"                       # JSON numbers are minutes too
```

## Five rules

0. **Estimate your speed, not a human's.** An agent writes a 100-line module in
   a minute or two; a human-sized estimate (15m) inflates the plan 10–25× and the
   ETA is useless until the pace correction kicks in. What *is* slow for an
   agent: installs, builds, test suites, network, CI, and waiting for the user —
   estimate those by wall clock.
1. **Estimate the real time, not the lucky time.** Changing six functions takes
   an hour if nothing surprises you. Something will: an unfamiliar pattern, a
   failing test, docs that disagree with the code. The honest number is three
   hours. Underestimate and the bar sits at "20 minutes left" forever.
2. **Don't make everything a round hour.** `1h / 1h / 2h / 1h` is a guess.
   `15m / 40m / 1h20m / 3h / 20m` looks like someone thought about each step.
3. **Look before you estimate.** Spend five minutes on the files or material
   first; otherwise you're estimating the code you imagine. That look is often
   subtask one.
4. **Rough is fine.** What hurts isn't a rough first estimate, it's never
   recording actuals.

## Granularity

Aim for **5–9 subtasks**, each 10%–35% of the total.

| Symptom | Fix |
|---|---|
| More than 12 | Merge; demote small items to notes |
| One subtask > 50% of what's left | Split into two deliverables (`check` warns) |
| One subtask < 5% | Merge it or drop it |
| Fewer than 4 | You may not need a bar; just do it |

Split by **deliverable**, not by action:

```
✗ Q1 read code   Q2 write code   Q3 run tests   Q4 commit
  — "Q1 done" means nothing to the user while Q2 is half-written

✓ Q1 Notes on how the 6 handlers handle errors today        30m
  Q2 Agreed convention: error codes, logging, response body 45m
  Q3 All 6 handlers converted, app starts locally          3h
  Q4 Deployed to staging, 6 endpoints return the new shape 1h30m
  Q5 Change note for the team                              20m
```

## How the pace correction works

```
pace      = Σ actual / Σ estimate        (finished subtasks with --took only)
time left = open estimate × pace
```

Safeguards (deliberate — don't remove them):

- At least **2** finished subtasks with actuals, covering **20%+** of the plan.
  One sample is not a sample.
- A pace between 0.85 and 1.15 is treated as noise. Otherwise every number would
  look like a precise forecast.
- When active, the bar says "left at current pace", distinct from "plan".

## Worked examples

**Fix a cross-module bug** — reproduce and locate 40m · confirm root cause 50m ·
fix + regression test 2h · verify on real data 40m · write up in PR 15m.
Finding the bug is 30% of the plan; in real debugging, finding often takes
longer than fixing.

**A 20-page technical report** — structure and audience 45m · gather and check
facts and sources 3h · write sections 4h · re-check numbers against sources
1h30m · layout 40m. The classic mistake is estimating the writing as the big
part and the fact-checking as a rounding error.

**A multi-part analysis or competition problem** — one subtask per question
(model + solve + check), then figures and write-up, then a consistency pass.
With a deadline, the useful number is the ETA: if it lands after the deadline,
`replan` and cut scope now rather than at the last minute.

## When not to use a time bar

- One or two steps: just do it.
- Exploratory work where deliverables can't be listed yet: work a bit first,
  create the ledger once 3+ checkable milestones appear.
- The user said "no progress reports": do the work, report total time at the end.
