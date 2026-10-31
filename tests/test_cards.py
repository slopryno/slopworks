"""Team trading cards (Ryno, 2026-10-20 12:18 PM ET: "Lock this design, have Comms polish the wording"). Trial's acceptance tests."""
import json, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import avatars, build, cards, ceo, check  # noqa: E402


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
            self.assertEqual(doc.count('class="flip"'), len(self.roles) + 1, s)  # plus Ryno's CEO card
            self.assertIn('class="scrub"', doc, s)
            self.assertIn('class="list-toggle"', doc, s)
            self.assertIn('class="deck-wrap"', doc, s)
            for f in (ROOT / "bots").glob("*.md"):
                self.assertIn(f'id="card-{f.stem}"', doc)
                self.assertIn(f'href="#{ "card-" + f.stem}"', doc) if False else self.assertIn(f'href="#card-{f.stem}"', doc)
                self.assertIn(f'href="{f.stem}/">Character sheet', doc)

    def test_flip_is_native_details_with_list_and_scrub(self):
        # Mobile UX playbook 2026-10-31: details/summary flip, scrub chips, list escape — no :target overlay.
        for s, doc in self.pages.items():
            stems = [f.stem for f in (ROOT / "bots").glob("*.md")] + ["ryno"]
            for st in stems:
                self.assertIn(f'id="card-{st}"', doc, (s, st))
            self.assertIn("Flip", doc, s)  # via CSS content on .face.front::after
            self.assertIn("List (", doc, s)  # list-toggle summary
            self.assertIn("scroll-snap-type:x mandatory", doc, s)
            self.assertNotIn(".o:target{inset:0;z-index:8}", doc, s)

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
            self.assertIn(f">{n}</p>", doc)  # front face name
            self.assertIn(f"Lv <span>{num}</span>", doc, n)

    def test_cards_v6_stay_uncluttered(self):
        # Cards v6 (CEO direction, Oct 21): no XP words on a card, no pip bars by the move counts, and Weak to / Resists /
        # Hands off only on the character sheets.
        for s, doc in self.pages.items():
            self.assertNotIn("\u00a0XP</span>", doc, s)
            self.assertNotIn(" XP to ", doc, s)
            self.assertNotIn('class="pp', doc, s)
            self.assertNotIn('<p class="wr">', doc, s)
        css = (ROOT / "scripts/cards.css").read_text()
        self.assertNotIn(".wr{", css)  # its rules live in scripts/sheets.css now
        self.assertIn(".wr{", (ROOT / "scripts/sheets.css").read_text())

    def test_sheet_icon_has_a_calm_tap_cue(self):
        # Cards v6 (CEO direction, Oct 21): a square outline around the sheet icon, in the card's colour (gold on the CEO's),
        # pulsing 3 times and then still (under 5 s, WCAG 2.2.2), standing still for reduced motion, inside the 44px tap box.
        import re as _re
        css = (ROOT / "scripts/cards.css").read_text()
        rule = _re.search(r"\.sh::after\{([^}]*)\}", css).group(1)
        self.assertIn("inset:6px", rule)
        self.assertIn("border:2px solid var(--a)", rule)
        dur, n = _re.search(r"animation:rg ([\d.]+)s \S+ (\d+)", rule).groups()
        self.assertLessEqual(float(dur) * int(n), 5)
        self.assertRegex(css, r"prefers-reduced-motion:reduce\)\{[^{]*\.sh::after[^{]*\{animation:none")
        self.assertIn(".lead .lk{--a:#b8860b}", ceo.css("normal"))

    def test_holiday_art_only_in_its_approved_season(self):
        self.assertIn("October edition: Halloween art.", self.pages["halloween"])
        # Team deck uses season avatar SVGs; .g-* holiday scenes stay on character sheets (budget).
        stems = {n: n.lower() for n in self.spec["roles"]}
        self.assertIn(".g-forge{", cards.css(self.spec, "halloween", stems))
        self.assertNotIn(".g-forge{", cards.css_team(self.spec, "halloween", stems))
        h, n = avatars.files("halloween"), avatars.files("normal")
        self.assertNotEqual(h["forge.svg"], n["forge.svg"])
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

    def test_deck_css_ships_with_team_page(self):
        css = (ROOT / "scripts/deck.css").read_text()
        self.assertIn("scroll-snap-type:x mandatory", css)
        self.assertIn(".list-toggle", css)
        self.assertIn("prefers-reduced-motion", css)

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
