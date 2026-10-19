"""Trial's tests for public metrics and trends (i45, c328 to c335): records only, inspectable, honest directions."""
import json, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build, check, metrics  # noqa: E402

load = lambda n: json.loads((ROOT / f"data/{n}.json").read_text())


class Metrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load("metrics")
        cls.page = build.build()["metrics/index.html"]

    def test_generated_from_records(self):
        self.assertEqual(self.m, metrics.derive(load("wins"), load("aars"), load("ci"), load("ideas"), load("refusals"), load("tempo"),
                                                   load("blast_checks"),  # i46: blast-radius compares count too
                                                   metrics.month1_inputs(load, lambda n: (ROOT / f"data/{n}.json").exists())))  # i60
        for n in ("ci", "metrics", "wins"):
            self.assertEqual(check.validate(load(n), check.load_schema(n)), [], n)

    def test_numbers_match_their_sources(self):
        t, wins, aars = self.m["totals"], load("wins"), load("aars")
        self.assertEqual(t["prs"], len(wins))
        self.assertEqual(sum(d["prs"] for d in self.m["days"]), len(wins))
        self.assertEqual(t["aars"], len(aars))
        self.assertEqual(t["ci_catches"], sum(d["pr_ci_failed_bot"] for d in load("ci")["days"] if d["date"] >= min(w["date"] for w in wins)))
        self.assertEqual(t["main_failures"], sum(d["main_ci_failed"] + d["pages_failed"] for d in load("ci")["days"]))

    def test_every_number_card_has_a_definition_and_source(self):
        cards = re.findall(r"<ul class=\"nums\">(.*?)</ul>", self.page, re.S)[0].split("<li>")[1:]
        self.assertGreaterEqual(len(cards), 8)
        for c in cards:
            self.assertIn('class="def"', c)
            self.assertRegex(c, r'Source: <a href="https://github\.com/slopryno/slopworks/blob/main/data/\w+\.json">')

    def test_trends_are_honest(self):
        self.assertIn("days of history", self.page)
        self.assertIn("so far", self.page)
        for t in self.m["trends"]:
            self.assertIn(t["direction"], ("up", "down", "flat", "n/a"))
            better = next(x[3] for x in metrics.TRENDS if x[0] == t["key"])
            self.assertEqual(t["verdict"] is None, better is None or t["direction"] in ("flat", "n/a"))
        self.assertEqual(self.m["worsening"], [t["key"] for t in self.m["trends"] if t["verdict"] == "worse"])
        for word in ("<script", "velocity", "projected to", "on pace"):
            self.assertNotIn(word, self.page.lower())

    def test_text_not_color_alone(self):
        for row in re.findall(r"<tr><th scope=\"row\">[^<]+</th>.*?</tr>", self.page):
            if 'class="bar"' in row:
                self.assertRegex(row, r'aria-hidden="true"></span>\d+</td>')
        self.assertRegex(self.page, r"\u2191 up|\u2193 down|\u2192 flat")

    def test_linked_and_not_burying_the_tracker(self):
        files = build.build()
        self.assertIn('href="metrics/"', files["index.html"])
        self.assertIn('href="../metrics/"', files["hood/index.html"])
        home = files["index.html"]
        self.assertLess(home.index('aria-labelledby="trk"') if 'aria-labelledby="trk"' in home else home.index("Grok Bot tracker"), home.index('href="metrics/"'))


if __name__ == "__main__":
    unittest.main()


class MonthOneGoals(unittest.TestCase):
    """i60: Strategy's goals show progress from records only; nothing is shown for G1 until a traffic record exists."""
    def inputs(self, **kw):
        d = metrics.month1_inputs(load, lambda n: (ROOT / f"data/{n}.json").exists())
        d.update(kw)
        return d

    def test_g1_waits_for_a_record(self):
        g1 = metrics.goal_progress(**self.inputs(reach=None))[0]
        self.assertEqual((g1["status"], g1["source"]), ("On hold (CEO decision, Oct 19)", ""))

    def test_g1_from_aggregate_counts(self):
        r = [{"date": "2026-10-30", "views_14d": 120, "uniques_14d": 51, "stars": 5, "outside_referrers": ["news.ycombinator.com", "reddit.com"]}]
        self.assertEqual(metrics.goal_progress(**self.inputs(reach=r))[0]["status"], "met")

    def test_g2_and_g3_count_the_records(self):
        g = {x["id"]: x for x in metrics.goal_progress(**self.inputs())}
        n = len(load("cases")) + len(load("arena")) + len(load("challenges"))
        self.assertTrue(g["G2"]["now"].startswith(f"{n} of 12 entries"))
        new = [u for u in load("updates") if u["added"] >= "2026-10-19"]
        self.assertIn(f"of {len(new)} new tracker items", g["G3"]["now"])

    def test_the_page_shows_the_goals(self):
        page = build.build()["metrics/index.html"]
        self.assertIn('id="goals"', page)
        self.assertNotIn("reach.json", page)
