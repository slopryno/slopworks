"""Training plan rules (Ryno approved 2026-10-19 7:27 AM ET, i59)."""
import json, os, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check  # noqa: E402
import bot  # noqa: E402


class Derived(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "data").mkdir()
        (self.root / "data/x.json").write_text(json.dumps([{"s": "yes"}, {"s": "no"}, {"s": "yes"}], indent=2))

    def test_matching_lines_pass(self):
        self.assertEqual(check.derived_errors('Derived: count data/x.json = 3\nDerived: count data/x.json "yes" = 2', self.root), [])

    def test_a_wrong_number_fails(self):
        self.assertIn("is 3, not 4", check.derived_errors("Derived: count data/x.json = 4", self.root)[0])

    def test_files_outside_the_repo_are_refused(self):
        self.assertTrue(check.derived_errors("Derived: count ../../etc/passwd = 1", self.root))

    def test_lens_needs_a_derived_line(self):
        c = [{"author": {"login": "slopryno"}, "body": "Sign-off: Lens\n52 ideas."}]
        self.assertTrue(check.lens_derived_errors(c, self.root))
        c[0]["body"] += "\nDerived: count data/x.json = 3"
        self.assertEqual(check.lens_derived_errors(c, self.root), [])

    def test_bot_refuses_a_bad_lens_signoff_before_posting(self):
        with self.assertRaises(bot.Refused):
            bot.plan_signoffs("Advisor", ["data/ideas.json"], {"Lens": "Sign-off: Lens\nlooks right"})
        with self.assertRaises(bot.Refused):
            bot.plan_signoffs("Advisor", ["data/ideas.json"], {"Lens": "Sign-off: Lens\nDerived: count data/ideas.json = 1"})


class Loop(unittest.TestCase):
    def test_objective_on_a_shipped_idea_fails(self):
        ideas = [{"id": "i1", "state": "shipped"}, {"id": "i2", "state": "yes"}]
        self.assertEqual(len(check.objective_loop_errors([{"role": "A", "idea": "i1"}, {"role": "B", "idea": "i2"}], ideas)), 1)

    def test_current_records_close_the_loop(self):
        self.assertEqual(check.training_errors(), [])


class Drills(unittest.TestCase):
    def test_a_drill_cant_be_self_checked(self):
        root = Path(tempfile.mkdtemp())
        (root / "data").mkdir()
        d = json.loads((ROOT / "data/drills.json").read_text())
        d[0]["checked_by"] = d[0]["by"]
        (root / "data/drills.json").write_text(json.dumps(d))
        self.assertTrue(any("own drill" in e for e in check.drill_errors(root)))


class Lock(unittest.TestCase):
    def test_a_live_lock_refuses_and_a_dead_one_is_replaced(self):
        p = Path(tempfile.mkdtemp()) / "lock"
        p.write_text(f"{os.getppid()}\n")
        with self.assertRaises(bot.Refused):
            bot.take_lock(p)
        p.write_text("999999999\n")
        bot.take_lock(p)
        self.assertEqual(p.read_text().strip(), str(os.getpid()))
        bot.release_lock(p)
        self.assertFalse(p.exists())

    def test_resume_posts_only_missing_comments(self):
        planned = ["Blast radius: Atlas\nScope: x", "Sign-off: Lens\nok", "Sign-off: Trial\nok"]
        self.assertEqual(bot.missing_comments(planned, ["Sign-off: Lens\nok", "Blast radius: Atlas\nScope: x"]), ["Sign-off: Trial\nok"])



class StateRuns(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "data").mkdir()
        self.runs = [{"id": "2026-10-30-daily", "date": "2026-10-30", "kind": "daily", "status": "skipped", "counts": {}}]
        (self.root / "data/runs.json").write_text(json.dumps(self.runs))
        (self.root / "data/state.json").write_text(json.dumps({
            "auto_merge": "on", "paused_reason": None, "last_run": "2026-10-30", "last_status": "skipped", "updated": "2026-10-30"
        }))

    def test_matching_state_passes(self):
        self.assertEqual(check.state_runs_errors(self.root), [])

    def test_last_run_behind_runs_fails(self):
        s = json.loads((self.root / "data/state.json").read_text())
        s["last_run"] = "2026-10-29"
        (self.root / "data/state.json").write_text(json.dumps(s))
        self.assertTrue(any("last_run" in e for e in check.state_runs_errors(self.root)))

    def test_last_status_mismatch_fails(self):
        s = json.loads((self.root / "data/state.json").read_text())
        s["last_status"] = "ok"
        (self.root / "data/state.json").write_text(json.dumps(s))
        self.assertTrue(any("last_status" in e for e in check.state_runs_errors(self.root)))

    def test_current_records_pass(self):
        self.assertEqual(check.state_runs_errors(), [])


if __name__ == "__main__":
    unittest.main()
