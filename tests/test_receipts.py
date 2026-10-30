"""Trial's tests for build receipts on Timeline and item pages (Polish UX depth, UI/UX queue item c)."""
import json, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build, check  # noqa: E402

FILES = build.build()
UPS = json.loads((ROOT / "data/updates.json").read_text())
ISS = json.loads((ROOT / "data/issues.json").read_text())


class Receipts(unittest.TestCase):
    def test_item_pages_carry_a_record_only_receipt(self):
        for x, issue in [(u, False) for u in UPS[:5]] + [(i, True) for i in ISS]:
            doc = FILES[build.item_slug(x, issue) + "index.html"]
            with self.subTest(x["id"]):
                self.assertIn('class="receipt"', doc)
                self.assertIn("<dt>Problem</dt>", doc)
                self.assertIn("<dt>Result</dt>", doc)
                self.assertIn("<dt>Limits</dt>", doc)
                self.assertIn("<dt>Source</dt>", doc)
                self.assertIn("<dt>Review</dt>", doc)
                self.assertIn(build.e(x["title"]), doc[doc.index("receipt"):])
                self.assertIn(x["status"].capitalize(), doc[doc.index("receipt"):])
                self.assertNotIn("useful in practice", doc.lower())

    def test_timeline_items_carry_a_receipt(self):
        doc = FILES["timeline/index.html"]
        n = doc.count('class="receipt"')
        items = doc.count('class="tl-item')
        self.assertGreater(n, 0)
        self.assertEqual(n, items)
        self.assertIn("From the records when this page was built", doc)
        self.assertNotIn("<script", doc)

    def test_receipt_helper_escapes_and_skips_empty_review(self):
        html = build.receipt("A & B", "ok", "limits", "<a href=\"x\">src</a>")
        self.assertIn("A & B", html)  # caller escapes; helper does not double-escape
        self.assertNotIn("<dt>Review</dt>", html)
        html2 = build.receipt("p", "r", "l", "s", review="Lens")
        self.assertIn("<dt>Review</dt><dd>Lens</dd>", html2)

    def test_page_budgets_hold(self):
        budget = json.loads((ROOT / "scripts/patterns.json").read_text())["max_page_bytes"]
        for slug in ("timeline/index.html", build.item_slug(UPS[0]) + "index.html"):
            doc = FILES[slug]
            css = check.css_weight(check.page_css(slug, doc, ROOT / "site"), ROOT / "site")
            self.assertLess(len(doc.encode()) + css, budget, slug)
