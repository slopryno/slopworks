"""Trial's tests for the early run (Ryno, 2026-10-20 10:15 AM ET: "Lets have runs start early morning so visitors
can get the latest version once they wake up"). The run's time lives once, in data/schedule.json's daily cron, and
every page and the calendar feed read it from there."""
import json, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build, cal  # noqa: E402

SCHED = json.loads((ROOT / "data/schedule.json").read_text())
FILES = build.build()


class RunTime(unittest.TestCase):
    def test_words_from_cron(self):
        mk = lambda c: {"items": [{"id": "daily", "cron": c}]}
        self.assertEqual(cal.run_time(mk("45 4 * * *")), "4:45 AM ET")
        self.assertEqual(cal.run_time(mk("13 9 * * *")), "9:13 AM ET")
        self.assertEqual(cal.run_time(mk("5 0 * * *")), "12:05 AM ET")
        self.assertEqual(cal.run_time(mk("30 13 * * *")), "1:30 PM ET")

    def test_early_morning(self):
        minute, hour = (int(x) for x in next(i for i in SCHED["items"] if i["id"] == "daily")["cron"].split()[:2])
        self.assertTrue(4 <= hour < 6, "the daily run starts early morning ET")

    def test_daily_when_matches_cron(self):
        daily = next(i for i in SCHED["items"] if i["id"] == "daily")
        self.assertIn(cal.run_time(SCHED), daily["when"])

    def test_items_in_the_run_share_its_time(self):
        hm = next(i for i in SCHED["items"] if i["id"] == "daily")["cron"].split()[:2]
        for i in SCHED["items"]:
            self.assertEqual(i["cron"].split()[:2], hm, i["id"])

    def test_pages_and_feed_show_the_schedule_time(self):
        t = cal.run_time(SCHED)
        for name in ("how/index.html", "schedule/index.html", "calendar/index.html", "calendar.ics"):
            body = FILES[name] if isinstance(FILES[name], str) else FILES[name].decode()
            self.assertIn(t, body.replace("\r\n ", ""), name)
        for name, body in FILES.items():
            if isinstance(body, str) and not name.startswith(("chat/archive/", "timeline/archive/")):
                self.assertIsNone(re.search(r"around 9:1[35] AM ET", body), name)


if __name__ == "__main__":
    unittest.main()
