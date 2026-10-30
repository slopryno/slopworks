"""d2: every page carries a large social preview image."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


class SocialPreview(unittest.TestCase):
    def test_og_asset_exists_and_is_small(self):
        p = SITE / "assets" / "og.png"
        self.assertTrue(p.is_file())
        self.assertLessEqual(p.stat().st_size, 5 * 1024 * 1024)
        self.assertLessEqual(p.stat().st_size, 100_000)  # keep the repo lean

    def test_home_has_large_card_meta(self):
        html = (SITE / "index.html").read_text()
        self.assertIn('property="og:image"', html)
        self.assertIn("assets/og.png", html)
        self.assertIn('content="summary_large_image"', html)
        self.assertIn('name="twitter:image"', html)
        self.assertNotIn('content="summary"', html.split("twitter:card")[1][:80])
