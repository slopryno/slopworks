"""Trial's tests for Comms's word limits and voice check (visual review 2026-10-19, V2; docs/voice.md).
Each limit fails on a page over it, text behind a closed tap-to-expand counts only toward the details limit, records are
exempt, removing a guard is loosening, and the first phone screen stays within budget on enforced pages."""
import json, os, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check, mobile_audit  # noqa: E402

CFG = json.loads((ROOT / "data/word_limits.json").read_text())
VOICE = json.loads((ROOT / "data/voice.json").read_text())
words = lambda n: " ".join(f"w{i}" for i in range(n))
page = lambda body, footer="Home": f'<!doctype html><html lang="en"><body><main><h1>T</h1>{body}</main><footer>{footer}</footer></body></html>'


class Limits(unittest.TestCase):
    def test_config_matches_schema_and_names_every_area(self):
        self.assertEqual(check.validate(CFG, check.load_schema("word_limits")), [])
        for name in ("page_title", "lede", "section_intro", "role_bio", "team_role_card", "content_card", "lesson_card",
                     "metric_caption", "paragraph", "footer"):
            self.assertIn(name, CFG["areas"])
            self.assertIsInstance(CFG["areas"][name]["limit"], int)
        self.assertEqual(CFG["first_screen"], 110)
        self.assertEqual(CFG["details_limit"], 250)

    def test_each_area_fails_one_word_over(self):
        cases = {"lede": '<p class="lede">{}</p>', "paragraph": "<p>{}</p>", "role_bio": '<p class="bio">{}</p>',
                 "section_intro": "<h2>S</h2><p>{}</p>", "lesson_card": '<article class="card aar">{}</article>',
                 "content_card": '<article class="card case">{}</article>', "metric_caption": '<ul class="nums"><li>{}</li></ul>'}
        for area, tpl in cases.items():
            lim = CFG["areas"][area]["limit"]
            ok = check.page_word_errors("x.html", page(tpl.format(words(lim))), CFG, {area})
            bad = check.page_word_errors("x.html", page(tpl.format(words(lim + 1))), CFG, {area})
            self.assertEqual(ok, [], area)
            self.assertEqual(len(bad), 1, area)
            self.assertIn(f"{area} · {lim + 1} words > {lim}", bad[0])

    def test_footer_limit(self):
        lim = CFG["areas"]["footer"]["limit"]
        self.assertTrue(check.page_word_errors("x.html", page("", words(lim + 1)), CFG, {"footer"}))
        self.assertEqual(check.page_word_errors("x.html", page("", words(lim)), CFG, {"footer"}), [])

    def test_closed_details_count_only_toward_the_details_limit(self):
        lim = CFG["areas"]["lesson_card"]["limit"]
        body = f'<article class="card aar"><h2>Title</h2><details><summary>More</summary><p>{words(200)}</p></details></article>'
        self.assertEqual(check.page_word_errors("x.html", page(body), CFG), [])
        open_ = body.replace("<details>", "<details open>")
        self.assertTrue(any("lesson_card" in e for e in check.page_word_errors("x.html", page(open_), CFG)))
        big = f'<details><summary>More</summary><p>{words(CFG["details_limit"] + 1)}</p></details>'
        errs = check.page_word_errors("x.html", page(big), CFG)
        self.assertTrue(any(" details · " in e for e in errs), errs)
        self.assertLess(lim, 200)
        nested = f'<details><summary>Reports</summary><p>{words(200)}</p><details><summary>One</summary><p>{words(200)}</p></details></details>'
        self.assertEqual(check.page_word_errors("x.html", page(nested), CFG), [], "each tap reveals at most details_limit words")

    def test_quotes_and_disclaimer_are_exempt(self):
        body = f'<p class="disclaimer">{words(60)}</p><blockquote><p>{words(90)}</p></blockquote>'
        self.assertEqual(check.page_word_errors("x.html", page(body), CFG), [])

    def test_word_counter_skips_separators(self):
        self.assertEqual(check.word_count("Correction · RSS · Follow → Source - History"), 5)

    def test_built_site_passes_and_records_are_exempt(self):
        self.assertEqual(check.word_limit_errors(), [])
        for p in CFG["enforced_pages"]:
            self.assertFalse(p.startswith(tuple(CFG["exempt"])), p)
        self.assertEqual(sorted(CFG["exempt"]), ["chat/", "timeline/archive/"])

    def test_enforced_pages_must_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            (t / "data/schema").mkdir(parents=True); (t / "site").mkdir()
            (t / "data/schema/word_limits.schema.json").write_text((ROOT / "data/schema/word_limits.schema.json").read_text())
            cfg = dict(CFG, enforced_pages=["gone/index.html"], data_checks={})
            (t / "data/word_limits.json").write_text(json.dumps(cfg))
            orig = check.load_schema
            check.load_schema = lambda n: json.loads((t / f"data/schema/{n}.schema.json").read_text())
            try:
                errs = check.word_limit_errors(t)
            finally:
                check.load_schema = orig
            self.assertTrue(any("gone/index.html isn't a built page" in e for e in errs), errs)


