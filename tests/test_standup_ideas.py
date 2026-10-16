"""Trial's tests for the standup, pitches, idea log, and Team chat feeds. Written before the code."""
import json, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check, build  # noqa: E402

IDEA = {"id": "i1", "date": "2026-10-16", "by": "Polish", "problem": "P", "helps": "Readers", "effort": "S",
        "builder": "Pixel", "state": "pitched", "comments": []}
LINE = {"id": "s1", "date": "2026-10-16", "role": "Scout", "did": "a", "doing": "b", "blockers": "none"}


class Schemas(unittest.TestCase):
    def test_files_validated(self):
        self.assertIn("standup", check.DATA_FILES)
        self.assertIn("ideas", check.DATA_FILES)

    def test_standup_line(self):
        self.assertEqual(check.validate([LINE], check.load_schema("standup")), [])
        self.assertTrue(check.validate([dict(LINE, role="Ryno")], check.load_schema("standup")))
        self.assertTrue(check.validate([dict(LINE, extra=1)], check.load_schema("standup")))

    def test_idea(self):
        self.assertEqual(check.validate([IDEA], check.load_schema("ideas")), [])
        self.assertTrue(check.validate([dict(IDEA, effort="XL")], check.load_schema("ideas")))


class IdeaRules(unittest.TestCase):
    def test_pitched_ok(self):
        self.assertEqual(check.idea_errors([IDEA]), [])

    def test_decision_needs_reason_from_coordinator(self):
        self.assertTrue(check.idea_errors([dict(IDEA, state="yes")]))
        self.assertEqual(check.idea_errors([dict(IDEA, state="yes", decided="2026-10-19", decided_by="Coordinator", reason="fits")]), [])
        self.assertTrue(check.idea_errors([dict(IDEA, state="yes", decided="2026-10-19", decided_by="Forge", reason="fits")]))

    def test_only_shield_vetoes(self):
        v = dict(IDEA, state="vetoed", decided="2026-10-19", reason="risk")
        self.assertTrue(check.idea_errors([dict(v, decided_by="Coordinator")]))
        self.assertEqual(check.idea_errors([dict(v, decided_by="Shield")]), [])

    def test_two_strong_objections_escalate(self):
        c = [{"date": "2026-10-19", "role": r, "stance": "oppose", "strong": True, "text": "no"} for r in ("Atlas", "Trial")]
        d = dict(IDEA, state="yes", decided="2026-10-19", decided_by="Coordinator", reason="fits", comments=c)
        self.assertTrue(check.idea_errors([d]))  # must be needs-ceo
        self.assertEqual(check.idea_errors([dict(d, state="needs-ceo")]), [])
        one = dict(d, comments=c[:1])
        self.assertEqual(check.idea_errors([one]), [])

    def test_repitch_needs_evidence(self):
        self.assertTrue(check.idea_errors([dict(IDEA, repitch_of="i0")]))
        self.assertEqual(check.idea_errors([dict(IDEA, repitch_of="i0", evidence="new data")]), [])


class Site(unittest.TestCase):
    def test_chat_feeds_and_views(self):
        files = build.build()
        for f in ("chat.json", "chat.xml", "chat/index.html"):
            self.assertIn(f, files)
        json.loads(files["chat.json"])
        self.assertIn("<rss", files["chat.xml"])
        self.assertIn("Standup", files["chat/index.html"])
        self.assertIn("Ideas", files["chat/index.html"])

    def test_follow_doc_has_routine_prompt(self):
        doc = (Path(__file__).resolve().parent.parent / "docs/follow.md").read_text()
        self.assertIn("chat.json", doc)


class XDraft(unittest.TestCase):
    def test_style(self):
        ok = "bots shipped area filters... see it live slopryno.github.io/slopworks"
        self.assertEqual(check.x_draft_errors(ok), [])
        self.assertTrue(check.x_draft_errors("Bots Shipped It"))  # not lowercase
        self.assertTrue(check.x_draft_errors(ok + " #grok"))  # hashtag
        self.assertTrue(check.x_draft_errors("bots shipped 🎉🚀 slopryno.github.io/slopworks"))  # 2 emoji
        self.assertTrue(check.x_draft_errors("bots shipped something"))  # no link


if __name__ == "__main__":
    unittest.main()
