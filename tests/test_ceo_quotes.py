"""Trial's tests: no CEO quotes on the site (Ryno, Oct 21, 2026, 8:51 AM ET). His words and their ET time stay on the PR
and in the add-only records; pages say what he decided."""
import json, re, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build, ceo, ceo_quotes as cq, check  # noqa: E402


class Scrub(unittest.TestCase):
    CASES = [
        ('Ryno, 11:02 AM ET: "Lets run another sprint". One extra sprint today.', "Ryno's call, 11:02 AM ET. One extra sprint today."),
        ("Approved by Ryno in Grok Bot chat 2026-10-17 7:24 AM ET: 'Lift the cap, run all 8 PRs now.' One-time override.",
         "Approved by Ryno in Grok Bot chat 2026-10-17 7:24 AM ET. One-time override."),
        ("Ryno in Grok Bot chat 2026-10-18 1:17 AM ET: 'Build it', on the list.", "Decided by Ryno in Grok Bot chat 2026-10-18 1:17 AM ET, on the list."),
        ("Directed by Ryno in chat 1:37 PM ET ('lets heed her words', on a post): code first.", "Directed by Ryno in chat 1:37 PM ET (on a post): code first."),
        ("Huddle: Ryno said 'Run another sprint' at 8:31 PM ET.", "Huddle: Ryno decided at 8:31 PM ET."),
        ("dark mode lifted (Ryno: 'too dark?'), cards", "dark mode lifted (Ryno's feedback), cards"),
        ('Switch-on "Yes" from Ryno, Oct 19, 11:40 PM ET.', "Switch-on decision from Ryno, Oct 19, 11:40 PM ET."),
        ('Training note on Ryno\'s Oct 21 ask, "Have the team review": 8 roles add 9 skills.', "Training note on Ryno's Oct 21 ask: 8 roles add 9 skills."),
        ("Directed by Ryno. At 8:51 PM ET: 'Repo to remain lean.' Added.", "Directed by Ryno. He added more at 8:51 PM ET. Added."),
    ]

    def test_attributed_quotes_become_neutral_lines(self):
        for before, after in self.CASES:
            got, found = cq.scrub(before)
            self.assertEqual(got, after)
            self.assertTrue(found)

    def test_other_quotes_stay(self):
        for s in ("Polish: the 'Meet the team' button stays first.", "Lens said 'cases before demos'.", "Comms: 'XP' and 'level', never 'best'."):
            self.assertEqual(cq.scrub(s), (s, []))

    def test_registry_catches_his_words_unattributed(self):
        reg = cq.registry()
        for r in json.loads((ROOT / "data/ceo_overrides.json").read_text()):
            self.assertIn(r["quote"], reg)
        self.assertEqual(cq.scrub("The 'too dark?' huddle", reg)[0], "The CEO feedback huddle")


class Site(unittest.TestCase):
    def test_built_pages_have_no_ceo_quotes(self):
        files = build.build()
        reg = cq.registry()
        for rel, content in files.items():
            if rel.endswith((".html", ".xml", ".json", ".txt", ".ics")):
                self.assertEqual(cq.hits(cq.page_text(rel, content), reg), [], rel)

    def test_ceo_sheet_lists_decisions_not_words(self):
        sheet = ceo.sheet(build.REPO, 19, "")
        for h in ("Safeguard", "Unblock"):
            sec = re.search(rf"<h2>{h}</h2>(.*?)</ul>", sheet, re.S).group(1)
            self.assertNotIn("“", sec, h)
            self.assertNotIn("”", sec, h)
        recs = json.loads((ROOT / "data/ceo_decisions.json").read_text()) + json.loads((ROOT / "data/ceo_overrides.json").read_text())
        for r in recs:
            if r.get("quote"):
                self.assertNotIn(r["quote"], sheet)  # even "Yes", which is too short for the site-wide registry
        self.assertEqual(sheet.count("CEO override"), len(json.loads((ROOT / "data/ceo_overrides.json").read_text())))

    def test_records_keep_the_audit_trail(self):
        # The data stays intact: the EA's records still carry his verbatim words and time (check.py ceo_decision_errors).
        for r in json.loads((ROOT / "data/ceo_overrides.json").read_text()):
            self.assertTrue(r["quote"].strip())
        self.assertEqual(check.ceo_decision_errors(), [])

    def test_check_fails_a_quote_on_a_page(self):
        import tempfile, shutil
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            shutil.copytree(ROOT / "data", d / "data")
            (d / "site").mkdir()
            q = json.loads((ROOT / "data/ceo_overrides.json").read_text())[0]["quote"]
            (d / "site/index.html").write_text(f"<p>He wrote &#x27;{q}&#x27; in chat.</p>")
            self.assertTrue(check.ceo_quote_errors(d))
            (d / "site/index.html").write_text("<p>CEO override, 10/19.</p>")
            self.assertEqual(check.ceo_quote_errors(d), [])
        self.assertEqual(check.ceo_quote_errors(), [])


if __name__ == "__main__":
    unittest.main()
