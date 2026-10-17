"""Trial's tests for the showcase guardrails (i22, sprint PR 8). They only tighten: demo stays labeled, links stay safe, no live claims."""
import json, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check  # noqa: E402

DATA = {n: json.loads((ROOT / f"data/{n}.json").read_text()) for n in ("research", "arena", "cases", "challenges")}


def fake_site(pages):
    tmp = Path(tempfile.mkdtemp())
    for path, html in pages.items():
        (tmp / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp / path).write_text(html)
    return tmp


class Showcase(unittest.TestCase):
    def test_repo_data_passes(self):
        self.assertEqual(check.showcase_errors(DATA), [])

    def test_schemas_registered(self):
        for n in ("arena", "cases", "challenges"):
            self.assertIn(n, check.DATA_FILES)
            self.assertEqual(check.validate(DATA[n], check.load_schema(n)), [])

    def test_challenge_must_be_demo(self):
        bad = json.loads(json.dumps(DATA["challenges"])); bad[0]["demo"] = False
        self.assertTrue(check.validate(bad, check.load_schema("challenges")))
        self.assertTrue(any("demo: true" in e for e in check.showcase_errors(dict(DATA, challenges=bad))))

    def test_challenge_cannot_cite_real_research(self):
        bad = json.loads(json.dumps(DATA["challenges"])); bad[0]["sections"][0]["items"][0]["research"] = "r-scout-2026-10-17-showcase"
        self.assertTrue(any("real research" in e for e in check.showcase_errors(dict(DATA, challenges=bad))))

    def test_orphan_demo_research_flagged(self):
        self.assertTrue(any("must belong to a challenge" in e for e in check.showcase_errors(dict(DATA, challenges=[]))))

    def test_case_link_must_be_safe(self):
        bad = json.loads(json.dumps(DATA["cases"])); bad[0]["steps"][0]["link"] = "https://example.com/transcript"
        self.assertTrue(any("not a merged PR" in e for e in check.showcase_errors(dict(DATA, cases=bad))))

    def test_case_link_must_resolve(self):
        root = fake_site({"site/chat/index.html": '<p id="c1"></p>'})
        cases = [{"id": "x", "steps": [{"link": "../chat/#c1"}, {"link": "../chat/#c999"}]}]
        errs = check.showcase_errors({"cases": cases}, root)
        self.assertEqual(len(errs), 1); self.assertIn("c999", errs[0])

    def test_demo_page_needs_label_and_note(self):
        ch = [{"id": "demo-1", "demo": True, "sections": []}]
        root = fake_site({"site/challenges/index.html": '<article id="demo-1">A worked example.</article>'})
        self.assertTrue(any("Demo label" in e for e in check.showcase_errors({"challenges": ch}, root)))

    def test_no_live_claims(self):
        root = fake_site({"site/index.html": "<p>The team is working right now, in real time.</p>"})
        errs = check.showcase_errors({}, root)
        self.assertEqual(len(errs), 2)

    def test_guardrail_additions_only(self):
        self.assertFalse(check.loosening("scripts/check.py", ["x = 1"], []))
        self.assertTrue(check.loosening("scripts/check.py", [], ["x = 1"]))


if __name__ == "__main__":
    unittest.main()
