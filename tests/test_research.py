"""Trial's tests for the weekly research rotation and notes. Written before the code."""
import json, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check, build  # noqa: E402

SCHED = json.loads((ROOT / "data/schedule.json").read_text())
N = {"id": "r1", "date": "2026-10-20", "role": "Polish", "topic": "Type scales on static sites",
     "takeaways": ["a", "b"], "sources": ["https://example.org/post"]}  # 2026-10-20 is a Tuesday


class Rotation(unittest.TestCase):
    def test_every_role_once_a_week(self):
        rot = SCHED["research"]
        roles = [r["role"] for d in rot for r in d["roles"]]
        self.assertEqual(len(roles), len(set(roles)))
        for r in ["Coordinator", "Scout", "Verify", "Shield", "Forge", "Pixel", "Core", "Trial", "Polish", "Advisor", "Atlas", "Sweep", "Analyst", "Scoutmaster", "Critic", "Advocate", "Librarian"]:
            self.assertIn(r, roles)
        self.assertTrue(all(1 <= len(d["roles"]) <= 3 for d in rot))
        self.assertEqual(len(rot), 7)

    def test_schedule_page_shows_rotation(self):
        page = build.build()["schedule/index.html"]
        self.assertIn("Research rotation", page)
        self.assertIn("Polish", page)


class Notes(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(check.validate([N], check.load_schema("research")), [])
        self.assertEqual(check.research_errors([N], SCHED, []), [])

    def test_rules(self):
        self.assertTrue(check.research_errors([dict(N, takeaways=["a"])], SCHED, []))
        self.assertTrue(check.research_errors([dict(N, takeaways=["a", "b", "c", "d"])], SCHED, []))
        self.assertTrue(check.research_errors([dict(N, sources=[])], SCHED, []))
        self.assertTrue(check.research_errors([dict(N, sources=["https://e.org/%d" % i for i in range(6)])], SCHED, []))
        self.assertTrue(check.research_errors([dict(N, sources=["http://e.org"])], SCHED, []))
        self.assertTrue(check.research_errors([dict(N, sources=["https://x.com/a/status/1"])], SCHED, []))  # web only, no X reads
        self.assertTrue(check.research_errors([dict(N, date="2026-10-21")], SCHED, []))  # not Polish's day
        self.assertTrue(check.research_errors([dict(N, pitch="i404")], SCHED, []))
        self.assertEqual(check.research_errors([dict(N, pitch="i1")], SCHED, [{"id": "i1"}]), [])
        self.assertIn("research", check.DATA_FILES)


class Site(unittest.TestCase):
    def test_views_and_feeds(self):
        files = build.build()
        self.assertIn("Research", files["chat/index.html"])
        self.assertIn("Researches", files["team/index.html"])

    def test_every_bot_file_mentions_research(self):
        for f in (ROOT / "bots").glob("*.md"):
            self.assertIn("**Weekly research:**", f.read_text(), f.name)


if __name__ == "__main__":
    unittest.main()
