"""Mobile backlog d7–d11: first-screen trim, inline objective links, one-shot hop, XP togo text, XP table stack."""
import re, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS = (ROOT / "site" / "style.css").read_text()
HOME = (ROOT / "scripts" / "home.py").read_text()
CARDS = (ROOT / "scripts" / "cards.py").read_text()
BUILD = (ROOT / "scripts" / "build.py").read_text()


class MobileBacklog(unittest.TestCase):
    def test_d8_objective_links_are_inline_and_underlined(self):
        self.assertIn(".obj a{display:inline;text-decoration:underline", CSS)
        self.assertNotIn(".obj a,.recap a{display:inline-flex", CSS)
        self.assertNotRegex(CSS, r"\.obj a,.*text-decoration:none")

    def test_d9_avatar_hop_runs_once(self):
        self.assertIn("animation:hop .9s ease-in-out 1}", CSS)
        self.assertNotIn("animation:hop .9s ease-in-out infinite}", CSS)

    def test_d10_xp_bars_name_what_they_fill_toward(self):
        self.assertIn("xp-togo", HOME)
        self.assertIn("XP to", HOME)
        # Trading cards stay uncluttered (test_cards_v6); sheets already show togo.
        self.assertIn(".xp-togo{", CSS)

    def test_d11_xp_table_stacks_and_roster_stays_inline(self):
        self.assertIn('table class="stack"><thead><tr><th scope="col">Work</th>', BUILD)
        self.assertIn('ul class="roster"', BUILD)
        self.assertIn(".roster a{display:inline;min-height:0;min-width:0}", CSS)

    def test_d7_cases_outcome_lives_inside_details(self):
        i = BUILD.find("def case_card")
        block = BUILD[i:i + 900]
        self.assertLess(block.find("<details>"), block.find("Outcome:"))
        self.assertIn("Real decisions, from the problem to what shipped", BUILD)
        self.assertIn("Same-day, blameless after-action reviews. Every line links its record.", BUILD)


if __name__ == "__main__":
    unittest.main()
