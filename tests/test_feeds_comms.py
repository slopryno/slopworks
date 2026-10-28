"""Trial's tests for the feed check (i26) and Comms' page checks (i28): sitemap coverage, title and description, banned hype."""
import json, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check, build  # noqa: E402

FILES = build.build()


class Feeds(unittest.TestCase):
    def test_real_feeds_pass(self):
        for f in ("feed.xml", "chat.xml", "feed.json", "chat.json"):
            self.assertEqual(check.feed_errors(f, FILES[f]), [], f)

    def test_broken_feeds_fail(self):
        self.assertTrue(check.feed_errors("feed.xml", FILES["feed.xml"].replace("</channel>", "")))
        self.assertTrue(check.feed_errors("feed.xml", FILES["feed.xml"].replace("<guid", "<x", 1).replace("</guid>", "</x>", 1)))
        self.assertTrue(check.feed_errors("feed.xml", '<rss version="0.91"><channel><title>t</title></channel></rss>'))
        f = json.loads(FILES["feed.json"])
        f["items"].append(dict(f["items"][0]))
        self.assertTrue(check.feed_errors("feed.json", json.dumps(f)))
        self.assertTrue(check.feed_errors("chat.json", json.dumps({"version": "https://jsonfeed.org/version/1", "title": "t", "items": []})))
        self.assertTrue(check.feed_errors("chat.json", "{not json"))


class CommsPages(unittest.TestCase):
    def test_every_page_has_title_and_description(self):
        for k, v in FILES.items():
            if k.endswith(".html"):
                self.assertEqual(check.page_meta_errors(k, v), [], k)
        self.assertTrue(check.page_meta_errors("x", "<title></title>"))

    def test_sitemap_covers_every_page(self):
        self.assertEqual(check.sitemap_errors(check.tracked_files()), [])
        tmp = Path(tempfile.mkdtemp()); (tmp / "site").mkdir()
        (tmp / "site/sitemap.xml").write_text("<urlset><url><loc>https://slopryno.com/</loc></url></urlset>")
        errs = check.sitemap_errors(["site/index.html", "site/team/index.html"], tmp)
        self.assertEqual(len(errs), 1); self.assertIn("team/", errs[0])

    def test_hype_only_clear_cases(self):
        self.assertEqual(check.hype_hits("<p>Grok Bot is much faster, with better voice calls.</p>"), [])
        self.assertEqual(check.hype_hits("<p>Merged in PR #1 and issue #12.</p>"), [])
        self.assertEqual(check.hype_hits("<p>The post said \u201cgame-changing\u201d, quoted as written.</p>"), [])
        self.assertEqual(check.hype_hits("<p>A revolutionary, world-class tracker. We're #1.</p>"), ["#1", "revolutionary", "world-class"])
        for k, v in FILES.items():
            if k.endswith(".html"):
                self.assertEqual(check.hype_hits(v), [], k)

    def test_wordlist_matches_style_guide(self):
        guide = (ROOT / "docs/style-guide.md").read_text()
        for w in ("revolutionary", "world-class", "guaranteed", "10x", "groundbreaking"):
            self.assertIn(w, guide)


if __name__ == "__main__":
    unittest.main()
