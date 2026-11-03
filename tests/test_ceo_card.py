"""Trial's tests for Ryno's CEO card and sheet (Ryno, Oct 20, 2026: 3:48 PM ET "lets let the rhino be the every day look and
the trading card background only changes with holiday theme"; 3:54 PM ET "Today, i will override and have the team review +
embedd a link to my x account")."""
import json, re, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import avatars, build, ceo, cards  # noqa: E402

SEASONS = ("normal", "halloween", "winter")


def mix(a, b, k):  # CSS color-mix(in srgb, a k, b)
    return "#" + "".join(f"{round(int(a[i:i + 2], 16) * k + int(b[i:i + 2], 16) * (1 - k)):02x}" for i in (1, 3, 5))


class Avatar(unittest.TestCase):
    def test_one_rhino_all_year(self):
        got = {s: avatars.files(s) for s in SEASONS}
        for f in ("ceo.svg", "still/ceo.svg"):
            self.assertEqual(len({got[s][f] for s in SEASONS}), 1, f)
        self.assertEqual(got["normal"]["ceo.svg"], avatars.fixed_svg("ceo"))
        for season, d in avatars.COSTUMES.items():
            self.assertNotIn("ceo", d, season)  # never in a costume set
        self.assertEqual(ceo.HOLIDAY, "background-only")
        self.assertIn('aria-label="Ryno, the human CEO, as a rhino"', got["normal"]["ceo.svg"])
        self.assertNotIn("#f2c14e", got["normal"]["ceo.svg"])  # no crown on the rhino (Ryno, Oct 20 10:45 PM ET)

    def test_no_photo_no_outside_image(self):
        s = avatars.fixed_svg("ceo")
        self.assertNotIn("<image", s)
        self.assertNotIn("href", s)
        self.assertLess(len(s.encode()), 3000)

    def test_contrast_on_his_card_and_the_pages(self):
        """Body and outline: on every art background one of them is 3:1; the eyes are 3:1 on the face."""
        spec = cards.load()
        ty = next(t for t in spec["types"] if t["name"] == ceo.TYPE)
        backs = []
        for card in ("#ffffff", "#1c1c22"):  # --card in light and dark: the art window's centre and edge (scripts/cards.css .art)
            backs += [mix(ty["tint"].lower(), card, .85), mix(ty["colour"].lower(), card, .35)]
        backs += re.findall(r"#[0-9a-f]{6}", ceo.ART["halloween"]["scene"].split("linear-gradient", 1)[1])
        backs += ["#f6f5f1", "#141418", "#ffffff", "#1c1c22"]  # pages and card colours, where the still copy shows
        for b in backs:
            self.assertGreaterEqual(max(avatars.ratio(avatars.CEO_SLATE, b), avatars.ratio(avatars.CEO_LINE, b)), 3.0, b)
        self.assertGreaterEqual(avatars.ratio(avatars.EYE, avatars.CEO_SLATE), 3.0)
        self.assertIn(f'fill="{avatars.CEO_SLATE}" stroke="{avatars.CEO_LINE}"', avatars.fixed_svg("ceo"))


