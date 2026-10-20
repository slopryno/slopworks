"""Trial's tests for the seasonal avatar sets (Ryno, 2026-10-19 9:30 PM ET: "Ship tomorrow but make them see-through, no tiles")."""
import re, subprocess, sys, unittest
from datetime import date
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import avatars, build, check  # noqa: E402

LIGHT, DARK = "#f6f5f1", "#141418"
BACKS = (LIGHT, DARK, "#ffffff", "#1c1c22")  # both pages and both card colours


class DateSwitch(unittest.TestCase):
    def test_windows_and_edges(self):
        cases = {(10, 14): "normal", (10, 15): "halloween", (10, 20): "halloween", (10, 31): "halloween", (11, 1): "normal",
                 (11, 30): "normal", (12, 1): "winter", (12, 25): "winter", (12, 26): "winter", (12, 27): "normal", (1, 1): "normal",
                 (2, 29): "normal", (7, 4): "normal"}
        for (m, d), want in cases.items():
            self.assertEqual(avatars.season_for(date(2028, m, d)), want, (m, d))

    def test_every_year(self):
        for y in (2026, 2027, 2030):
            self.assertEqual(avatars.season_for(date(y, 10, 15)), "halloween")
            self.assertEqual(avatars.season_for(date(y, 12, 26)), "winter")

    def test_oct_20_build_is_halloween(self):
        got = avatars.files(avatars.season_for(date(2026, 10, 20)))
        self.assertEqual(got, avatars.files("halloween"))
        normal = avatars.files("normal")
        for n in avatars.HALLOWEEN:
            self.assertNotEqual(got[f"{n}.svg"], normal[f"{n}.svg"], n)
            self.assertIn(", Halloween", got[f"{n}.svg"], n)

    def test_cli_check_matches_committed_set(self):
        have = avatars.committed_season()
        self.assertIsNotNone(have, "committed avatars must be one complete set: run python3 scripts/avatars.py")
        inside = {"normal": "2026-07-01", "halloween": "2026-10-20", "winter": "2026-12-10"}
        for season, d in inside.items():
            r = subprocess.run([sys.executable, "scripts/avatars.py", "--check", "--date", d], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0 if season == have else 1, (season, r.stdout))


class Sets(unittest.TestCase):
    def test_normal_set_is_the_v2_blob(self):
        out = avatars.files("normal")
        for i, (n, spec) in enumerate(avatars.ROLES.items()):
            self.assertEqual(out[f"{n}.svg"], avatars.svg(i, n, *spec))

    def test_every_team_role_has_both_costumes(self):
        for n, *_ in build.team():
            key = build.avatar_of(n)
            self.assertIn(key, avatars.HALLOWEEN, n)
            self.assertIn(key, avatars.WINTER, n)

    def test_style_rules_every_set(self):
        for season in ("normal", "halloween", "winter"):
            for f, s in avatars.files(season).items():
                self.assertLess(len(s.encode()), 3000, f)
                self.assertNotIn("<script", s, f)
                self.assertNotIn("<text", s, f)
                self.assertNotIn('<rect width="100" height="100"', s, f)  # see-through, no tile
                self.assertNotIn("href=\"http", s, f)
                self.assertRegex(s, r'aria-label="[^"]+"', f)
                if f.startswith("still/"):
                    self.assertNotIn("<style", s, f)
                    self.assertNotIn("animation", s, f)
                else:
                    self.assertIn("@keyframes", s, f)
                    self.assertIn("prefers-reduced-motion", s, f)

    def test_no_loop_faster_than_0_9s(self):
        for season in ("halloween", "winter"):
            for f, s in avatars.files(season).items():
                for t in re.findall(r"animation:\w+ ([\d.]+)s", s):
                    self.assertGreaterEqual(float(t), .9, f)

    def test_still_copies_are_committed(self):
        for n in avatars.ROLES:
            self.assertTrue((ROOT / f"site/assets/avatars/still/{n}.svg").exists(), n)


class Contrast(unittest.TestCase):
    def test_eyes_on_their_face(self):
        for season, d in avatars.COSTUMES.items():
            for n, ch in d.items():
                self.assertGreaterEqual(avatars.ratio(avatars.EYE, ch["face"]), 3.0, (season, n))

    def test_band_is_3_to_1_on_both_pages(self):
        for start, L in zip(("#000000", "#ffffff"), avatars.BAND):  # the band's own edges, from the inside
            c = avatars._into(start, L)
            for b in BACKS:
                self.assertGreaterEqual(avatars.ratio(c, b), 3.0, (L, b))

    def test_every_rim_and_unrimmed_outer_fill_is_in_band(self):
        """A shape too light (or dark) for one theme carries a same-hue rim that reads on both."""
        for season in ("halloween", "winter"):
            for f, s in avatars.files(season).items():
                if f.startswith("still/"):
                    continue
                for rim in re.findall(r'stroke="(#\w{6})" stroke-width="[\d.]+" stroke-linejoin="round" paint-order="stroke"', s):
                    for b in BACKS:
                        self.assertGreaterEqual(avatars.ratio(rim, b), 3.0, (f, rim, b))

    def test_fit(self):
        for c in ("#ffffff", "#f4f4f4", "#f6c445", "#3fb8af", "#e03a3e", "#5c6482", "#2d333b", "#000000", "#f26b0f"):
            f, r = avatars.fit(c)
            ok = lambda x: all(avatars.ratio(x, b) >= 3 for b in BACKS)
            self.assertTrue(ok(f) or (r and ok(r)), c)


class Pages(unittest.TestCase):
    def test_long_lists_use_still_copies(self):
        files = build.build()
        self.assertIn("assets/avatars/still/", files["chat/index.html"])
        self.assertNotRegex(files["chat/index.html"], r'assets/avatars/(?!still/)\w+\.svg')

    def test_team_and_role_pages_animate(self):
        files = build.build()
        self.assertNotIn("avatars/still/", files["team/index.html"])
        self.assertIn("avatars/lens.svg", files["team/lens/index.html"])
        self.assertNotIn("avatars/still/", files["team/lens/index.html"])

    def test_still_copies_need_polish_and_shield(self):
        self.assertEqual(check.required_roles(["site/assets/avatars/still/lens.svg"]), {"Polish", "Shield"})


if __name__ == "__main__":
    unittest.main()
