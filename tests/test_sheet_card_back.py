"""Trial's tests for the character sheet as the card back (Ryno, 2026-10-20 3:06 PM ET: "Go with B, the card back").
Numbers and words come from the records, the CSS is one shared file counted only where it loads, the quest note
can't go stale, the badge case stays hidden until badges ship, and the holo-rare shine selector matches."""
import json, re, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import avatars, build, cards, check, sheets  # noqa: E402

STEMS = {f.stem.capitalize(): f.stem for f in (ROOT / "bots").glob("*.md")}


class CardBack(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = build.build()
        cls.spec, cls.prog = cards.load(), build.load("progression")
        cls.tot = build.xp_totals(build.load("xp_ledger"))
        cls.sheets = {n: cls.files[f"team/{s}/index.html"] for n, s in STEMS.items()}
        cls.main = {n: d.split("<main", 1)[1].split("</main>")[0] for n, d in cls.sheets.items()}

    def test_shared_stylesheet_no_inline_style(self):
        self.assertIn("sheets.css", self.files)
        season = avatars.committed_season() or "normal"
        self.assertEqual(self.files["sheets.css"], sheets.css(self.spec, season, {n: f[:-3] for n, _, _, _, f in build.team()}))
        for n, d in self.sheets.items():
            self.assertIn('<link rel="stylesheet" href="../../sheets.css">', d, n)
            self.assertNotIn("<style", d, n)
        self.assertNotIn("sheets.css", self.files["team/index.html"], "Team keeps its own card CSS")
        self.assertEqual(sheets.errors(self.files), [])

    def test_banner_is_the_card_from_the_records(self):
        order = [m for _, ms in build.GROUPS for m in ms]
        for n, d in self.main.items():
            r = self.spec["roles"][n]
            num = build.level_for(self.tot.get(n, 0), self.prog["levels"])[0]
            # No visible type pill (Ryno, Oct 20, #135): the type is the icon's accessible name, like the cards' hidden text
            self.assertIn(f'role="img" aria-label="{build.e(r["type"])}"', d, n)
            self.assertNotIn(f"<b>{build.e(r['type'])}</b>", d, n)
            self.assertIn(f'<p class="gm">{cards.rarity(num, self.spec)[1]}</p>', d, n)
            self.assertIn(f">{order.index(n) + 1:02d}/{len(STEMS)}</p>", d, n)
            self.assertIn(f'href="../#card-{STEMS[n]}"', d, n)  # back to the open card on Team
            for m in r["moves"]:
                self.assertIn(build.e(m["name"]), d, n)
            self.assertIn(' holo"' if num >= 4 else f"r{cards.rarity(num, self.spec)[0]}", d, n)

    def test_comms_wording(self):
        for n, d in self.main.items():
            self.assertIn('<h2 id="work">Recent work</h2>', d, n)
            self.assertNotIn("Recent wins", d, n)
            qt = re.search(r'<section class="tile qt".*?</section>', d, re.S).group(0)
            self.assertNotRegex(qt, r"\((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d", n)  # the quest note carries no date
            self.assertNotIn("`", d, n)  # role-file backticks render as <code>
        self.assertIn("<code>plans/direction.md</code>", self.main["Coordinator"])
        locked = [a for a in self.prog["achievements"] if a["event"] == "block_upheld"][0]
        self.assertIn(f"Not yet: {locked['rule'][0].lower() + locked['rule'][1:]}", self.main["Gamemaster"])  # words, not colour alone

    def test_quest_note_cant_go_stale(self):
        self.assertEqual(sheets.quest_note({"later_weeks": {}}), "")
        self.assertIn("Week 2", sheets.quest_note({"later_weeks": {"week2": "x"}}))
        self.assertNotRegex(sheets.quest_note({"later_weeks": {"week2": "x"}}), r"\d{1,2}\)|Oct|Nov|Dec")
        dated = {"team/x/index.html": '<link rel="stylesheet" href="../../sheets.css">Tracking starts in Week 2 (Oct 22)'}
        self.assertTrue(sheets.errors(dated))
        self.assertTrue(sheets.errors({"team/x/index.html": "<style>x</style>"}))

    def test_badge_case_hidden_until_badges_ship(self):
        for n, d in self.main.items():
            self.assertNotIn("assets/badges/", d, n)
            self.assertNotIn('class="bc"', d, n)

    def test_details_stay_under_the_comms_cap(self):
        cap = json.loads((ROOT / "data/word_limits.json").read_text())["details_limit"]
        for n, d in self.main.items():
            for blk in re.findall(r"<details\b.*?</details>", d, re.S):
                self.assertLessEqual(len(re.sub(r"<[^>]+>", " ", blk).split()), cap, n)

    def test_holo_rare_shine_selector_matches(self):
        css = (ROOT / "scripts/cards.css").read_text()
        self.assertIn(".holo.r4 .card::after", css)
        self.assertNotIn(".holo:has(.r4)", css)  # r4 sits on the same element as holo, so :has() never matched

    def test_stylesheet_counts_only_where_it_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site"
            (site / "team/a").mkdir(parents=True)
            (site / "style.css").write_text("x" * 100)
            (site / "sheets.css").write_text("y" * 900)
            sheet = '<link rel="stylesheet" href="../../style.css"><link rel="stylesheet" href="../../sheets.css">'
            (site / "team/a/index.html").write_text(sheet)
            (site / "index.html").write_text('<link rel="stylesheet" href="style.css">')
            self.assertEqual(check.page_css("team/a/index.html", sheet, site), {"style.css", "sheets.css"})
            self.assertEqual(check.page_css("index.html", "", site), {"style.css"})
            errs = check.page_weight_errors(Path(tmp), limit=900)
            self.assertTrue(any("team/a/index.html" in x for x in errs))
            self.assertFalse(any(x.startswith("site/index.html") for x in errs))

    def test_every_sheet_within_budget_with_its_stylesheets(self):
        site = ROOT / "site"
        for s in STEMS.values():
            rel = f"team/{s}/index.html"
            doc = (site / rel).read_text()
            total, missing = check.page_weight(rel, doc, check.css_weight(check.page_css(rel, doc, site), site))
            self.assertEqual(missing, [])
            self.assertLessEqual(total, check.PATTERNS["max_page_bytes"], rel)
        self.assertIn("sheet_errors()", __import__("inspect").getsource(check.run_repo))


    def test_paths_and_file_names_break_at_slash_and_underscore_only(self):
        self.assertEqual(sheets.wbr("Added tests/test_a_b.py"), "Added tests/<wbr>test_<wbr>a_<wbr>b.py")
        self.assertEqual(sheets.wbr("a<b"), "a&lt;b")


if __name__ == "__main__":
    unittest.main()
