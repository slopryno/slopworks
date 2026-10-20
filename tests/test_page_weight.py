"""Images count toward the page budget (Ryno, 2026-10-20 7:27 AM ET)."""
import inspect
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check  # noqa: E402
import mobile_audit  # noqa: E402


class PageImages(unittest.TestCase):
    def test_resolves_relative_dedupes_and_includes_stills(self):
        doc = ('<img src="../assets/avatars/lens.svg"><img src="../assets/avatars/lens.svg">'
               '<img src="../assets/avatars/still/lens.svg"><link rel="icon" href="../favicon.svg">')
        self.assertEqual(check.page_images("team/index.html", doc),
                         {"assets/avatars/lens.svg", "assets/avatars/still/lens.svg", "favicon.svg"})

    def test_skips_external_and_data(self):
        doc = '<img src="https://example.com/a.png"><img src="//cdn.example.com/b.svg"><img src="data:image/png;base64,AA">'
        self.assertEqual(check.page_images("index.html", doc), set())

    def test_srcset_counts(self):
        doc = '<img src="a.png" srcset="a.png 1x, b.png 2x">'
        self.assertEqual(check.page_images("x/index.html", doc), {"x/a.png", "x/b.png"})


class Budget(unittest.TestCase):
    def site(self, files):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for rel, body in files.items():
            (root / "site" / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / "site" / rel).write_text(body)
        return root

    def test_images_push_a_page_over(self):
        page = '<img src="../a/b.svg"><img src="../a/b.svg">'
        root = self.site({"style.css": "x" * 100, "p/index.html": page, "a/b.svg": "y" * 600})
        total, missing = check.page_weight("p/index.html", page, 100, root)
        self.assertEqual((total, missing), (len(page) + 100 + 600, []))  # the repeated image counts once
        self.assertTrue(any("over" in e for e in check.page_weight_errors(root, limit=700)))
        self.assertEqual(check.page_weight_errors(root, limit=1024), [])

    def test_missing_image_is_flagged(self):
        root = self.site({"style.css": "", "index.html": '<img src="gone.svg">'})
        self.assertIn("site/index.html: loads missing image gone.svg", check.page_weight_errors(root))

    def test_css_url_images_count(self):
        root = self.site({"style.css": "body{background:url(bg.png)}", "index.html": "<p>hi</p>", "bg.png": "z" * 2000})
        self.assertTrue(check.page_weight_errors(root, limit=1500))

    def test_live_site_is_within_budget(self):
        self.assertEqual(check.page_weight_errors(), [])

    def test_ci_runs_it_and_records_the_ask(self):
        self.assertIn("page_weight_errors()", inspect.getsource(check.run_repo))
        self.assertIn('"Yes, count avatar images in the page budget', inspect.getsource(check))

    def test_audit_uses_the_same_rule(self):
        team = (ROOT / "site/team/index.html").read_text()
        css = sum(p.stat().st_size for p in (ROOT / "site").glob("*.css"))
        self.assertEqual(mobile_audit.static_numbers()["pages"]["team/index.html"]["page_bytes"],
                         check.page_weight("team/index.html", team, css)[0])


if __name__ == "__main__":
    unittest.main()
