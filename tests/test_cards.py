"""Team trading cards (Ryno, 2026-10-20 12:18 PM ET: "Lock this design, have Comms polish the wording"). Trial's acceptance tests."""
import json, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import avatars, build, cards, check  # noqa: E402


def team_page(season):
    real = avatars.committed_season
    avatars.committed_season = lambda: season
    try:
        return build.build()["team/index.html"]
    finally:
        avatars.committed_season = real


class Cards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = cards.load()
        cls.roles = [n for n, *_ in build.team()]
        cls.pages = {s: team_page(s) for s in ("normal", "halloween", "winter")}

    def test_card_data_is_valid(self):
        self.assertEqual(cards.errors(roles=self.roles), [])
        self.assertEqual(sorted(self.spec["roles"]), sorted(self.roles))

    def test_types_are_real_world_job_functions(self):
        names = [t["name"] for t in self.spec["types"]]
        self.assertEqual(len(names), len(set(names)))
        self.assertLessEqual(len(names), 10)
        for t in names:  # no elemental or game types (Ryno, 11:53 AM ET)
            self.assertNotRegex(t.lower(), r"fire|water|grass|psychic|ghost|electric|dragon")

    def test_one_card_per_role_that_opens_without_script(self):
        for s, doc in self.pages.items():
            self.assertNotIn("<script", doc.lower(), s)
            self.assertEqual(doc.count('class="o" id="'), len(self.roles) + 1, s)  # plus Ryno's CEO card (scripts/ceo.py)
            for f in (ROOT / "bots").glob("*.md"):
                self.assertIn(f'href="#{f.stem}"', doc)
                self.assertIn(f'href="#m-{f.stem}"', doc)
                self.assertIn(f'href="{f.stem}/">Character sheet', doc)

    def test_tap_outside_closes_and_close_link_is_focusable(self):
        # Ryno, 2026-10-20 9:22 PM ET: no close button; tap outside the card to close. Escape would need script, so it isn't offered.
        for s, doc in self.pages.items():
            stems = [f.stem for f in (ROOT / "bots").glob("*.md")] + ["ryno"]
            for st in stems:  # the backdrop is the open card's own target: a full-screen link back to #m-, out of the tab order and hidden from screen readers
                self.assertIn(f'<a class="o" id="{st}" href="#m-{st}" tabindex="-1" aria-hidden="true"></a>', doc, (s, st))
                self.assertIn(f'<a class="cl" href="#m-{st}">Close</a>', doc, (s, st))  # a real link with words: in the tab order
            self.assertIn(".o:target{inset:0;z-index:8}", doc, s)
            self.assertIn("position:fixed;z-index:9;", doc, s)  # the open card sits above its backdrop, so taps inside it don't close it
            self.assertIn(".cl:not(:focus-visible){clip-path:inset(50%)}", doc, s)  # shown only when focused from the keyboard
            self.assertNotRegex(doc, r'class="cl"[^>]*(tabindex|aria-hidden)')

    def test_ids_are_unique_and_sprite_ids_prefixed(self):
        doc = self.pages["halloween"]
        ids = re.findall(r'\bid="([^"]+)"', doc)
        self.assertEqual(len(ids), len(set(ids)), [i for i in ids if ids.count(i) > 1][:5])
        for sym in re.findall(r'<symbol id="([^"]+)"', doc):
            self.assertTrue(sym.startswith(cards.P), sym)
        for use in re.findall(r'<use href="#([^"]+)"', doc):
            self.assertIn(use, ids)

    def test_numbers_come_from_the_ledger(self):
        doc, tot = self.pages["normal"], build.xp_totals(json.loads((ROOT / "data/xp_ledger.json").read_text()))
        levels = json.loads((ROOT / "data/progression.json").read_text())["levels"]
        for n in self.roles:
            num = build.level_for(tot.get(n, 0), levels)[0]
            self.assertIn(f"<b>{n}</b>", doc)
            self.assertIn(f"Lv\u00a0{num} · {tot.get(n, 0)}\u00a0XP", doc, n)

    def test_holiday_art_only_in_its_approved_season(self):
        self.assertIn("October edition: Halloween art.", self.pages["halloween"])
        self.assertIn(".g-forge{", self.pages["halloween"])
        for s in ("normal", "winter"):  # winter has no card art yet: it falls back to the type motif
            self.assertNotIn(".g-forge{", self.pages[s])
            self.assertNotIn("Halloween", self.pages[s])

    def test_badge_hook_renders_nothing_until_badges_ship(self):
        for doc in self.pages.values():
            self.assertNotIn('class="bd"', doc)
            self.assertNotIn("/badges/", doc)

    def test_comms_wording_rules(self):
        for n, r in self.spec["roles"].items():
            for m in r["moves"]:
                self.assertLessEqual(len(m["line"].split()), cards.MAX_LINE, (n, m["line"]))
            for k, line in r["flavour"].items():
                self.assertLessEqual(len(line.split()), 10, (n, k, line))
        text = json.dumps(self.spec).lower()
        for w in ("official", "endorsed", "real-time", "live agent", "separate agents"):  # unofficial fan project; roles, not live agents
            self.assertNotIn(w, text)

    def test_badges_sit_in_the_card_corner_not_on_the_blob(self):
        # Ryno, Oct 20 10:45-10:47 PM ET: the job badge moves off every blob to the card's corner; his is a gold crown.
        for s, doc in self.pages.items():
            self.assertEqual(doc.count('<svg class="jb" viewBox="-10 -10 20 20">'), len(self.roles) + 1, s)
        for s in ("normal", "halloween", "winter"):
            for name, svg in avatars.files(s).items():
                self.assertNotIn("translate(80 82)", svg, (s, name))
        self.assertIn('<path d="M-5 5l', self.pages["halloween"])  # his crown badge

    def test_minis_show_dots_not_level_text(self):
        css = (ROOT / "scripts/cards.css").read_text()
        self.assertIn(".card:not(.lead .card) .ml{position:absolute;white-space:nowrap;clip-path:inset(50%)}", css)  # read, not shown
        self.assertIn(".o:target~.card .ml{position:static;clip-path:none}", css)  # the open card keeps its level

    def test_team_page_fits_100_kb_in_every_season(self):
        for s, doc in self.pages.items():
            # the stylesheets Team loads (style.css; site/sheets.css loads on the character sheets only, Oct 20 3:06 PM ET)
            css = check.css_weight(check.page_css("team/index.html", doc, ROOT / "site"), ROOT / "site")
            if s == avatars.committed_season():
                total = check.page_weight("team/index.html", doc, css)[0]
            else:  # the other sets aren't on disk: count their avatar files from the generator
                files = avatars.files(s)
                imgs = check.page_images("team/index.html", doc)
                total = len(doc.encode()) + css + sum(len(files[i.split("avatars/", 1)[1]].encode()) for i in imgs if i.startswith("assets/avatars/"))
            self.assertLessEqual(total, 100_000, s)


if __name__ == "__main__":
    unittest.main()
