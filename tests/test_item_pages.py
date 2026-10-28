"""Tracker item pages (#149 §2.1): one page per update and issue, linked from the lists, the feeds and the sitemap."""
import json, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build  # noqa: E402

FILES = build.build()
UPS = json.loads((ROOT / "data/updates.json").read_text())
ISS = json.loads((ROOT / "data/issues.json").read_text())
ITEMS = [(x, False) for x in UPS] + [(x, True) for x in ISS]


class ItemPages(unittest.TestCase):
    def test_every_record_has_a_page_at_its_id(self):
        for x, issue in ITEMS:
            self.assertIn(f'{"issues" if issue else "updates"}/{x["id"]}/index.html', FILES)

    def test_page_shows_the_record_and_its_source(self):
        for x, issue in ITEMS:
            doc = FILES[build.item_slug(x, issue) + "index.html"]
            with self.subTest(x["id"]):
                self.assertIn(f"<title>{build.e(x['title'])} · Slopworks</title>", doc)
                self.assertIn(build.e(x["summary"]), doc)
                self.assertIn(f'itemprop="isBasedOn" href="{build.e(x["source"])}"', doc)
                self.assertIn(f'<meta itemprop="datePublished" content="{x["date"]}">', doc)
                self.assertIn('itemtype="https://schema.org/Article"', doc)
                self.assertIn("Back to " + ("Known issues" if issue else "What's new"), doc)
                self.assertNotIn("<script", doc)

    def test_h1_fits_the_page_title_limit(self):
        limit = json.loads((ROOT / "data/word_limits.json").read_text())["areas"]["page_title"]["limit"]
        for x, issue in ITEMS:
            h1 = re.search(r"<h1>(.*?)</h1>", FILES[build.item_slug(x, issue) + "index.html"]).group(1)
            self.assertLessEqual(len(h1.split()), limit, x["id"])
            self.assertEqual(h1, build.e(x.get("short_title") or x["title"]))

    def test_related_items_share_the_area(self):
        by_id = {x["id"]: x for x, _ in ITEMS}
        for x, issue in ITEMS:
            doc = FILES[build.item_slug(x, issue) + "index.html"]
            more = re.search(r"<h2>More in [^<]+</h2><ul>(.*?)</ul>", doc)
            for rid in re.findall(r'<li><a href="\.\./([^/"]+)/">', more.group(1) if more else ""):
                self.assertEqual(by_id[rid]["area"], x["area"], (x["id"], rid))
                self.assertNotEqual(rid, x["id"])

    def test_lists_link_each_page_and_keep_the_old_anchors(self):
        for x, issue in ITEMS:
            doc = FILES[("issues" if issue else "updates") + "/index.html"]
            self.assertIn(f'id="e{x["id"]}"', doc)
            self.assertIn(f'<a href="{x["id"]}/" aria-label="Details on {build.e(x["title"])}">details</a>', doc)

    def test_description_is_escaped_once(self):
        x = dict(UPS[0], summary='A "quoted" word & more')
        build.DESCRIPTIONS["updates/t/"] = build.describe(None, x["summary"])
        doc = build.page("updates/t/", "T", "L", "", "data/updates.json")
        self.assertIn('content="A &quot;quoted&quot; word &amp; more"', doc)

    def test_feeds_link_item_pages_with_unchanged_guids(self):
        feed = json.loads(FILES["feed.json"])
        for it in feed["items"]:
            kind, _, rid = it["id"].partition("-")
            self.assertEqual(it["url"], f'{build.BASE}{"issues" if kind == "issue" else "updates"}/{rid}/')
        self.assertIn('<guid isPermaLink="false">update-', FILES["feed.xml"])

    def test_sitemap_lastmod_only_from_record_dates(self):
        sm = FILES["sitemap.xml"]
        for x, issue in ITEMS:
            self.assertIn(f"<loc>{build.BASE}{build.item_slug(x, issue)}</loc><lastmod>{build.item_modified(x, issue)}</lastmod>", sm)
        self.assertIn(f"<loc>{build.BASE}team/</loc></url>", sm)  # no record date, so no lastmod


if __name__ == "__main__":
    unittest.main()
