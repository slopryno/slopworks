"""Trial's tests for permanent weekly pages (d3 / level-up 2.5)."""
import re
import unittest
from datetime import date
from pathlib import Path

import scripts.build as build
import scripts.weekly as weekly

ROOT = Path(__file__).resolve().parents[1]


class WeeklyPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = build.build()
        cls.week_pages = sorted(
            p for p in cls.files if re.fullmatch(r"weekly/20\d{2}-w\d{2}/index.html", p)
        )

    def test_week_key_is_iso_of_start(self):
        self.assertEqual(weekly.week_key(date(2026, 10, 15)), "2026-w42")
        self.assertEqual(weekly.week_key(date(2026, 10, 22)), "2026-w43")

    def test_each_week_has_a_permanent_page(self):
        self.assertGreaterEqual(len(self.week_pages), 1)
        for p in self.week_pages:
            doc = self.files[p]
            self.assertIn("This week in Grok Bot", doc)
            self.assertIn('class="panel week"', doc)
            self.assertIn("All weeks", doc)
            slug = p.replace("index.html", "")
            self.assertIn(f'content="https://slopryno.com/{slug}"', doc)

    def test_index_links_to_permanent_pages(self):
        index = self.files["weekly/index.html"]
        for p in self.week_pages:
            key = p.split("/")[1]
            self.assertIn(f'href="{key}/"', index)

    def test_index_still_counts_every_merged_pr(self):
        """i42: index panels still list every week so day/PR counts stay checkable there."""
        import json
        page = self.files["weekly/index.html"]
        wins = json.loads((ROOT / "data/wins.json").read_text())
        total = sum(int(x) for x in re.findall(r"<li><strong>(\d+)</strong> merged PRs</li>", page))
        self.assertEqual(total, len(wins))
