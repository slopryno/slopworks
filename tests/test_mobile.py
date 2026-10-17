"""Mobile first (i36): every page works at 360px wide, measured in a real browser, and the CSS stays min-width first.

The browser check runs headless Chrome through scripts/mobile_audit.py (Chrome ships on GitHub's ubuntu-latest runner,
and the run takes a few seconds). Off CI, a box without Chrome skips it; on CI, a missing Chrome is a failure, not a skip.
"""
import os, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import mobile_audit  # noqa: E402

CSS = (ROOT / "site" / "style.css").read_text()


class MinWidthFirst(unittest.TestCase):
    def test_width_queries_are_min_width_only(self):
        queries = re.findall(r"@media[^{]*", CSS)
        width = [q for q in queries if "width" in q]
        self.assertTrue(width, "expected at least one min-width step")
        bad = [q for q in width if re.search(r"max-width|width\s*<", q)]
        self.assertEqual(bad, [], "base styles are for phones; widen with min-width queries only")

    def test_fluid_type_uses_clamp(self):
        for sel in ("h1{", "h2{", "main.home>h1{"):
            rule = re.search(r"(?:^|\})" + re.escape(sel) + r"[^}]*", CSS, re.M)
            self.assertIsNotNone(rule, sel)
            self.assertIn("clamp(", rule.group(0), sel)

    def test_no_fixed_widths_wider_than_a_phone(self):
        # A fixed width over 360px forces sideways scrolling on a phone; max-width is fine.
        for m in re.finditer(r"(?<![-\w(])(?:min-)?width:\s*(\d+(?:\.\d+)?)(px|rem|em)", CSS):
            px = float(m.group(1)) * (1 if m.group(2) == "px" else 16)
            self.assertLessEqual(px, 360, m.group(0))


@unittest.skipUnless(mobile_audit.chrome() or os.environ.get("CI"), "headless Chrome not installed (required on CI)")
class At360(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not mobile_audit.chrome():
            raise AssertionError("CI needs headless Chrome for the 360px check")
        cls.rows = mobile_audit.measure([360])

    def test_every_page_was_measured(self):
        self.assertEqual(len(self.rows), len(mobile_audit.pages()))
        self.assertEqual([r["page"] for r in self.rows if r.get("error")], [])

    def test_no_horizontal_overflow(self):
        self.assertEqual({r["page"]: r["overflow_px"] for r in self.rows if r["overflow_px"]}, {})

    def test_tap_targets_at_least_44px(self):
        # Links inside a sentence or paragraph are exempt, as in WCAG 2.5.5 (Inline).
        self.assertEqual({r["page"]: r["small_examples"][:3] for r in self.rows if r["small_targets"]}, {})


if __name__ == "__main__":
    unittest.main()
