"""Trial's checks for the i40 prototype page (c265): real data, no scripts, every text color pair at 4.5:1 or more."""
import json, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build, prototype  # noqa: E402


def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def ratio(a, b):
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


class Prototype(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = build.build()
        cls.doc = cls.files["prototype/index.html"]

    def test_text_pairs_pass_aa(self):
        for t in (prototype.DARK, prototype.LIGHT):
            for fg in ("fg", "muted", "done", "block", "research"):
                for bg in ("bg", "card"):
                    self.assertGreaterEqual(ratio(t[fg], t[bg]), 4.5, f"{fg} on {bg}: {t[fg]} on {t[bg]}")
            self.assertGreaterEqual(ratio(t["on-done"], t["done"]), 4.5)
            self.assertGreaterEqual(ratio(t["bg"], t["fg"]), 4.5)  # the filled Confirmed chip

    def test_static_and_labeled(self):
        self.assertNotIn("<script", self.doc)
        self.assertNotIn("<form", self.doc)
        self.assertIn('class="pill">Prototype</span>', self.doc)
        self.assertNotIn("live now", self.doc.lower())

    def test_numbers_come_from_the_repo(self):
        wins = json.loads((ROOT / "data/wins.json").read_text())
        self.assertIn(f"<strong>{len(wins)}</strong><span>merged PRs</span>", self.doc)
        last = max(w.get("merged") or w["date"] for w in wins)
        self.assertIn(f"{last[:10]} {last[11:16]} ET", self.doc)
        self.assertNotIn("current quest", self.doc.lower())  # no quest slot until quests exist (Gamemaster, c264)

    def test_live_site_untouched(self):
        for k, v in self.files.items():
            if k.endswith(".html") and k != "prototype/index.html":
                self.assertFalse(re.search(r'href="[^"]*prototype/', v), f"{k} links the prototype")

    def test_page_budget(self):
        budget = json.loads((ROOT / "scripts/patterns.json").read_text())["max_page_bytes"]
        css = sum(p.stat().st_size for p in (ROOT / "site").glob("*.css"))
        self.assertLess(len(self.doc.encode()) + css, budget // 2)


if __name__ == "__main__":
    unittest.main()
