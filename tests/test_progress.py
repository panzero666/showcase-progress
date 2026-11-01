"""Tests for scripts/progress.py. Run: python -m unittest discover -s tests"""

import contextlib
import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, os.pardir, "scripts", "progress.py")

spec = importlib.util.spec_from_file_location("progress", SCRIPT)
progress = importlib.util.module_from_spec(spec)
spec.loader.exec_module(progress)

PLAN = [
    {"id": "Q1", "title": "Map current auth code", "est": "30m"},
    {"id": "Q2", "title": "Token endpoint returns JWT", "est": "1h30m",
     "done_when": "curl /token returns 200 + JWT"},
    {"id": "Q3", "title": "Migrate 6 handlers", "est": "2h"},
    {"id": "Q4", "title": "Deploy to staging", "est": "40m"},
]


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.state = os.path.join(self.dir, "state.json")
        os.environ.pop("SP_LANG", None); os.environ.pop("AGP_LANG", None)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def run_cli(self, *argv, expect=0):
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = progress.main(["--state", self.state] + list(argv))
            except SystemExit as exc:
                code = exc.code
        self.assertEqual(code, expect, "stdout=%s stderr=%s" % (out.getvalue(), err.getvalue()))
        return out.getvalue() + err.getvalue()

    def init(self, plan=PLAN, title="Ship login API"):
        return self.run_cli("init", "--title", title, "--subtasks", json.dumps(plan),
                            "--started", "2026-11-01T09:00:00", "--now", "2026-11-01T09:00:00")

    def ledger(self):
        with open(self.state, encoding="utf-8") as handle:
            return json.load(handle)

    def info(self):
        return progress.totals(self.ledger())


