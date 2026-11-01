# Contributing

Thanks for helping. The most useful things right now:

1. **Test on another agent.** Install the skill in Codex, Gemini CLI, OpenClaw,
   Cursor or anything else that reads Agent Skills, give it a real multi-step
   task, and open an issue with what happened: did it trigger, did it run the
   script, did it post the progress lines? Screenshots welcome.
2. **Bug reports** with the command you ran and the ledger file
   (`.showcase-progress/state.json`) if you can share it.
3. **Translations** of the messages in `scripts/progress.py` (`MESSAGES`) and of
   `PROMPT.md`.

## Ground rules

- The script stays **standard-library only** and runs on Python 3.8+.
- Every behaviour change comes with a test in `tests/test_progress.py`.
- Keep `SKILL.md` short (under 500 lines); details go in `references/`.
- The core promise doesn't change: numbers come from the ledger, unfinished
  work earns nothing unless it's counted, and nothing pretends to run in the
  background.

## Running tests

```bash
python -m unittest discover -s tests -v
```

If you change output, regenerate the demo: `python tools/make_demo.py`.
