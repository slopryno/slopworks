"""Trial's tests for the character sheets and How XP works (i34, Week 1): numbers on the page are the computed ones,
every link lands, a 0-XP role is shown honestly, and there's no leaderboard wording (Critic, c185)."""
import json, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import build, check  # noqa: E402
from test_timeline import resolve_all  # noqa: E402

STEMS = {f.stem.capitalize(): f.stem for f in (ROOT / "bots").glob("*.md")}


class Sheets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = build.build()
        cls.led, cls.prog = build.load("xp_ledger"), build.load("progression")
        cls.tot = build.xp_totals(cls.led)

    def test_every_role_has_a_sheet_linked_from_its_card(self):
        team = self.files["team/index.html"]
        for n, s in STEMS.items():
            self.assertIn(f"team/{s}/index.html", self.files, n)
            self.assertIn(f'href="{s}/">Character sheet</a>', team, n)
        self.assertIn('href="xp/"', team)

    def test_sheet_numbers_are_computed(self):
        for n, s in STEMS.items():
            doc = self.files[f"team/{s}/index.html"]
            x = self.tot.get(n, 0)
            num, lv, nxt = build.level_for(x, self.prog["levels"])
            self.assertIn(f"<strong>{x} XP</strong>", doc, n)
            self.assertIn(f"Level {num} · {lv['name']}", doc, n)
            if nxt:
                self.assertIn(f"{nxt['xp'] - x} XP to {nxt['name']}", doc, n)
            ok = sum(y["agent"] == n and y["status"] == "approved" for y in self.led)
            self.assertIn(f"{ok} entries count", doc, n)
            self.assertIn(f"Level {num}, {lv['name']}, {x} XP", self.files["team/index.html"], n)

    def test_zero_xp_shown_honestly(self):
        zero = [n for n in STEMS if not self.tot.get(n)]
        self.assertIn("Gamemaster", zero, "Game Master never awards XP and has no work yet")
        for n in zero:
            doc = self.files[f"team/{STEMS[n]}/index.html"]
            self.assertIn("No XP yet. Every role starts here.", doc)
            self.assertIn("width:0%", doc)

    def test_links_resolve_and_no_scripts(self):
        merged = {w["pr"] for w in build.load("wins")}
        pages, n = resolve_all(self.files, self, prefix="team/", check_prs=False)
        self.assertGreater(n, 100)
        for k in pages:
            for pr in re.findall(r'href="(https://github\.com/slopryno/slopworks/pull/\d+)[#"]', self.files[k]):
                self.assertIn(pr, merged, f"{k}: {pr} is not a merged PR")
        for k in pages:
            self.assertNotIn("<script", self.files[k].lower(), k)
            self.assertLess(len(self.files[k].encode()), check.PATTERNS["max_page_bytes"], k)

    def test_no_contest_words(self):
        for k in [f"team/{s}/index.html" for s in STEMS.values()] + ["team/xp/index.html"]:
            main = re.sub(r"<[^>]+>", " ", self.files[k].split("<main", 1)[1].split("</main>")[0])
            main = re.sub(r"Team chat|team/", "", main)
            self.assertNotRegex(main.lower(), r"\b(leaderboard|top performer|ranked|best role)\b", k)

    def test_explainer_covers_rules_and_later_weeks(self):
        doc = self.files["team/xp/index.html"]
        for l in self.prog["levels"]:
            self.assertIn(f"<td>{l['name']}</td><td>{l['xp']}</td>", doc)
        for w in ("Week 2:", "Week 3:", "Week 4:", "quests", "raid", "Skill trees" if "Skill trees" in doc else "skill trees"):
            self.assertIn(w, doc)
        for r in self.prog["anti_gaming"]:
            self.assertIn(build.e(r), doc)
        self.assertIn(build.BASE + "team/xp/", self.files["sitemap.xml"])
        self.assertIn(build.BASE + "team/xp/", self.files["llms.txt"])


if __name__ == "__main__":
    unittest.main()