class Card(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = build.build()
        cls.team, cls.sheet = cls.files["team/index.html"], cls.files["team/ryno/index.html"]

    def test_ceo_group_comes_first(self):
        t = self.team
        self.assertLess(t.index('id="card-ryno"'), t.index('id="card-coordinator"'))
        self.assertEqual(t.count('id="card-'), len(build.team()) + 1)
        slot = t[t.index('<li class="slot t0 lead'):t.index('id="card-coordinator"')]
        for want in ('id="card-ryno"', "One of one", f"00/{len(build.team())}",
                     "Management", "Human verified", '<p class="lv" title="Management">CEO</p>', "Safeguard", "Unblock", "Vision", 'src="../assets/avatars/ceo.svg"', 'href="ryno/">Character sheet'):
            self.assertIn(want, slot)
        for no in ("\u00a0XP", "Lv\u00a0", "--w:", "<script"):
            self.assertNotIn(no, slot)

    def test_numbers_come_from_the_records(self):
        f = ceo.facts()
        load = lambda n: json.loads((ROOT / "data" / n).read_text())
        self.assertEqual(f["approvals"], len(load("ceo_decisions.json")))
        self.assertEqual(f["overrides"], len(load("ceo_overrides.json")))
        self.assertEqual(f["decisions"], sum(1 for i in load("ideas.json") if i.get("decided_by") == "CEO"))
        for (_, _, _, rec, unit) in ceo.MOVES:
            self.assertIn(f'<em>{f[rec]}<small> {unit[0 if f[rec] == 1 else 1]}</small></em>', self.team)
        for x in load("ceo_overrides.json"):  # Ryno, Oct 21 8:51 AM ET: no CEO quotes on the site; each override is listed by its date
            self.assertNotIn(x["quote"], self.sheet)
            self.assertIn(f'<time datetime="{x["at"][:10]}">', self.sheet)
        for x in load("ceo_decisions.json"):
            self.assertIn(f'PR #{x["pr"]}', self.sheet)

    def test_holiday_changes_only_the_background(self):
        spec, n = cards.load(), len(build.team())
        out = {s: ceo.card(cards, spec, s, n, "../assets/avatars/ceo.svg") for s in SEASONS}
        self.assertIn("g-ryno", out["halloween"])
        self.assertNotIn("g-ryno", out["normal"])
        strip = lambda h: h.replace(" g-ryno", "").replace(" " + ceo.ART["halloween"]["particles"] + '"', ' P"')
        norm = cards.load()["types"][[t["name"] for t in spec["types"]].index(ceo.TYPE)]["particles"]
        self.assertEqual(strip(out["halloween"]), out["normal"].replace(" " + norm + '"', ' P"'))  # same card, same avatar
        self.assertIn(".g-ryno{--g:", ceo.css("halloween"))
        self.assertNotIn(".g-ryno", ceo.css("normal"))

    def test_sheet_stands_alone(self):
        s = self.sheet
        self.assertIn("<title>Ryno: character sheet", s)
        self.assertIn('src="../../assets/avatars/ceo.svg"', s)
        self.assertIn('href="../#card-ryno"', s)
        self.assertEqual(re.findall(r'<link rel="stylesheet" href="([^"]+)"', s), ["../../style.css", "../../sheets.css"])  # the bots' card back, cached
        self.assertNotIn("<script", s)

    def test_sheet_is_three_power_cards(self):
        # Cards v6 (CEO direction, Oct 21): his own card back with Safeguard, Unblock and Vision as three cards, each with its
        # real count and its record behind a fold; no quote of his anywhere on it.
        s, f = self.sheet, ceo.facts()
        for (_, name, _, rec, unit) in ceo.MOVES:
            m = re.search(rf'<li id="{ceo.ABIL[rec]}"><div class="ph">.*?<h2>{name}</h2><p class="n">(\d+)<small>', s)
            self.assertTrue(m, name)
            self.assertEqual(int(m.group(1)), f[rec])
        self.assertEqual(s.count("<summary>The record ("), 3)
        load = lambda n: json.loads((ROOT / "data" / n).read_text())
        for r in load("ceo_decisions.json") + load("ceo_overrides.json"):
            if r.get("quote"):
                self.assertNotIn(r["quote"], s)
        self.assertNotIn("\u201c", s)


class XLink(unittest.TestCase):
    """His public X profile, as a plain link: nothing loaded from X, no tracking referrer, and no other X address."""
    def test_exact_link_and_nothing_else_from_x(self):
        self.assertEqual(ceo.X_URL, "https://x.com/slopryno")
        files = build.build()
        seen = []
        for name, doc in files.items():
            if not name.endswith(".html"):
                continue
            for m in re.finditer(r'<[^>]+(?:x\.com|twitter\.com|twimg\.com)[^>]*>', doc):
                tag = m.group(0)
                self.assertTrue(tag.startswith("<a "), (name, tag))  # no img, iframe, script or stylesheet from X
                for u in re.findall(r'href="(https://(?:x|twitter)\.com/[^"]+)"', tag):
                    if "/status/" in u:
                        continue  # cited posts (data sources), unchanged
                    self.assertEqual(u, ceo.X_URL, (name, tag))  # the only profile link on the site
                    self.assertIn('rel="noopener noreferrer"', tag, name)
                    seen.append(name)
        self.assertEqual(sorted(set(seen)), ["team/index.html", "team/ryno/index.html"])
        self.assertEqual(seen.count("team/index.html"), 1)

    def test_label_shows_the_public_handle_only(self):
        self.assertIn(">slopryno on X</a>", ceo.X_LINK)
        self.assertNotIn("@", ceo.X_LINK)


if __name__ == "__main__":
    unittest.main()
