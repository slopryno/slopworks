"""Trial's tests for the XP ledger and progression rules (i34, Week 1). Written before the profile pages.
They only tighten: every entry resolves to a real artifact, nobody reviews their own XP, no XP without evidence,
totals are the sum of approved entries, and levels are computed from thresholds, never typed."""
import datetime, json, re, sys, unittest
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build, check, xp  # noqa: E402

load = lambda n: json.loads((ROOT / f"data/{n}.json").read_text())
ROLES = {f.stem.capitalize() for f in (ROOT / "bots").glob("*.md")}
PITCH_LEVELS = [("Recruit", 0), ("Apprentice", 100), ("Specialist", 250), ("Operator", 500), ("Expert", 850),
                ("Veteran", 1300), ("Elite", 1850), ("Master", 2500), ("Grandmaster", 3300), ("Legend", 4300)]


class Ledger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.led, cls.prog = build.load("xp_ledger"), build.load("progression")
        cls.files = build.build()
        cls.merged = {w["pr"] for w in load("wins")}

    def test_schema_and_unique_ids(self):
        for n in ("xp_ledger", "progression"):
            self.assertEqual(check.validate(load(n), check.load_schema(n)), [], n)
        ids = [x["id"] for x in self.led]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreater(len(ids), 100)

    def test_every_entry_resolves_to_a_real_artifact(self):
        for x in self.led:
            ev = x["evidence"]
            m = re.match(r"(https://github\.com/slopryno/slopworks/pull/\d+)(#issuecomment-\d+)?$", ev)
            if m:
                self.assertIn(m.group(1), self.merged, f"{x['id']}: {ev} is not a merged PR")
                continue
            path, frag = ev[len(build.BASE):].split("#")
            page = path + "index.html" if path.endswith("/") or not path else path
            self.assertIn(page, self.files, f"{x['id']}: {ev} is not a built page")
            self.assertIn(f'id="{frag}"', self.files[page], f"{x['id']}: {ev} has no anchor")

    def test_no_self_review_and_game_master_never_awards(self):
        for x in self.led:
            self.assertNotEqual(x["agent"], x["reviewer"], x["id"])
            self.assertNotEqual(x["reviewer"], "Gamemaster", x["id"])
            if x["status"] == "approved":
                self.assertIn(x["reviewer"], ROLES | {"CEO"}, x["id"])

    def test_no_xp_without_evidence_and_xp_comes_from_the_table(self):
        for x in self.led:
            self.assertTrue(x["evidence"].startswith("https://"), x["id"])
            t = self.prog["tables"]
            self.assertEqual(x["base_xp"], t.get(x["agent"], {}).get(x["type"], t["default"].get(x["type"])), x["id"])
            self.assertEqual(x["quality_pct"], self.prog["quality"]["default_pct"], x["id"])
            if x["status"] in ("rejected", "reversed", "pending"):
                self.assertTrue(x.get("note"), f"{x['id']}: a non-counting entry says why")

    def test_totals_are_the_sum_of_approved_and_levels_are_computed(self):
        tot = build.xp_totals(self.led)
        for r in ROLES:
            want = sum(x["base_xp"] * x["quality_pct"] // 100 for x in self.led if x["agent"] == r and x["status"] == "approved")
            self.assertEqual(tot.get(r, 0), want, r)
        raw = json.dumps(load("xp_ledger")) + json.dumps(load("progression")["tables"])
        self.assertNotRegex(raw, r'"(level|total|rank)"\s*:', "levels and totals are computed, never typed")
        self.assertEqual([(l["name"], l["xp"]) for l in self.prog["levels"]], PITCH_LEVELS)
        self.assertEqual(build.level_for(0, self.prog["levels"])[1]["name"], "Recruit")
        self.assertEqual(build.level_for(4299, self.prog["levels"])[1]["name"], "Grandmaster")
        self.assertIsNone(build.level_for(4300, self.prog["levels"])[2])

    def test_signoff_cap_and_no_future_times(self):
        cap = self.prog["events"]["signoff"]["cap_per_day"]
        per = {}
        for x in self.led:
            if x["type"] == "signoff" and x["status"] == "approved":
                k = (x["agent"], x["timestamp"][:10])
                per[k] = per.get(k, 0) + 1
        self.assertLessEqual(max(per.values()), cap)
        now = datetime.datetime.now(ZoneInfo("America/New_York"))
        for x in self.led:
            ts = x["timestamp"] if "T" in x["timestamp"] else x["timestamp"] + "T00:00-04:00"
            self.assertLessEqual(datetime.datetime.fromisoformat(ts), now + datetime.timedelta(minutes=10), x["id"])

    def test_rules_cover_every_role(self):
        self.assertEqual(self.prog["owner"], "Gamemaster")
        self.assertTrue(set(self.prog["tables"]) - {"default"} <= ROLES)
        self.assertTrue(ROLES <= set(self.prog["quests"]))
        self.assertEqual(len(self.prog["anti_gaming"]), 6)


class Script(unittest.TestCase):
    """xp.ledger() on a made-up PR list: the rules hold without network."""
    def pr(self, n, body, comments, files=()):
        return {"number": n, "title": f"PR {n}", "body": body, "mergedAt": f"2026-10-17T1{n % 10}:00:00Z",
                "url": f"https://github.com/slopryno/slopworks/pull/{n}", "files": list(files),
                "comments": [{"authorAssociation": a, "body": b, "createdAt": "2026-10-17T15:00:00Z",
                              "url": f"https://github.com/slopryno/slopworks/pull/{n}#issuecomment-{n}{i}"} for i, (a, b) in enumerate(comments)]}

    def test_rules(self):
        prog = load("progression")
        prs = [self.pr(1, "Maker: Pixel", [("OWNER", "Sign-off: Lens"), ("NONE", "Sign-off: Trial"), ("OWNER", "Sign-off: Forge")]),
               self.pr(2, "no maker line", [("OWNER", "Sign-off: Lens")])]
        prs += [self.pr(10 + k, "Maker: Forge", [("OWNER", "Sign-off: Lens")]) for k in range(8)]
        led = [x for x in xp.ledger(prs, prog, {}) if x["type"] in ("pr_merged", "signoff")]
        made = [x for x in led if x["type"] == "pr_merged"]
        self.assertEqual({x["agent"] for x in made}, {"Forge"}, "Pixel counts as Forge, and no Maker line means no XP")
        self.assertNotIn("pull/2", " ".join(x["evidence"] for x in led))
        signs = [x for x in led if x["type"] == "signoff"]
        self.assertEqual({x["agent"] for x in signs}, {"Lens"}, "untrusted and self sign-offs don't count")
        self.assertEqual(sum(x["status"] == "approved" for x in signs), prog["events"]["signoff"]["cap_per_day"])
        self.assertTrue(all(x.get("note") for x in signs if x["status"] == "rejected"))


if __name__ == "__main__":
    unittest.main()


class ChunkedFetch(unittest.TestCase):
    """Trial (Oct 28): xp.py's one 200-PR gh call 502'd and capped the list at 200. fetch_merged() must page by created
    date, retry a 502, and refuse to write a ledger when a merged PR is missing."""

    def fake(self, n, fail_first=0, drop=()):
        import subprocess
        prs = [{"number": i, "createdAt": f"2026-10-{1 + i % 28:02d}T12:00:00Z"} for i in range(1, n + 1)]
        calls = {"n": 0, "heavy": 0}

        def run(args, **kw):
            calls["n"] += 1
            if calls["n"] <= fail_first:
                raise subprocess.CalledProcessError(1, args, stderr="HTTP 502")
            if "--search" not in args:
                out = prs
            else:
                calls["heavy"] += 1
                lo, hi = args[args.index("--search") + 1][len("created:"):].split("..")
                out = [dict(p, title=f"t{p['number']}") for p in prs if lo <= p["createdAt"][:10] <= hi and p["number"] not in drop]
            return type("R", (), {"stdout": json.dumps(out)})()
        return run, calls

    def test_fetches_every_merged_pr_past_200_in_small_chunks(self):
        run, calls = self.fake(230)
        got = xp.fetch_merged(run, chunk=40)
        self.assertEqual([p["number"] for p in got], list(range(1, 231)))
        self.assertGreaterEqual(calls["heavy"], 6)

    def test_retries_a_502(self):
        run, _ = self.fake(10, fail_first=2)
        self.assertEqual(len(xp.fetch_merged(run)), 10)

    def test_a_missing_pr_stops_the_run(self):
        run, _ = self.fake(50, drop={17})
        with self.assertRaises(SystemExit) as e:
            xp.fetch_merged(run)
        self.assertIn("17", str(e.exception))