class Durations(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(progress.parse_minutes("1h30m"), 90)
        self.assertEqual(progress.parse_minutes("90"), 90)
        self.assertEqual(progress.parse_minutes("2小时"), 120)
        self.assertEqual(progress.parse_minutes("45分钟"), 45)
        self.assertEqual(progress.parse_minutes("1.5h"), 90)
        self.assertEqual(progress.parse_minutes(20), 20)

    def test_bad_duration(self):
        with self.assertRaises(ValueError):
            progress.parse_minutes("soon")

    def test_format_back(self):
        self.assertEqual(progress.fmt_minutes(45), "45m")
        self.assertEqual(progress.fmt_minutes(130), "2h10m")
        self.assertEqual(progress.fmt_minutes(119.9), "2h")
        self.assertEqual(progress.fmt_minutes(0.6), "<1m")
        self.assertEqual(progress.fmt_minutes(0), "0m")

    def test_seconds_for_fast_agents(self):
        self.assertAlmostEqual(progress.parse_minutes("40s"), 40 / 60)
        self.assertAlmostEqual(progress.parse_minutes("1m30s"), 1.5)


class Weighting(Base):
    def test_percent_is_time_not_count(self):
        self.init()
        self.run_cli("update", "Q1=done", "--now", "2026-11-01T09:30:00")
        # 1 of 4 subtasks done, but only 30m of 4h40m: 10.7%, not 25%
        self.assertAlmostEqual(self.info()["fraction"], 30 / 280)

    def test_doing_earns_nothing(self):
        self.init()
        self.run_cli("update", "Q3=doing")
        self.assertEqual(self.info()["fraction"], 0.0)

    def test_count_gives_partial_credit(self):
        self.init()
        self.run_cli("update", "Q3=doing", "--count", "3/6")
        self.assertAlmostEqual(self.info()["fraction"], 60 / 280)

    def test_count_cleared_when_done(self):
        self.init()
        self.run_cli("update", "Q3=doing", "--count", "3/6")
        self.run_cli("update", "Q3=done")
        sub = [s for s in self.ledger()["subtasks"] if s["id"] == "Q3"][0]
        self.assertNotIn("count", sub)
        self.assertAlmostEqual(self.info()["fraction"], 120 / 280)

    def test_bad_count_rejected(self):
        self.init()
        self.run_cli("update", "Q3=doing", "--count", "7/6", expect=1)

    def test_splitting_does_not_inflate(self):
        # One 2h task vs. the same 2h split into 6 pieces: finishing the same
        # amount of work must give the same percentage.
        self.init([{"id": "A", "est": "2h"}, {"id": "B", "est": "2h"}])
        self.run_cli("update", "A=done")
        whole = self.info()["fraction"]
        pieces = [{"id": "A%d" % i, "est": "20m"} for i in range(6)] + [{"id": "B", "est": "2h"}]
        self.init(pieces)
        self.run_cli("update", ",".join("A%d=done" % i for i in range(6)))
        self.assertAlmostEqual(self.info()["fraction"], whole)

    def test_dropped_leaves_denominator(self):
        self.init()
        self.run_cli("update", "Q4=dropped(out of scope)")
        self.assertEqual(self.info()["plan"], 240)


class Speed(Base):
    def test_one_sample_is_not_a_sample(self):
        self.init()
        self.run_cli("update", "Q2=done", "--took", "3h")
        self.assertIsNone(self.info()["factor"])

    def test_factor_after_two_samples(self):
        self.init()
        self.run_cli("update", "Q1=done", "--took", "45m")
        self.run_cli("update", "Q2=done", "--took", "2h")
        info = self.info()
        self.assertAlmostEqual(info["factor"], 165 / 120)
        self.assertAlmostEqual(info["remaining"], 160 * 165 / 120)

    def test_noise_ignored(self):
        self.init()
        self.run_cli("update", "Q1=done", "--took", "32m")
        self.run_cli("update", "Q2=done", "--took", "1h35m")
        self.assertIsNone(self.info()["factor"])

    def test_label_says_current_pace(self):
        self.init()
        self.run_cli("update", "Q1=done", "--took", "45m")
        out = self.run_cli("update", "Q2=done", "--took", "2h", "--brief")
        self.assertIn("left at current pace", out)


class Replan(Base):
    def test_replan_keeps_finished_work(self):
        self.init()
        self.run_cli("update", "Q1=done", "--took", "40m")
        new = PLAN + [{"id": "Q5", "title": "Write changelog", "est": "20m"}]
        self.run_cli("replan", "--subtasks", json.dumps(new), "--reason", "added changelog")
        q1 = [s for s in self.ledger()["subtasks"] if s["id"] == "Q1"][0]
        self.assertEqual(q1["state"], "done")
        self.assertEqual(q1["actual"], 40)
        # More work in the plan means a lower percentage - that's honest.
        self.assertAlmostEqual(self.info()["fraction"], 30 / 300)

    def test_removed_done_is_recorded(self):
        self.init()
        self.run_cli("update", "Q1=done")
        self.run_cli("replan", "--subtasks", json.dumps(PLAN[1:]))
        last = self.ledger()["history"][-1]
        self.assertEqual(last["detail"]["removed_done"], ["Q1"])


class Check(Base):
    def test_clean_plan_passes(self):
        self.init()
        self.run_cli("check")

    def test_duplicate_id_fails(self):
        self.init([{"id": "A", "est": "1h"}, {"id": "A", "est": "1h"}])
        out = self.run_cli("check", expect=1)
        self.assertIn("duplicate-id", out)

    def test_done_without_evidence_warns(self):
        self.init()
        self.run_cli("update", "Q2=done")
        out = self.run_cli("check")
        self.assertIn("no-evidence", out)

    def test_evidence_silences_warning(self):
        self.init()
        self.run_cli("update", "Q2=done", "--evidence", "curl returned 200, token decoded")
        out = self.run_cli("check")
        self.assertNotIn("no-evidence", out)

    def test_lopsided_warns(self):
        self.init([{"id": "A", "est": "10m"}, {"id": "B", "est": "10m"}, {"id": "C", "est": "5h"}])
        self.assertIn("lopsided", self.run_cli("check"))


class Moves(Base):
    def test_note_with_commas(self):
        self.init()
        self.run_cli("update", "Q4=blocked(no access, waiting on ops)")
        q4 = [s for s in self.ledger()["subtasks"] if s["id"] == "Q4"][0]
        self.assertEqual(q4["note"], "no access, waiting on ops")

    def test_fullwidth_parentheses(self):
        self.init()
        self.run_cli("update", "Q4=blocked（等运维，没权限）")
        q4 = [s for s in self.ledger()["subtasks"] if s["id"] == "Q4"][0]
        self.assertEqual(q4["state"], "blocked")
        self.assertEqual(q4["note"], "等运维，没权限")

    def test_took_needs_single_move(self):
        self.init()
        self.run_cli("update", "Q1=done,Q2=done", "--took", "1h", expect=1)

    def test_next_mentions_blocked(self):
        self.init()
        self.run_cli("update", "Q1=done,Q2=blocked(waiting on keys)")
        out = self.run_cli("render", "--mode", "next")
        self.assertIn("Q3", out)
        self.assertIn("waiting on keys", out)


class Language(Base):
    def test_english_by_default(self):
        self.assertIn("Progress", self.init())

    def test_chinese_title_gives_chinese(self):
        self.assertIn("进度", self.init(title="统一云函数错误处理"))

    def test_flag_overrides(self):
        self.init(title="统一云函数错误处理")
        self.assertIn("left", self.run_cli("--lang", "en", "render", "--mode", "bar"))

    def test_env_overrides(self):
        os.environ["SP_LANG"] = "zh"
        try:
            self.assertIn("进度", self.init())
        finally:
            os.environ.pop("SP_LANG", None); os.environ.pop("AGP_LANG", None)


class Persistence(Base):
    def test_resume_from_disk(self):
        self.init()
        self.run_cli("update", "Q1=done", "--took", "30m")
        # a fresh process only has the file
        out = self.run_cli("render", "--now", "2026-11-01T10:00:00")
        self.assertIn("10.7%", out)
        self.assertIn("Q2", out)

    def test_export_writes_both(self):
        self.init()
        self.run_cli("update", "Q2=done", "--evidence", "curl ok")
        json_out = os.path.join(self.dir, "p.json")
        md_out = os.path.join(self.dir, "P.md")
        self.run_cli("export", "--json-out", json_out, "--md-out", md_out)
        with open(md_out, encoding="utf-8") as handle:
            self.assertIn("curl ok", handle.read())
        with open(json_out, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["plan_minutes"], 280)

    def test_old_schema_refused(self):
        with open(self.state, "w", encoding="utf-8") as handle:
            json.dump({"schema": 1, "subtasks": [{"id": "x"}]}, handle)
        self.run_cli("init", "--subtasks", json.dumps(PLAN), expect=1)

    def test_v2_ledger_still_reads(self):
        with open(self.state, "w", encoding="utf-8") as handle:
            json.dump({"schema": 2, "title": "old", "started_at": "2026-11-01T09:00:00",
                       "subtasks": [{"id": "Q1", "title": "a", "state": "done", "est": 30},
                                    {"id": "Q2", "title": "b", "state": "todo", "est": 30}]},
                      handle)
        self.assertIn("50.0%", self.run_cli("render", "--mode", "bar"))


class Bar(unittest.TestCase):
    def test_never_falsely_full_or_empty(self):
        self.assertEqual(progress.make_bar(0.99, 20).count("□"), 1)
        self.assertEqual(progress.make_bar(0.01, 20).count("■"), 1)
        self.assertEqual(progress.make_bar(0.0, 20).count("■"), 0)
        self.assertEqual(progress.make_bar(1.0, 20).count("□"), 0)


if __name__ == "__main__":
    unittest.main()
