"""Trial's tests for the stdlib golden helper: UPDATE=1 rewrites, otherwise a readable unified diff."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import golden  # noqa: E402


class Helper(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self._update = os.environ.pop(golden.UPDATE_ENV, None)
        self.addCleanup(self._restore_env)

    def _restore_env(self):
        if self._update is None:
            os.environ.pop(golden.UPDATE_ENV, None)
        else:
            os.environ[golden.UPDATE_ENV] = self._update

    def test_mismatch_fails_with_a_unified_diff(self):
        (self.root / "wired.css").write_text(".ok{color:blue}\n")
        with self.assertRaises(AssertionError) as ctx:
            golden.assert_matches(self, "wired.css", ".ok{color:red}\n", root=self.root)
        msg = str(ctx.exception)
        self.assertIn("golden wired.css differs", msg)
        self.assertIn("UPDATE=1", msg)
        self.assertIn("Read this diff before accepting", msg)
        self.assertIn("--- goldens/wired.css", msg)
        self.assertIn("+++ actual", msg)
        self.assertIn("-.ok{color:blue}", msg)
        self.assertIn("+.ok{color:red}", msg)

    def test_match_passes(self):
        (self.root / "ok.txt").write_text("same\n")
        golden.assert_matches(self, "ok.txt", "same\n", root=self.root)

    def test_update_rewrites_after_you_opt_in(self):
        path = self.root / "card.html"
        path.write_text("old\n")
        os.environ[golden.UPDATE_ENV] = "1"
        golden.assert_matches(self, "card.html", "new\n", root=self.root)
        self.assertEqual(path.read_text(), "new\n")

    def test_update_is_only_the_digit_one(self):
        (self.root / "x.txt").write_text("keep\n")
        os.environ[golden.UPDATE_ENV] = "yes"
        with self.assertRaises(AssertionError):
            golden.assert_matches(self, "x.txt", "no\n", root=self.root)
        self.assertEqual((self.root / "x.txt").read_text(), "keep\n")

    def test_missing_golden_tells_you_to_opt_in(self):
        with self.assertRaises(AssertionError) as ctx:
            golden.assert_matches(self, "missing.html", "<p>hi</p>\n", root=self.root)
        self.assertIn("missing golden", str(ctx.exception))
        self.assertIn("UPDATE=1", str(ctx.exception))
        self.assertFalse((self.root / "missing.html").exists())


class Normalize(unittest.TestCase):
    def test_record_bits_are_stripped_and_wiring_stays(self):
        a = (
            '<li class="slot t3 r4 holo" id="card-forge">'
            '<p class="lv"><span class="ml" title="Engineering">Lv <span>9</span></span> · Grandmaster</p>'
            '<div class="bar" aria-hidden="true"><span style="width:6%"></span></div>'
            '<p class="rar">Holo rare · 10/19</p>'
            '<em>115<small> PRs</small></em>'
            '<li><b>XP</b><em>3365</em></li>'
            '<li class="lvf">Last verified · <a href="https://github.com/slopryno/slopworks/pull/204">#204</a></li>'
            '<ol class="recent"><li><a href="forge/">Forge</a><a href="https://github.com/slopryno/slopworks/pull/204">PR #204</a></li></ol>'
        )
        b = (
            '<li class="slot t3 r1" id="card-forge">'
            '<p class="lv"><span class="ml" title="Engineering">Lv <span>1</span></span> · Recruit</p>'
            '<div class="bar" aria-hidden="true"><span style="width:90%"></span></div>'
            '<p class="rar">Common · 10/19</p>'
            '<em>1<small> PR</small></em>'
            '<li><b>XP</b><em>5</em></li>'
            '<li class="lvf">Last verified · <a href="https://github.com/slopryno/slopworks/pull/1">#1</a></li>'
            '<ol class="recent"><li><a href="sweep/">Sweep</a><a href="https://github.com/slopryno/slopworks/pull/185">PR #185</a></li></ol>'
        )
        self.assertEqual(golden.normalize_team(a), golden.normalize_team(b))
        self.assertIn('id="card-forge"', golden.normalize_team(a))
        self.assertIn('class="slot t3"', golden.normalize_team(a))
        self.assertNotIn("holo", golden.normalize_team(a))
        self.assertNotIn("r4", golden.normalize_team(a))

    def test_a_real_markup_change_survives_normalize(self):
        keep = '<details class="flip"><p class="nm">Forge</p></details>'
        changed = '<details class="flip extra"><p class="nm">Forge</p></details>'
        self.assertNotEqual(golden.normalize_team(keep), golden.normalize_team(changed))


class NormalizeChrome(unittest.TestCase):
    def test_relative_prefixes_collapse_and_a_href_change_survives(self):
        team = '<nav class="tabs" aria-label="Main"><ul><li><a href="../">Home</a></li><li><a href="../updates/">Tracker</a></li></ul></nav>'
        nested = '<nav class="tabs" aria-label="Main"><ul><li><a href="../../">Home</a></li><li><a href="../../updates/">Tracker</a></li></ul></nav>'
        home = '<nav class="tabs" aria-label="Main"><ul><li><a href="">Home</a></li><li><a href="updates/">Tracker</a></li></ul></nav>'
        self.assertEqual(golden.normalize_chrome(team), home)
        self.assertEqual(golden.normalize_chrome(nested), home)
        typo = team.replace("../updates/", "../reciepts/")
        self.assertNotEqual(golden.normalize_chrome(typo), golden.normalize_chrome(team))

    def test_nav_tabs_and_sitelist_extract_or_raise(self):
        html = (
            '<header><nav class="tabs" aria-label="Main"><ul><li><a href="">Home</a></li></ul></nav></header>'
            '<footer><nav class="sitelist" aria-label="Sections"><ul><li><a href="">Home</a></li></ul></nav></footer>'
        )
        self.assertIn('aria-label="Main"', golden.nav_tabs(html))
        self.assertIn('aria-label="Sections"', golden.footer_sitelist(html))
        with self.assertRaises(ValueError):
            golden.nav_tabs("<main></main>")
        with self.assertRaises(ValueError):
            golden.footer_sitelist("<main></main>")
        self.assertEqual(golden.tabs_golden_name(""), "tabs-home.html")
        self.assertEqual(golden.tabs_golden_name("team/"), "tabs-team.html")


class NormalizeMetrics(unittest.TestCase):
    def test_record_churn_is_stripped_and_structure_stays(self):
        a = (
            '<table class="trend"><caption>plus the 19-day series under each row</caption>'
            '<thead><tr><th scope="col">Metric</th><th scope="col">Mon Nov\u00a016</th>'
            '<th scope="col">Tue Nov\u00a017 (so far)</th><th scope="col">Direction</th></tr></thead>'
            '<tbody><tr><th scope="row">Merged PRs</th><td>0</td><td>2</td><td>↑ up</td></tr>'
            '<tr><td colspan="4"><span class="spark"><svg viewBox="0 0 96 20" role="img" '
            'aria-label="Merged PRs, 19 days"><polyline points="1,18 6,13"/><polyline points="95,18"/>'
            '</svg><span class="spark-val">2 (0–60)</span></span></td></tr></tbody></table>'
        )
        b = (
            '<table class="trend"><caption>plus the 21-day series under each row</caption>'
            '<thead><tr><th scope="col">Metric</th><th scope="col">Wed Nov\u00a018</th>'
            '<th scope="col">Thu Nov\u00a019 (so far)</th><th scope="col">Direction</th></tr></thead>'
            '<tbody><tr><th scope="row">Merged PRs</th><td>7</td><td>1</td><td>↓ down</td></tr>'
            '<tr><td colspan="4"><span class="spark"><svg viewBox="0 0 96 20" role="img" '
            'aria-label="Merged PRs, 21 days"><polyline points="1,18 6,13 10,1 95,19"/>'
            '</svg><span class="spark-val">1 (0–60)</span></span></td></tr></tbody></table>'
        )
        self.assertEqual(golden.normalize_metrics_charts(a), golden.normalize_metrics_charts(b))
        got = golden.normalize_metrics_charts(a)
        self.assertIn('scope="row">Merged PRs</th>', got)
        self.assertIn('class="spark-val">VAL</span>', got)
        self.assertIn('viewBox="0 0 96 20"', got)
        self.assertIn('role="img"', got)
        self.assertIn('<polyline points="PTS"/>', got)
        self.assertIn("<td>DIR</td>", got)
        self.assertIn("N-day series", got)
        self.assertIn("LATEST (so far)", got)
        self.assertNotIn("↑", got)
        self.assertNotIn("19 days", got)

    def test_a_real_markup_change_survives_normalize(self):
        keep = (
            '<span class="spark"><svg viewBox="0 0 96 20" role="img" aria-label="Merged PRs, 21 days">'
            '<polyline points="1,18"/></svg><span class="spark-val">1</span></span>'
        )
        dropped = '<td colspan="4"></td>'
        typo = keep.replace("Merged PRs", "Merged PR")
        tall = keep.replace('viewBox="0 0 96 20"', 'viewBox="0 0 96 40"')
        color_only = keep.replace('<span class="spark-val">1</span>', "")
        self.assertNotEqual(golden.normalize_metrics_charts(keep), golden.normalize_metrics_charts(dropped))
        self.assertNotEqual(golden.normalize_metrics_charts(keep), golden.normalize_metrics_charts(typo))
        self.assertNotEqual(golden.normalize_metrics_charts(keep), golden.normalize_metrics_charts(tall))
        self.assertNotEqual(golden.normalize_metrics_charts(keep), golden.normalize_metrics_charts(color_only))



if __name__ == "__main__":
    unittest.main()
