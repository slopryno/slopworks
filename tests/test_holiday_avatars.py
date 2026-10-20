"""Trial's tests for the seasonal avatar sets (Ryno, 2026-10-19 9:30 PM ET: "Ship tomorrow but make them see-through, no tiles"; 9:52 PM ET: "Should be a full month of themed look so Oct 15 should be Oct 1";
9:56 PM ET: "Yes, holiday looks wait for my yes before switching on")."""
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
        cases = {(9, 30): "normal", (10, 1): "halloween", (10, 14): "halloween", (10, 15): "halloween", (10, 20): "halloween", (10, 31): "halloween", (11, 1): "normal",
                 (11, 30): "normal", (12, 1): "winter", (12, 25): "winter", (12, 26): "winter", (12, 27): "winter", (12, 31): "winter", (1, 1): "normal",
                 (2, 29): "normal", (7, 4): "normal"}
        for (m, d), want in cases.items():
            self.assertEqual(avatars.in_window(date(2028, m, d)), want, (m, d))

    def test_every_year(self):
        for y in (2026, 2027, 2030):
            self.assertEqual(avatars.in_window(date(y, 10, 1)), "halloween")
            self.assertEqual(avatars.in_window(date(y, 12, 31)), "winter")

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
        for d in ("2026-07-01", "2026-10-20", "2026-12-10"):
            want = avatars.season_for(date.fromisoformat(d))
            r = subprocess.run([sys.executable, "scripts/avatars.py", "--check", "--date", d], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0 if want == have else 1, (d, want, r.stdout))


def _cal(yes_status=None, theme="halloween-2028", window=("2028-10-01", "2028-10-31"), avatar_set="halloween"):
    """A minimal data/calendar.json: one scheduled theme, and its ceo-yes event when yes_status is given."""
    ev = [{"id": "x-plan", "date": "2028-09-01", "title": "plan", "owner": "Coordinator", "type": "holiday-theme",
           "status": "done", "theme": theme, "step": "plan"}]
    if yes_status:
        ev.append({"id": "x-yes", "date": "2028-09-24", "title": "Ryno's yes", "owner": "Ryno", "type": "holiday-theme",
                   "status": yes_status, "theme": theme, "step": "ceo-yes"})
    return {"themes": [{"id": theme, "name": "T", "status": "scheduled", "avatar_set": avatar_set,
                        "switch_on": window[0], "switch_off": window[1]}], "events": ev}


class YesGate(unittest.TestCase):
    """Ryno, 9:56 PM ET: "Yes, holiday looks wait for my yes before switching on"."""
    day = date(2028, 10, 20)

    def test_in_window_without_a_yes_is_the_blob(self):
        self.assertEqual(avatars.season_for(self.day, _cal()), "normal")

    def test_planned_yes_is_not_a_yes(self):
        self.assertEqual(avatars.season_for(self.day, _cal("planned")), "normal")

    def test_in_window_with_a_yes_is_the_holiday_set(self):
        self.assertEqual(avatars.season_for(self.day, _cal("done")), "halloween")
        self.assertEqual(avatars.season_for(date(2028, 10, 1), _cal("done")), "halloween")
        self.assertEqual(avatars.season_for(date(2028, 10, 31), _cal("done")), "halloween")

    def test_a_yes_does_not_reach_outside_the_window(self):
        for d in (date(2028, 9, 30), date(2028, 11, 1), date(2029, 10, 20)):
            self.assertEqual(avatars.season_for(d, _cal("done")), "normal", d)

    def test_a_yes_for_one_theme_does_not_switch_another(self):
        self.assertEqual(avatars.season_for(date(2028, 12, 10), _cal("done")), "normal")
        other = _cal("done", theme="winter-2028", window=("2028-12-01", "2028-12-31"), avatar_set="winter")
        self.assertEqual(avatars.season_for(self.day, other), "normal")

    def test_the_real_calendar(self):
        """Halloween 2026 has Ryno's 9:30 PM yes. Other themes follow their own ceo-yes event (winter 2026's is due Nov 24)."""
        cal = avatars.load_calendar()
        self.assertTrue(avatars.cal_mod.yes_done(cal, "halloween-2026"))
        self.assertEqual(avatars.season_for(date(2026, 10, 20)), "halloween")
        for theme, d, s in (("winter-2026", date(2026, 12, 10), "winter"), ("halloween-2027", date(2027, 10, 5), "halloween")):
            self.assertEqual(avatars.season_for(d), s if avatars.cal_mod.yes_done(cal, theme) else "normal", theme)


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
                for t in re.findall(r"animation:\w+ ([\d.]+)s", s) + re.findall(r"animation:([\d.]+)s", s):  # named, and the shared timing
                    self.assertGreaterEqual(float(t), .9, f)
                if not f.startswith("still/") and re.search(r'aria-label="[^"]+, (Halloween|winter holidays)"', s):
                    self.assertRegex(s, r"animation:[\d.]+s", f)  # the shared timing is seen by this test

    def test_slim_markup_is_the_same_drawing(self):
        # Page budget (Ryno, Oct 20 7:27 AM ET): round caps and joins once on the root, the eye colour once on the eye group,
        # one shared timing for the four loops. Stills keep the root attributes, so they draw the same.
        for season in ("halloween", "winter"):
            for f, s in avatars.files(season).items():
                if not re.search(r'aria-label="[^"]+, (Halloween|winter holidays)"', s):
                    continue
                self.assertRegex(s, r'^<svg [^>]*stroke-linecap="round" stroke-linejoin="round"', f)
                self.assertNotIn('stroke-linecap="round"', s.split(">", 1)[1], f)
                self.assertNotIn('stroke-linejoin="round"', s.split(">", 1)[1], f)
                self.assertIn(f'<g class="g" fill="{avatars.EYE}">', s, f)
                if not f.startswith("still/"):
                    for k in "sqge":
                        self.assertIn(f"animation-name:{k}", s, f)
        cane = [s for s in avatars.files("winter").values() if "stroke-dasharray" in s]
        self.assertTrue(cane and all('stroke-linecap="butt" stroke-linejoin="miter"' in s for s in cane))  # dashes stay square

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
