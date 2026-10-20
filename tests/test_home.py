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
        self.assertIn(f"<li><strong>{roles}</strong> roles</li><li><strong>{len(self.wins)}</strong> merged PRs</li>", self.doc)  # V4 tiles
        last = max(self.wins, key=lambda w: w.get("merged") or w["date"])
        self.assertIn(f'PR #{last["pr"].rsplit("/", 1)[1]}</a>', self.doc)

    def test_sprints_counted_only_when_completed(self):
        items = [{"sprint": "i1", "capped": True, "cue": "retro"}, {"sprint": "i2", "capped": True, "cue": "kickoff"},
                 {"sprint": "i3", "capped": False, "cue": "thread"}, {"cue": "PR #3"}]
        self.assertEqual(home.completed_sprints(items), items[:1])
        tl = "".join(v for k, v in self.files.items() if k.startswith("timeline/"))
        n = int(re.search(r"<li><strong>(\d+)</strong> completed sprints</li>", self.doc).group(1))
        sprints = re.findall(r'<li class="tl-item[^"]*" id="tl-sprint-.*?</li>\s*(?=<li class="tl-item|</ol>)', tl, re.S)
        done = [x for x in sprints if '<span class="tag">Sprint</span>' in x and ">retro</a>" in x]
        self.assertEqual(n, len(done))  # a running sprint shows "kickoff", and a shipped decision isn't a sprint
        self.assertNotIn('<span class="tag">Sprint</span> <time datetime="2026-10-17T21:38', tl)  # i40 was a decision, not a sprint

    def test_tracker_comes_before_the_team(self):
        self.assertLess(self.doc.index('id="tracker"'), self.doc.index('id="team-t"'))
        self.assertIn('href="updates/"', self.doc)
        self.assertIn('href="issues/"', self.doc)

    def test_nothing_invented_or_live(self):
        low = self.doc.lower()
        for word in ("current quest", "live now", "<script", "<form"):
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


class FollowUp(unittest.TestCase):
    """Trial's tests for sprint i42 (c293 to c300): short titles, objectives from real records, the weekly recap, the featured count."""
    @classmethod
    def setUpClass(cls):
        cls.files = build.build()
        cls.doc = cls.files["index.html"]
        cls.ideas = {i["id"]: i for i in json.loads((ROOT / "data/ideas.json").read_text())}
        cls.objectives = json.loads((ROOT / "data/objectives.json").read_text())
        cls.chat = {c["id"] for c in json.loads((ROOT / "data/chat.json").read_text())}

    def test_featured_uses_a_short_title(self):
        h2 = re.search(r'<h2 id="feat-t">([^<]*)</h2>', self.doc).group(1)
        self.assertLessEqual(len(h2), 40)
        self.assertIn(h2, {i.get("short_title") for i in self.ideas.values()})

    def test_featured_count_is_the_retro_range(self):
        sec = re.search(r'<section class="panel feature".*?</section>', self.doc, re.S).group(0)
        n = int(re.search(r"<span>(\d+) merged PRs?</span>", sec).group(1))
        m = re.search(r"#(\d+)\s*(?:-|to)\s*#(\d+)", sec)
        if m:
            self.assertEqual(n, int(m.group(2)) - int(m.group(1)) + 1)
        self.assertEqual(home.pr_count({"text": "6 PRs (#79 to #84)."}), 6)

    def test_objectives_are_real_and_shown_only_for_those_roles(self):
        roles = {f.stem.capitalize() for f in (ROOT / "bots").glob("*.md")}
        for o in self.objectives:
            self.assertIn(o["role"], roles)
            self.assertTrue((ROOT / o["source"]).exists(), o["source"])
            self.assertIn(o["ref"], self.chat)
        sheets = [v for k, v in self.files.items() if re.fullmatch(r"team/\w+/index.html", k) and k != "team/xp/index.html"]
        self.assertEqual(sum(s.count('class="obj"') for s in sheets), len(self.objectives))  # on the sheets since the trading cards (Oct 20)
        cards = re.findall(r'<li class="char">.*?</li>', self.doc, re.S)
        with_obj = {re.search(r"<h3><a[^>]*>(\w+)</a>", c).group(1) for c in cards if 'class="obj"' in c}
        self.assertTrue(with_obj <= {o["role"] for o in self.objectives})

    def test_weekly_recap_is_labelled_and_counted(self):
        page = self.files["weekly/index.html"]
        wins = json.loads((ROOT / "data/wins.json").read_text())
        self.assertIn('href="weekly/"', self.doc)
        first = re.search(r'<section class="panel week".*?</section>', page, re.S).group(0)
        if "Final" not in first:
            self.assertRegex(first, r"Days 1 to [1-7] so far")
            self.assertIn("Nothing here is projected", first)
        total = sum(int(x) for x in re.findall(r"<li><strong>(\d+)</strong> merged PRs</li>", page))
        self.assertEqual(total, len(wins))
        self.assertNotRegex(page.lower(), r"projected (total|week)|on pace|per week average")


class IdeasStayTrue(unittest.TestCase):
    """i43 AAR aar-2026-10-18-stale-ideas (Lens, c306): an approved idea that merged PRs already name is either closed
    as shipped or backed by an open objective that says what's left."""
    def test_named_yes_ideas_have_an_open_objective(self):
        ideas = json.loads((ROOT / "data/ideas.json").read_text())
        wins = json.loads((ROOT / "data/wins.json").read_text())
        owned = {o.get("idea") for o in json.loads((ROOT / "data/objectives.json").read_text())}
        named = {m for w in wins for m in re.findall(r"\b(i\d+)\b", w["title"])}
        stale = sorted(i["id"] for i in ideas if i["state"] == "yes" and i["id"] in named and i["id"] not in owned)
        self.assertEqual(stale, [], "close these as shipped, or add the remaining work to data/objectives.json")

    def test_the_check_fires(self):
        named = {m for m in re.findall(r"\b(i\d+)\b", "Onboard Game Master (i33): bot file")}
        self.assertEqual(named, {"i33"})


class RecapByDay(unittest.TestCase):
    """i43 (Analyst, c304): the recap shows each day's merged PRs and AARs; days add up to the week, from records only."""
    def test_days_add_up_to_the_week(self):
        page = build.build()["weekly/index.html"]
        wins = json.loads((ROOT / "data/wins.json").read_text())
        aars = json.loads((ROOT / "data/aars.json").read_text())
        for sec in re.findall(r'<section class="panel week".*?</section>', page, re.S):
            week = int(re.search(r"<li><strong>(\d+)</strong> merged PRs</li>", sec).group(1))
            days = re.search(r'<ul class="byday">(.*?)</ul>', sec, re.S).group(1)
            self.assertEqual(sum(int(n) for n in re.findall(r": (\d+) merged PRs?", days)), week)
        self.assertEqual(sum(int(n) for n in re.findall(r": (\d+) merged PRs?", page)), len(wins))
        self.assertEqual(sum(int(n) for n in re.findall(r", (\d+) AARs?</li>", page)), len(aars))


if __name__ == "__main__":
    unittest.main()