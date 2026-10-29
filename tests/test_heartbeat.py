"""Missed-run heartbeat (#148 item 1): the Oct 22-26 outage shape, the grace window, and a read-only workflow."""
import datetime, json, sys, unittest
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import heartbeat  # noqa: E402

ET = ZoneInfo("America/New_York")
SCHED = {"items": [{"id": "daily", "cron": "45 4 * * *"}]}


def at(day, hour, minute=0):
    return datetime.datetime(2026, 10, day, hour, minute, tzinfo=ET)


class Heartbeat(unittest.TestCase):
    def test_outage_is_caught(self):
        ok, msg = heartbeat.verdict({"last_run": "2026-10-21"}, SCHED, at(23, 10))
        self.assertFalse(ok)
        self.assertIn("2026-10-23", msg)
        self.assertIn("2 days behind", msg)

    def test_todays_run_passes(self):
        self.assertTrue(heartbeat.verdict({"last_run": "2026-10-28"}, SCHED, at(28, 10))[0])

    def test_before_the_grace_window_yesterday_is_enough(self):
        self.assertTrue(heartbeat.verdict({"last_run": "2026-10-27"}, SCHED, at(28, 8))[0])

    def test_after_the_grace_window_yesterday_is_a_miss(self):
        ok, msg = heartbeat.verdict({"last_run": "2026-10-27"}, SCHED, at(28, 8, 46))
        self.assertFalse(ok)
        self.assertIn("1 day behind", msg)

    def test_run_time_comes_from_the_schedule(self):
        self.assertEqual(heartbeat.daily_time(json.loads((ROOT / "data/schedule.json").read_text())), (4, 45))

    def test_workflow_is_read_only_and_runs_the_script(self):
        w = (ROOT / ".github/workflows/heartbeat.yml").read_text()
        self.assertIn("python3 scripts/heartbeat.py", w)
        self.assertIn("contents: read", w)
        self.assertNotRegex(w, r":\s*write\b")


if __name__ == "__main__":
    unittest.main()
