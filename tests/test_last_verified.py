"""(f) Last verified line on agent cards (home + trading cards)."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
WINS = {w["role"] for w in json.loads((ROOT / "data/wins.json").read_text())}


class LastVerified(unittest.TestCase):
    def test_home_chars_label_last_verified(self):
        html = (SITE / "index.html").read_text()
        self.assertRegex(html, r'class="last"><span class="kicker">Last verified</span>')

    def test_team_trading_cards_show_last_verified(self):
        html = (SITE / "team" / "index.html").read_text()
        self.assertIn("Last verified", html)
        self.assertGreaterEqual(html.count('class="lvf"'), min(10, len(WINS)))
        self.assertTrue(re.search(r'class="lvf">Last verified · <a href="[^"]+/pull/\d+"', html))