class Voice(unittest.TestCase):
    def test_banned_phrases_are_caught_and_the_brand_is_not(self):
        self.assertEqual(check.validate(VOICE, check.load_schema("voice")), [])
        self.assertIn("keep the dice", check.voice_hits("I keep the dice fair.", VOICE))
        self.assertIn("I'm new here", check.voice_hits("I\u2019m new here.", VOICE))
        self.assertTrue(check.voice_hits("that was sloppy work", VOICE))
        self.assertEqual(check.voice_hits("Slopworks, by slopryno: Shield owns security and privacy.", VOICE), [])

    def test_bio_only_phrases(self):
        self.assertEqual(check.voice_hits("I report honestly.", VOICE), [])
        self.assertIn("honestly", check.voice_hits("I report honestly.", VOICE, bio=True))

    def test_built_site_and_bios_pass(self):
        self.assertEqual(check.voice_errors(), [])


class Loosening(unittest.TestCase):
    def test_removing_an_enforced_page_or_phrase_is_loosening(self):
        self.assertTrue(check.words_loosened([], ['    "team/index.html",']))
        self.assertTrue(check.words_loosened(['    "a.html"'], ['    "a.html",', '    "b.html"']))
        self.assertTrue(check.loosening("data/voice.json", [], ['    "keep the dice",']))

    def test_adding_a_page_or_moving_a_comma_is_not(self):
        self.assertFalse(check.words_loosened(['    "a.html",', '    "b.html"'], ['    "a.html"']))
        self.assertFalse(check.loosening("data/word_limits.json", ['    "team/index.html"'], []))

    def test_raising_a_limit_or_changing_a_selector_is_loosening(self):
        old = '"lede": {"selector": "main p.lede", "limit": 25},'
        self.assertTrue(check.words_loosened(['"lede": {"selector": "main p.lede", "limit": 30},'], [old]))
        self.assertTrue(check.words_loosened(['"lede": {"selector": "main p.intro", "limit": 25},'], [old]))
        self.assertFalse(check.words_loosened(['"lede": {"selector": "main p.lede", "limit": 20},'], [old]))
        self.assertTrue(check.words_loosened(['"details_limit": 300,'], ['"details_limit": 250,']))
        self.assertTrue(check.words_loosened([], [old]))

    def test_adding_an_exemption_is_loosening(self):
        self.assertTrue(check.words_loosened(['"exempt": ["chat/", "timeline/archive/", "team/"],'], ['"exempt": ["chat/", "timeline/archive/"],']))
        self.assertTrue(check.words_loosened(['"exempt_selectors": ["blockquote", "p.disclaimer", "article"],'], ['"exempt_selectors": ["blockquote", "p.disclaimer"],']))
        self.assertFalse(check.words_loosened(['"exempt": ["chat/"],'], ['"exempt": ["chat/", "timeline/archive/"],']))

    def test_the_config_file_keeps_one_page_per_line(self):
        lines = (ROOT / "data/word_limits.json").read_text().splitlines()
        start = next(i for i, l in enumerate(lines) if '"enforced_pages"' in l)
        for l in lines[start + 1:]:
            if l.strip() in ("]", "}"):
                break
            self.assertRegex(l.strip(), r'^"[^"]+\.html",?$')


@unittest.skipUnless(mobile_audit.chrome() or os.environ.get("CI"), "headless Chrome not installed (required on CI)")
class FirstScreen(unittest.TestCase):
    """The first phone screen (390x844, closed details excluded) of every enforced page holds at most first_screen words."""
    def test_first_screen_budget(self):
        if not mobile_audit.chrome():
            raise AssertionError("CI needs headless Chrome for the first-screen budget")
        pages = CFG["enforced_pages"]
        if not pages:
            self.skipTest("no enforced pages yet")
        rows = mobile_audit.measure([390], only=pages)
        over = {r["page"]: r["words_above_fold"] for r in rows if r.get("error") or r["words_above_fold"] > CFG["first_screen"]}
        self.assertEqual(over, {})


if __name__ == "__main__":
    unittest.main()
