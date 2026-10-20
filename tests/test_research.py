"""Trial's tests for the weekly research rotation and notes. Written before the code."""
import json, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check, build  # noqa: E402

SCHED = json.loads((ROOT / "data/schedule.json").read_text())
N = {"id": "r1", "date": "2026-10-20", "role": "Polish", "kind": "rotation", "question": "What type scale reads best on mobile?",
     "outcome": "finding", "finding": "F", "facts": ["a"], "inferences": ["b"], "evidence": ["https://example.org/post"],
     "confidence": "medium", "status": "verified", "fresh_until": "2027-01-20"}  # 2026-10-20 is a Tuesday
P = dict(N, outcome="proposal", existing_work="none", opportunity="o", alternatives="a", effort="S", risks="r",
         experiment="e", success_metric="m", recommendation="investigate")


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
        for n in (N, P, dict(N, outcome="no-change")):
            self.assertEqual(check.validate([n], check.load_schema("research")), [])
            self.assertEqual(check.research_errors([n], SCHED, []), [])

    def test_rules(self):
        bad = [dict(N, evidence=[]), dict(N, evidence=["https://e.org/%d" % i for i in range(6)]), dict(N, evidence=["http://e.org"]),
               dict(N, evidence=["https://x.com/a/status/1"]), dict(N, date="2026-10-21"), dict(N, pitch="i404"),
               dict(N, facts=[]),  # verified needs facts, kept apart from inferences
               dict(P, success_metric=""),  # proposals need the full report
               dict(N, role="Advocate", date="2026-10-20"),  # demand claims are hypothesis until real feedback
               dict(N, fresh_until=None)]
        for b in bad:
            self.assertTrue(check.research_errors([b], SCHED, []), b)
        self.assertEqual(check.research_errors([dict(N, kind="focused", date="2026-10-21")], SCHED, []), [])  # focused any day
        self.assertEqual(check.research_errors([dict(N, role="Advocate", status="hypothesis")], SCHED, []), [])
        self.assertEqual(check.research_errors([dict(N, pitch="i1")], SCHED, [{"id": "i1"}]), [])
        self.assertIn("research", check.DATA_FILES)


class Site(unittest.TestCase):
    def test_views_and_feeds(self):
        files = build.build()
        self.assertIn("Research", files["chat/index.html"])
        # Page budget (Ryno, Oct 20 7:27 AM ET): each role's research rotation and latest note live on its character sheet.
        sheets = [k for k in files if k.startswith("team/") and k.count("/") == 2 and k.endswith("/index.html") and k != "team/xp/index.html"]
        with_research = [k for k in sheets if 'id="research"' in files[k]]
        self.assertGreaterEqual(len(with_research), 10)
        self.assertTrue(all("on the weekly research rotation" in files[k] for k in with_research))
        self.assertNotIn("Researches", files["team/index.html"])

    def test_every_bot_file_mentions_research(self):
        for f in (ROOT / "bots").glob("*.md"):
            self.assertIn("**Weekly research:**", f.read_text(), f.name)


if __name__ == "__main__":
    unittest.main()
