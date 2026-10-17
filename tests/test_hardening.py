"""Trial's tests for i30 PR 3: typed loaders fail fast, and hand-copied values are checked against their source."""
import json, re, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build, check  # noqa: E402

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def schedule_days():
    sched = json.loads((ROOT / "data/schedule.json").read_text())
    return {r["role"]: d["day"] for d in sched["research"] for r in d["roles"]}


class TypedLoaders(unittest.TestCase):
    def test_stale_field_read_fails_loudly(self):
        rec = build._typed([{"id": "r1", "finding": "x"}], check.load_schema("research"), "data/research.json")[0]
        self.assertEqual(rec.get("finding"), "x")
        self.assertIsNone(rec.get("facts"))  # declared but absent: fine
        with self.assertRaisesRegex(KeyError, "doesn't declare"):
            rec.get("takeaways")  # the kind of stale field behind AAR research-render
        with self.assertRaises(KeyError):
            rec["summary"]

    def test_nested_records_are_strict(self):
        a = build._typed([{"concepts": [{"name": "n", "scores": {"impact": 1}}]}], check.load_schema("arena"), "a")[0]
        self.assertRaises(KeyError, a["concepts"][0]["scores"].get, "value")

    def test_bad_file_stops_the_build_before_rendering(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "data").mkdir()
            (Path(d) / "data/chat.json").write_text(json.dumps([{"id": "c1", "date": "2026-10-17", "from": "Lens", "to": "Team", "text": "x" * 281}]))
            with mock.patch.object(build, "ROOT", Path(d)):
                with self.assertRaisesRegex(build.DataError, "data/chat.json doesn't match its schema"):
                    build.load("chat")
            (Path(d) / "data/chat.json").write_text("[{")
            with mock.patch.object(build, "ROOT", Path(d)):
                self.assertRaisesRegex(build.DataError, "data/chat.json", build.load, "chat")

    def test_prototype_todays_build_reads_only_declared_fields(self):
        """Open question from docs/hardening.md: does the current build read any undeclared field? It doesn't."""
        self.assertIn("index.html", build.build())


class HandCopiedValues(unittest.TestCase):
    def test_bot_file_research_days_match_schedule(self):
        days, n = schedule_days(), 0
        for f in sorted((ROOT / "bots").glob("*.md")):
            para = re.search(r"^\*\*Weekly research:\*\*(.*)$", f.read_text(), re.M).group(1)
            for who, day in re.findall(r"\b([A-Z]\w+) on (Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)days", para):
                n += 1
                self.assertEqual(days.get(who), day + "day", f"{f.name}: {who} on {day}days, schedule says {days.get(who)}")
        self.assertGreaterEqual(n, 16)

    def test_tracker_rotation_matches_schedule(self):
        days = schedule_days()
        text = (ROOT / "plans/tracker.md").read_text()
        seen = {}
        for day, roles in re.findall(r"^\s+- (" + "|".join(DAYS) + r"): (.+)$", text, re.M):
            for r in roles.split(","):
                seen[r.strip()] = day
        self.assertEqual(seen, days)

    def test_research_notes_have_two_or_three_takeaways(self):
        """plans/tracker.md says research notes carry 2-3 takeaways; nothing checked it until now."""
        for n in json.loads((ROOT / "data/research.json").read_text()):
            self.assertIn(len(n.get("facts", [])), (2, 3), n["id"])


if __name__ == "__main__":
    unittest.main()
