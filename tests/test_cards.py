"""Team trading cards (Ryno, 2026-10-20 12:18 PM ET: "Lock this design, have Comms polish the wording"). Trial's acceptance tests."""
import json, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import avatars, build, cards, ceo, check  # noqa: E402
import golden  # noqa: E402


def team_page(season):
    real = avatars.committed_season
    avatars.committed_season = lambda: season
    try:
        return build.build()["team/index.html"]
    finally:
        avatars.committed_season = real


def stems_of(spec):
    return {n: n.lower() for n in spec["roles"]}


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

    def test_no_script_and_every_role_has_a_card_and_sheet_link(self):
        for s, doc in self.pages.items():
            self.assertNotIn("<script", doc.lower(), s)
            for f in (ROOT / "bots").glob("*.md"):
                self.assertIn(f'id="card-{f.stem}"', doc, (s, f.stem))
                self.assertIn(f'href="{f.stem}/">Character sheet', doc, (s, f.stem))
            self.assertIn('id="card-ryno"', doc, s)
            self.assertIn('href="ryno/">Character sheet', doc, s)

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
        css = (ROOT / "scripts/cards.css").read_text()
        rule = re.search(r"\.sh::after\{([^}]*)\}", css).group(1)
        self.assertIn("inset:6px", rule)
        self.assertIn("border:2px solid var(--a)", rule)
        dur, n = re.search(r"animation:rg ([\d.]+)s \S+ (\d+)", rule).groups()
        self.assertLessEqual(float(dur) * int(n), 5)
        self.assertRegex(css, r"prefers-reduced-motion:reduce\)\{[^{]*\.sh::after[^{]*\{animation:none")
        self.assertIn(".lead .lk{--a:#b8860b}", ceo.css("normal"))

    def test_holiday_scenes_stay_off_the_team_css(self):
        # Team deck uses season avatar SVGs; .g-* holiday scenes stay on character sheets (budget).
        stems = stems_of(self.spec)
        self.assertIn(".g-forge{", cards.css(self.spec, "halloween", stems))
        self.assertNotIn(".g-forge{", cards.css_team(self.spec, "halloween", stems))
        h, n = avatars.files("halloween"), avatars.files("normal")
        self.assertNotEqual(h["forge.svg"], n["forge.svg"])

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

    def test_job_badge_stays_off_the_blob(self):
        # Ryno, Oct 20 10:45-10:47 PM ET: the job badge moves off every blob to the card's corner; his is a gold crown.
        for s in ("normal", "halloween", "winter"):
            for name, svg in avatars.files(s).items():
                self.assertNotIn("translate(80 82)", svg, (s, name))

    def test_deck_css_ships_with_team_page(self):
        css = (ROOT / "scripts/deck.css").read_text()
        self.assertIn("scroll-snap-type:x mandatory", css)
        self.assertNotIn(".list-toggle", css)
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

    def test_normalized_team_html_and_css_team_match_goldens(self):
        stems = stems_of(self.spec)
        for s, doc in self.pages.items():
            golden.assert_matches(self, f"team-{s}.html", golden.normalize_team(golden.team_slice(doc)))
            # css_team is currently identical across seasons; each season still has to match the same golden
            # so a later season-specific rule cannot slip in unnoticed.
            golden.assert_matches(self, "css_team.css", cards.css_team(self.spec, s, stems))

    def test_record_refresh_leaves_goldens_untouched(self):
        xp_path, wins_path = ROOT / "data/xp_ledger.json", ROOT / "data/wins.json"
        xp_orig, wins_orig = xp_path.read_text(), wins_path.read_text()
        try:
            xp = json.loads(xp_orig)
            for row in xp:
                if row.get("agent") == "Forge":
                    row["base_xp"] = int(row["base_xp"]) + 50
                    break
            else:
                self.fail("need a Forge ledger row to simulate a records refresh")
            wins = json.loads(wins_orig)
            latest = None
            for row in wins:
                if row.get("role") != "Forge":
                    continue
                key = row.get("merged") or row["date"]
                if latest is None or key > (latest.get("merged") or latest["date"]):
                    latest = row
            if latest is None:
                self.fail("need a Forge win to simulate a records refresh")
            previous_pr = latest["pr"]
            latest["pr"] = "https://github.com/slopryno/slopworks/pull/99999"
            xp_path.write_text(json.dumps(xp))
            wins_path.write_text(json.dumps(wins))
            before = self.pages["winter"]
            xp_before = re.search(r'vh">Forge</span>.*?<li><b>XP</b><em>(\d+)</em>', before, re.S).group(1)
            doc = team_page("winter")
            xp_after = re.search(r'vh">Forge</span>.*?<li><b>XP</b><em>(\d+)</em>', doc, re.S).group(1)
            self.assertIn("pull/99999", doc, "the mutated last-verified PR should appear before normalize")
            self.assertNotEqual(xp_after, xp_before, "the ledger bump must change Forge's XP so this is a real records refresh")
            self.assertNotIn("pull/99999", golden.normalize_team(doc))
            golden.assert_matches(self, "team-winter.html", golden.normalize_team(golden.team_slice(doc)))
            golden.assert_matches(self, "css_team.css", cards.css_team(self.spec, "winter", stems_of(self.spec)))
        finally:
            xp_path.write_text(xp_orig)
            wins_path.write_text(wins_orig)

    def test_a_markup_or_css_change_fails_with_a_clear_diff(self):
        self.assertFalse(golden.update_mode(), "UPDATE=1 would rewrite goldens; this test must see the failure")
        doc = golden.normalize_team(golden.team_slice(self.pages["winter"]))
        bumped = doc.replace('class="flip"', 'class="flip pilot"', 1)
        with self.assertRaises(AssertionError) as ctx:
            golden.assert_matches(self, "team-winter.html", bumped)
        msg = str(ctx.exception)
        self.assertIn("golden team-winter.html differs", msg)
        self.assertIn("flip pilot", msg)
        self.assertIn("--- goldens/team-winter.html", msg)
        css = cards.css_team(self.spec, "winter", stems_of(self.spec)) + "\n.pilot{color:red}\n"
        with self.assertRaises(AssertionError) as ctx:
            golden.assert_matches(self, "css_team.css", css)
        self.assertIn("+.pilot{color:red}", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
