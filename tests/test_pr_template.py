"""Trial: the pull request template yields a body that passes the Maker check once filled in."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import bot  # noqa: E402
import check  # noqa: E402

TEMPLATE = ROOT / ".github" / "pull_request_template.md"


class PrTemplate(unittest.TestCase):
    def test_template_exists_and_names_maker_placeholder(self):
        text = TEMPLATE.read_text()
        self.assertRegex(text, r"(?m)^Maker:\s*")
        # Comment lists the same known set bot.py accepts (spot-check Core, which tripped local edits before).
        self.assertIn("Core", text)
        self.assertIn("Forge", text)
        self.assertIn("Gamemaster", text)

    def test_filled_template_passes_maker_gate(self):
        filled = TEMPLATE.read_text().replace(
            "Maker: <!-- role name, e.g. Forge -->", "Maker: Forge", 1
        )
        # No paths -> no required reviewers; gate only checks the Maker line parses.
        self.assertEqual(check.review_gate([], filled, []), [])
        self.assertTrue(
            check.review_gate([], "no maker here", []),
        )
        self.assertIn("must name its maker", check.review_gate([], "no maker here", [])[0])
        self.assertEqual(bot.role("Forge"), "Forge")
        self.assertEqual(bot.role("Core"), "Core")

    def test_known_makers_match_bot_py(self):
        known = {f.stem.capitalize() for f in (ROOT / "bots").glob("*.md")} | bot.SPECIALISTS
        for name in ("Core", "Forge", "Lens", "Assistant", "Pixel", "Vault", "Relay"):
            self.assertIn(name, known)
            self.assertEqual(bot.role(name), name)


if __name__ == "__main__":
    unittest.main()
