"""Tests for scripts/statusline.py. Run: python -m unittest discover -s tests"""

import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, os.pardir, "scripts", "statusline.py")

spec = importlib.util.spec_from_file_location("statusline", SCRIPT)
statusline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(statusline)
progress = statusline.progress

NOW = progress.parse_time("2026-11-01T12:00:00")


def ledger(folder, subtasks, title="Add password reset", updated="2026-11-01T11:55:00"):
    path = os.path.join(folder, ".showcase-progress", "state.json")
    os.makedirs(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"schema": 3, "title": title, "started_at": "2026-11-01T09:00:00",
                   "updated_at": updated, "subtasks": subtasks}, handle)
    return path


class StatusLine(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        for name in ("SP_STATE", "AGP_STATE", "HP_STATE", "SP_LANG", "AGP_LANG"):
            os.environ.pop(name, None)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def text(self, cwd=None, **kw):
        data = {"workspace": {"current_dir": cwd or self.dir}}
        return statusline.status_text(data, moment=kw.get("moment", NOW), color=False)

    def test_nothing_without_ledger(self):
        self.assertEqual(self.text(), "")

    def test_shows_progress_and_current(self):
        ledger(self.dir, [
            {"id": "Q1", "title": "a", "est": 30, "state": "done"},
            {"id": "Q2", "title": "b", "est": 60, "state": "doing", "count": [1, 3]},
        ])
        line = self.text()
        self.assertIn("Add password reset", line)
        self.assertIn("55.6%", line)          # (30 + 20) / 90
        self.assertIn("Q2 1/3", line)
        self.assertIn("40m left", line)

    def test_found_from_subfolder(self):
        ledger(self.dir, [{"id": "Q1", "title": "a", "est": 30}])
        sub = os.path.join(self.dir, "src", "deep")
        os.makedirs(sub)
        self.assertIn("0.0%", self.text(cwd=sub))

    def test_finished_task_fades_out(self):
        ledger(self.dir, [{"id": "Q1", "title": "a", "est": 30, "state": "done"}],
               updated="2026-11-01T11:00:00")
        self.assertEqual(self.text(), "")
        self.assertIn("✓", self.text(moment=NOW - timedelta(minutes=50)))

    def test_idle_marker(self):
        ledger(self.dir, [{"id": "Q1", "title": "a", "est": 30}], updated="2026-11-01T08:00:00")
        self.assertIn("idle 4h", self.text())

    def test_blocked_count(self):
        ledger(self.dir, [
            {"id": "Q1", "title": "a", "est": 30, "state": "blocked", "note": "keys"},
            {"id": "Q2", "title": "b", "est": 30, "state": "todo"},
        ])
        self.assertIn("1 blocked", self.text())

    def test_long_title_truncated(self):
        ledger(self.dir, [{"id": "Q1", "title": "a", "est": 30}], title="x" * 80)
        self.assertIn("x" * 27 + "…", self.text())

    def test_chinese_ledger(self):
        ledger(self.dir, [{"id": "Q1", "title": "a", "est": 30}], title="统一错误处理")
        self.assertIn("剩 30m", self.text())

    def test_legacy_agent_progress_ledger(self):
        path = os.path.join(self.dir, ".agent-progress", "progress-state.json")
        os.makedirs(os.path.dirname(path))
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"schema": 2, "title": "old", "updated_at": "2026-11-01T11:59:00",
                       "subtasks": [{"id": "Q1", "title": "a", "state": "todo", "est": 10}]}, handle)
        self.assertIn("old", self.text())

    def test_chain_runs_first(self):
        ledger(self.dir, [{"id": "Q1", "title": "a", "est": 30}])
        payload = json.dumps({"workspace": {"current_dir": self.dir}})
        out = io.StringIO()
        cmd = '"%s" -c "print(\'OTHER\')"' % sys.executable
        stdin = sys.stdin
        sys.stdin = io.StringIO(payload)
        try:
            with contextlib.redirect_stdout(out):
                statusline.main(["--chain", cmd])
        finally:
            sys.stdin = stdin
        lines = out.getvalue().splitlines()
        self.assertEqual(lines[0], "OTHER")
        self.assertIn("Add password reset", lines[1])


if __name__ == "__main__":
    unittest.main()
