# showcase-progress — prompt-only version

For chat models that can't run scripts (ChatGPT, DeepSeek, Gemini, Kimi, Claude.ai
without tools, …). Paste the block below into custom instructions, a GPT / Gem /
Project system prompt, or at the start of a conversation.

**Limitation, stated up front:** without a script, the model does the arithmetic
itself and there is no ledger on disk. The rules below make it show its sums so
you can check them, but treat the numbers as **estimates**. Agents that can run
code should use the full skill (`SKILL.md` + `scripts/progress.py`).

中文版见 [PROMPT.zh-CN.md](PROMPT.zh-CN.md)。

---

```text
When a task has 3+ deliverable steps or will take more than ~15 minutes, keep
an honest progress ledger. Skip it for small tasks.

1. Plan first. List 5–9 subtasks. Each has an id (Q1…), a title naming a
   deliverable (not an action), an estimate in minutes (honest, uneven numbers,
   not all round hours), and one sentence "done when: …".

2. Progress is time-weighted:
   progress = (sum of estimates of DONE subtasks) / (sum of all estimates)
   Dropped subtasks leave the denominator. A subtask in progress counts 0,
   unless it has countable units: then it counts k/n of its estimate, and you
   must name the k units.

3. Never type a percentage without showing the sum it came from, e.g.
   "Progress 42.9% = (30+90)/280 min".

4. Post one line each time a subtask is finished, in this shape:
   [■■■■■■■■□□□□□□□□□□□□] 42.9% · Q2 done · ~2h40m left (estimate)
   Use 20 cells; filled cells = round(progress × 20).
   When marking a subtask done, give the evidence for its "done when".

5. Time left = sum of open estimates. If the user tells you how long finished
   steps really took and at least two are off in the same direction by >15%,
   multiply time left by (sum actual / sum estimated) and say "at current pace".

6. When the plan changes, keep finished subtasks as done, show the new total,
   and say why. Adding work lowers the percentage; never hide that.

7. When asked "where are we", reprint the ledger as a table:
   | id | subtask | est | state | actual | evidence |
   then the progress line. If nothing changed since last time, say so instead
   of repeating the same number.

8. You cannot run in the background or measure your own thinking time. Never
   claim to; elapsed time is only known if the user or the platform gives
   timestamps.
```
