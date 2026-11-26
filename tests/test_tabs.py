"""Trial's tab-bar chrome goldens and static clearance tests.

Goldens lock the five-tab nav and footer sitelist (href prefixes stripped so
Home, Team, and nested pages share one snapshot) and the shared tabs.css.
Clearance checks are assertions, not goldens: the fixed bar must pad the iOS
safe area, and jump links must have scroll-padding equal to the bar height.
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import build  # noqa: E402
import golden  # noqa: E402

TABS_CSS = ROOT / "site/tabs.css"
PHONE_CLEARANCE = "calc(4.5rem + env(safe-area-inset-bottom,0px))"
NESTED = "team/ryno/"


def sample(slug):
    return build.page(slug, "Title", "A short lede.", "<p>Body.</p>", "scripts/build.py")


class ChromeGoldens(unittest.TestCase):
    def test_tabs_css_matches_golden(self):
        golden.assert_matches(self, "tabs.css", TABS_CSS.read_text())

    def test_normalized_tab_bar_matches_golden_on_each_hub(self):
        for slug, _title in build.TABS:
            html = sample(slug)
            golden.assert_matches(
                self,
                golden.tabs_golden_name(slug),
                golden.normalize_chrome(golden.nav_tabs(html)),
            )

    def test_normalized_footer_sitelist_matches_golden_on_home_team_and_a_nested_page(self):
        want = None
        for slug in ("", "team/", NESTED):
            got = golden.normalize_chrome(golden.footer_sitelist(sample(slug)))
            golden.assert_matches(self, "footer-sitelist.html", got)
            if want is None:
                want = got
            else:
                self.assertEqual(got, want)

    def test_a_dropped_tab_fails_with_a_clear_diff(self):
        nav = golden.nav_tabs(sample("team/"))
        broken = re.sub(r'<li><a href="(?:\.\./)*more/">More</a></li>', "", nav)
        self.assertNotEqual(broken, nav)
        with self.assertRaises(self.failureException) as ctx:
            golden.assert_matches(self, "tabs-team.html", golden.normalize_chrome(broken))
        msg = str(ctx.exception)
        self.assertIn("golden tabs-team.html differs", msg)
        self.assertIn("More", msg)


class TabBarClearance(unittest.TestCase):
    """Static checks of site/tabs.css. These stay assertions, not goldens."""

    @classmethod
    def setUpClass(cls):
        cls.css = TABS_CSS.read_text()

    def test_body_padding_clears_the_bar_and_the_safe_area(self):
        self.assertIn(f"body{{padding-bottom:{PHONE_CLEARANCE}}}", self.css)

    def test_tab_bar_pads_the_safe_area_inset(self):
        m = re.search(r"\.tabs\{[^}]*\}", self.css)
        self.assertIsNotNone(m, "site/tabs.css is missing a .tabs rule")
        self.assertIn("env(safe-area-inset-bottom,0px)", m.group(0))
        self.assertIn("position:fixed", m.group(0))

    def test_scroll_padding_bottom_clears_the_fixed_tab_bar_on_phones(self):
        """Jump links and focus must not land under the bar (WCAG 2.4.11)."""
        self.assertIn(f"html{{scroll-padding-bottom:{PHONE_CLEARANCE}}}", self.css)

    def test_wide_screens_drop_the_fixed_bar_and_its_clearance(self):
        m = re.search(r"@media \(min-width:40rem\)\{((?:[^{}]|\{[^{}]*\})*)\}", self.css)
        self.assertIsNotNone(m, "missing the 40rem desktop reset")
        block = m.group(1)
        self.assertIn("position:static", block)
        self.assertIn("scroll-padding-bottom:0", block)
        self.assertIn("padding-bottom:0", block)


class TabSwitchTransitions(unittest.TestCase):
    """Cross-document view transitions: content fades, the tab bar stays put, reduced motion is off."""

    @classmethod
    def setUpClass(cls):
        cls.css = TABS_CSS.read_text()

    def _motion_ok_block(self):
        m = re.search(
            r"@media\s*\(\s*prefers-reduced-motion\s*:\s*no-preference\s*\)\{((?:[^{}]|\{[^{}]*\})*)\}",
            self.css,
        )
        self.assertIsNotNone(m, "missing the no-preference view-transition block")
        return m.group(1)

    def test_view_transitions_are_opted_in_only_when_motion_is_ok(self):
        block = self._motion_ok_block()
        self.assertIn("@view-transition{navigation:auto}", block)
        # The opt-in must not leak outside that query (reduced-motion users get a normal load).
        self.assertEqual(self.css.count("@view-transition"), 1)
        self.assertEqual(self.css.count("navigation:auto"), 1)

    def test_tab_bar_stays_put_while_content_transitions(self):
        self.assertIn("view-transition-name:tabs", self.css)
        self.assertIn("::view-transition-group(tabs){animation-duration:0s}", self._motion_ok_block())

    def test_reduced_motion_query_does_not_enable_view_transitions(self):
        reduce_blocks = re.findall(
            r"@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)\{((?:[^{}]|\{[^{}]*\})*)\}",
            self.css,
        )
        for block in reduce_blocks:
            self.assertNotIn("navigation:auto", block)
            self.assertNotIn("@view-transition", block)


if __name__ == "__main__":
    unittest.main()
