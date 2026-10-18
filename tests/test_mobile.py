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


@unittest.skipUnless(mobile_audit.chrome() or os.environ.get("CI"), "headless Chrome not installed (required on CI)")
class Visual(unittest.TestCase):
    """Visual defects the metric checks missed on /work/ (AAR 2026-10-17): words broken mid-word, boxes whose content is
    wider than they are, and anything past the right edge, even when it is clipped. Checked at 320 (a 390 phone with
    large text), 360 and 390, and again at 360 in a wide fallback font, so a layout that only fits one font fails too."""
    KEYS = ("midword_breaks", "box_overflow", "past_right_edge", "narrow_text")

    @classmethod
    def setUpClass(cls):
        if not mobile_audit.chrome():
            raise AssertionError("CI needs headless Chrome for the visual checks")
        cls.rows = mobile_audit.measure([320, 360, 390]) + mobile_audit.measure([360], font='"DejaVu Sans", "Verdana", sans-serif')

    def problems(self, key):
        return {f'{r["page"]} @{r["width"]}': r[key][:3] for r in self.rows if r.get(key)}

    def test_every_page_measured_with_visual_checks(self):
        self.assertEqual([r["page"] for r in self.rows if r.get("error")], [])
        for r in self.rows:
            for k in self.KEYS:
                self.assertIn(k, r)

    def test_no_word_broken_mid_word(self):
        self.assertEqual(self.problems("midword_breaks"), {})

    def test_no_text_squeezed_into_a_narrow_column(self):
        self.assertEqual(self.problems("narrow_text"), {})

    def test_no_element_content_wider_than_its_box(self):
        self.assertEqual(self.problems("box_overflow"), {})

    def test_nothing_past_the_right_edge_even_clipped(self):
        self.assertEqual(self.problems("past_right_edge"), {})


@unittest.skipUnless(mobile_audit.chrome() or os.environ.get("CI"), "headless Chrome not installed (required on CI)")
class VisualDetectorsFire(unittest.TestCase):
    """Each visual detector catches its defect on a known-bad page, so a passing site means something."""
    BAD = """<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width"><title>t</title></head><body style="margin:0">
<main><div style="width:20px;overflow-wrap:anywhere"><strong style="display:block">Timeline</strong></div>
<div style="overflow:hidden;width:300px"><div style="width:500px">clipped wide box</div></div>
<p style="white-space:nowrap">Corrections: slopryno+corrections@mail.grokbot.com and more words after it</p></main></body></html>"""

    def test_detectors_fire_on_a_bad_page(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "bad.html"
            f.write_text(self.BAD)
            r = mobile_audit.measure([360], only=[str(f)])[0]
        self.assertTrue(any("Timeline" in x for x in r["midword_breaks"]), r["midword_breaks"])
        self.assertTrue(r["narrow_text"], "narrow column")
        self.assertTrue(any("scrollWidth 500" in x for x in r["box_overflow"]), r["box_overflow"])
        self.assertTrue(any("clipped wide box" in x for x in r["past_right_edge"]), "clipped element past the edge")
        self.assertTrue(any("Corrections" in x for x in r["past_right_edge"]), "text past the edge")


class At200PercentZoom(unittest.TestCase):
    """i43 (Polish, c305): a 390 px phone zoomed to 200% lays pages out at 195 CSS px. No page may scroll sideways there;
    a wide data table may scroll inside its own box."""
    @classmethod
    def setUpClass(cls):
        if not mobile_audit.chrome():
            raise AssertionError("CI needs headless Chrome for the zoom check")
        cls.rows = mobile_audit.measure([195])

    def test_every_page_measured(self):
        self.assertEqual([r["page"] for r in self.rows if r.get("error")], [])
        self.assertEqual(len(self.rows), len(mobile_audit.pages()))

    def test_no_page_scrolls_sideways(self):
        self.assertEqual({r["page"]: r["overflow_px"] for r in self.rows if r["overflow_px"]}, {})
        self.assertEqual({r["page"]: r["past_right_edge"][:2] for r in self.rows if r["past_right_edge"]}, {})


if __name__ == "__main__":
    unittest.main()
