"""Slopworks logo and favicon, option A Blob Badge (Ryno, 2026-10-20 9:06 PM ET: Polish owns branding; shipped Oct 21 in a regular slot)."""
import re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build  # noqa: E402

FAV = ROOT / "site/assets/favicon.svg"


class Brand(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pages = build.build()

    def test_every_page_has_one_icon_link_to_the_favicon(self):
        self.assertTrue(FAV.exists())
        for name, doc in self.pages.items():
            if not name.endswith(".html"):
                continue
            icons = re.findall(r'<link rel="icon" href="([^"]*)"', doc)
            self.assertEqual(len(icons), 1, name)
            self.assertEqual((ROOT / "site" / Path(name).parent / icons[0]).resolve(), FAV.resolve(), name)

    def test_favicon_is_small_plain_svg(self):
        svg = FAV.read_text()
        self.assertLessEqual(len(FAV.read_bytes()), 1024)
        self.assertIn("viewBox=", svg)
        for bad in ("<script", "href=", "@import", "url(", "<text", "font", "<image", "<foreignObject"):
            self.assertNotIn(bad, svg, bad)

    def test_header_mark_is_decorative_and_name_stays(self):
        for name, doc in self.pages.items():
            if not name.endswith(".html"):
                continue
            m = re.search(r'<a class="brand"[^>]*>(.*?)</a>', doc)
            self.assertIsNotNone(m, name)
            self.assertRegex(m.group(1), r'^<img src="[^"]*favicon\.svg" alt="" width="28" height="28">Slopworks$', name)

    def test_mark_never_on_the_team_grid(self):
        team = self.pages["team/index.html"]
        main = team.split("</header>", 1)[1]
        self.assertNotIn("favicon.svg", main)


if __name__ == "__main__":
    unittest.main()
