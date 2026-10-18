"""Trial's tests for the home page (mission i41, c286), written before the build: real data only, completed sprints only,
the tracker above the team, no invented objective, no scripts, and the prototype page retired."""
import json, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build, home  # noqa: E402


class Home(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = build.build()
        cls.doc = cls.files["index.html"]
        cls.wins = json.loads((ROOT / "data/wins.json").read_text())

    def test_headline_and_status_from_data(self):
        self.assertIn("<h1>" + home.HEADLINE + "</h1>", self.doc)
        roles = len(list((ROOT / "bots").glob("*.md")))
        self.assertIn(f"<span>{roles} roles</span><span>{len(self.wins)} merged PRs</span>", self.doc)
        last = max(self.wins, key=lambda w: w.get("merged") or w["date"])
        self.assertIn(f'PR #{last["pr"].rsplit("/", 1)[1]}</a>', self.doc)

    def test_sprints_counted_only_when_completed(self):
        items = [{"sprint": "i1", "cue": "retro"}, {"sprint": "i2", "cue": "kickoff"}, {"cue": "PR #3"}]
        self.assertEqual(home.completed_sprints(items), items[:1])
        tl = "".join(v for k, v in self.files.items() if k.startswith("timeline/"))
        n = int(re.search(r"<span>(\d+) completed sprints</span>", self.doc).group(1))
        self.assertEqual(n, tl.count(">retro</a>"))  # a running sprint shows "kickoff" and isn't counted

    def test_tracker_comes_before_the_team(self):
        self.assertLess(self.doc.index('id="tracker"'), self.doc.index('id="team-t"'))
        self.assertIn('href="updates/"', self.doc)
        self.assertIn('href="issues/"', self.doc)

    def test_nothing_invented_or_live(self):
        low = self.doc.lower()
        for word in ("current objective", "current quest", "live now", "<script", "<form"):
            self.assertNotIn(word, low)

    def test_prototype_retired(self):
        self.assertNotIn("prototype/index.html", self.files)
        for k, v in self.files.items():
            if k.endswith(".html"):
                self.assertFalse(re.search(r'href="[^"]*prototype/', v), f"{k} links the prototype")

    def test_page_budget(self):
        budget = json.loads((ROOT / "scripts/patterns.json").read_text())["max_page_bytes"]
        css = sum(p.stat().st_size for p in (ROOT / "site").glob("*.css"))
        self.assertLess(len(self.doc.encode()) + css, budget // 2)


if __name__ == "__main__":
    unittest.main()
