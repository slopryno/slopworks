"""Trial's tests for the standing tempo and its automatic slowdown (i44, Ryno 2026-10-18 8:35 AM ET)."""
import json, sys, tempfile, unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import bot, check, tempo  # noqa: E402

ET = ZoneInfo("America/New_York")
pr = lambda n, t: {"number": n, "merged": f"2026-10-{t}-04:00"}
aar = lambda trig, cpr: {"id": f"aar-{cpr}", "trigger": trig, "change_pr": cpr}


class Rules(unittest.TestCase):
    def test_normal_without_trips(self):
        t = tempo.derive([pr(1, "19T09:00")], [aar("ci-pr", 1), aar("block-upheld", 1)])
        self.assertEqual((t["mode"], t["clean_prs"]), ("normal", None))

    def test_trip_slows_until_ten_clean_prs(self):
        wins = [pr(1, "19T09:00")] + [pr(n, f"{19 + (n - 2) // 3}T1{(n - 2) % 3}:00") for n in range(2, 12)]
        t = tempo.derive(wins[:10], [aar("data-correction", 1)])
        self.assertEqual((t["mode"], t["clean_prs"]), ("slowed", 9))
        t = tempo.derive(wins, [aar("data-correction", 1)])
        self.assertEqual((t["mode"], t["clean_prs"]), ("normal", 10))

    def test_a_new_trip_resets_the_count(self):
        wins = [pr(n, f"19T{8 + n:02d}:00") for n in range(1, 6)]
        t = tempo.derive(wins, [aar("incident", 1), aar("revert", 4)])
        self.assertEqual((t["mode"], t["clean_prs"], t["trip_pr"]), ("slowed", 1, 4))

    def test_unmerged_change_pr_trips_now(self):
        mode, used, limit = tempo.today([pr(1, "19T09:00")], [aar("ci-main", 2)], datetime(2026, 10, 19, 10, tzinfo=ET))
        self.assertEqual((mode, used, limit), ("slowed", 0, 3))

    def test_slowed_day_counts_only_after_the_trip(self):
        wins = [pr(n, f"19T0{n}:00") for n in range(1, 6)]  # trip at #5, 05:00; #1-#4 don't count
        self.assertEqual(tempo.today(wins, [aar("incident", 5)], datetime(2026, 10, 19, 9, tzinfo=ET)), ("slowed", 0, 3))
        more = wins + [pr(6, "19T06:00"), pr(7, "19T07:00"), pr(8, "19T08:00")]
        self.assertEqual(tempo.today(more, [aar("incident", 5)], datetime(2026, 10, 19, 9, tzinfo=ET)), ("slowed", 3, 3))

    def test_violations_after_the_decision_only(self):
        wins = [pr(n, f"19T{9 + n:02d}:00") for n in range(1, 6)]
        self.assertEqual(len(tempo.violations(wins, [aar("incident", 1)])), 1)  # #2, #3, #4 ok; #5 is the 4th after the trip
        self.assertEqual(tempo.violations([pr(n, "17T10:00") for n in range(1, 31)], []), [])  # before 2026-10-18 08:35


class Enforced(unittest.TestCase):
    def test_bot_refuses_over_the_limit(self):
        wins = [pr(n, f"19T0{n}:00") for n in range(1, 9)]
        with self.assertRaisesRegex(bot.Refused, "slowed mode allows 3"):
            bot.tempo_gate(wins, [aar("incident", 5)], datetime(2026, 10, 19, 9, tzinfo=ET))
        self.assertEqual(bot.tempo_gate(wins[:6], [aar("incident", 5)], datetime(2026, 10, 19, 9, tzinfo=ET))[1], 1)

    def test_bot_refuses_while_main_is_red(self):
        runs = [{"name": "Pages", "status": "completed", "conclusion": "failure"}, {"name": "CI", "status": "completed", "conclusion": "success"}]
        self.assertRaisesRegex(bot.Refused, "main is red", bot.main_red, runs)
        bot.main_red([{"name": "CI", "status": "in_progress", "conclusion": ""}] + runs[1:])

    def test_refusals_are_logged_and_redacted(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "refusals.json"
            now = datetime(2026, 10, 19, 9, tzinfo=ET)
            bot.log_refusal(f, "bot/feature-x", "tempo: slowed mode allows 3\nmore", now)
            bot.log_refusal(f, "bot/feature-x", "data/a.json: possible secret (github_token: ghp_abc)", now)
            log = json.loads(f.read_text())
            self.assertEqual(log[0], {"at": "2026-10-19T09:00-04:00", "branch": "bot/feature-x", "reason": "tempo: slowed mode allows 3"})
            self.assertNotIn("ghp_", log[1]["reason"])
            self.assertEqual(check.validate(log, check.load_schema("refusals")), [])

    def test_check_catches_a_hand_edited_mode(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "data").mkdir()
            for n in ("wins", "aars", "refusals", "tempo"):
                (Path(d) / f"data/{n}.json").write_text((ROOT / f"data/{n}.json").read_text())
            self.assertEqual(check.tempo_errors(Path(d)), [])
            t = json.loads((ROOT / "data/tempo.json").read_text())
            (Path(d) / "data/tempo.json").write_text(json.dumps(dict(t, mode="normal" if t["mode"] == "slowed" else "slowed")))
            self.assertTrue(check.tempo_errors(Path(d)))


class Records(unittest.TestCase):
    def test_tempo_json_is_derived_and_shown(self):
        t = json.loads((ROOT / "data/tempo.json").read_text())
        load = lambda n: json.loads((ROOT / f"data/{n}.json").read_text())
        self.assertEqual(t, tempo.derive(load("wins"), load("aars")))
        self.assertEqual(t["violations"], [])
        import build
        hood = build.build()["hood/index.html"]
        self.assertIn(f"<strong>Pace: {t['mode']}</strong>", hood)


if __name__ == "__main__":
    unittest.main()


class CeoOverride(unittest.TestCase):
    """Ryno 2026-10-19 4:31 PM ET: "Im lifting the slowdown for this work only." Scoped, expiring, add-only."""
    O = {"id": "ovr-2026-10-19-t", "kind": "lift-slowdown", "by": "Ryno (CEO)", "quote": "Im lifting the slowdown for this work only.",
         "source": "test", "at": "2026-10-19T16:31-04:00", "expires": "2026-10-19T23:59-04:00",
         "branches": ["bot/design-a", "bot/design-b"], "max_prs": 2}
    TRIP = [aar("data-correction", 1)]
    WINS = [pr(1, "18T09:00"), pr(2, "19T09:00"), pr(3, "19T10:00"), pr(4, "19T11:00")]  # slowed, 3 of 3 used on the 19th
    at = lambda self, h, m=0: datetime(2026, 10, 19, h, m, tzinfo=ET)

    def test_lifts_only_named_branches_inside_the_window(self):
        o = [self.O]
        self.assertEqual(tempo.today(self.WINS, self.TRIP, self.at(17), "bot/design-a", o)[2], 18)
        self.assertEqual(tempo.today(self.WINS, self.TRIP, self.at(17), "bot/data-daily", o), ("slowed", 3, 3))
        self.assertEqual(tempo.today(self.WINS, self.TRIP, self.at(17), None, o), ("slowed", 3, 3))
        self.assertEqual(tempo.today(self.WINS, self.TRIP, self.at(16, 30), "bot/design-a", o), ("slowed", 3, 3))
        self.assertEqual(tempo.today(self.WINS, self.TRIP, datetime(2026, 10, 20, 0, 1, tzinfo=ET), "bot/design-a", o)[2], 3)

    def test_capped_at_max_prs(self):
        wins = self.WINS + [pr(5, "19T16:40"), pr(6, "19T16:50")]
        self.assertEqual(tempo.today(wins, self.TRIP, self.at(17), "bot/design-b", [self.O]), ("slowed", 5, 3))

    def test_tripwires_stay(self):
        self.assertEqual(tempo.today(self.WINS, self.TRIP + [aar("revert", 99)], self.at(17), "bot/design-a", [self.O]), ("slowed", 0, 3))
        wins = self.WINS + [pr(5, "19T16:40")]  # a new trip merged after the override started ends it
        self.assertEqual(tempo.today(wins, self.TRIP + [aar("ci-main", 5)], self.at(17), "bot/design-a", [self.O]), ("slowed", 0, 3))

    def test_violations_excused_only_inside_the_cap(self):
        wins = self.WINS + [pr(5, "19T16:40"), pr(6, "19T16:50"), pr(7, "19T17:00")]
        t = tempo.derive(wins, self.TRIP, [self.O])
        self.assertEqual(len(t["excused"]), 2)
        self.assertEqual([v.split()[0] for v in t["violations"]], ["#7"])
        self.assertEqual(len(tempo.derive(wins, self.TRIP, [])["violations"]), 3)
        self.assertEqual(t["ceo_overrides"][0]["quote"], self.O["quote"])

    def test_records_are_strict(self):
        for bad in ({"expires": "2026-10-20T09:00-04:00"}, {"expires": "2026-10-19T16:00-04:00"}, {"by": "Advisor"},
                    {"quote": " "}, {"branches": ["main"]}, {"branches": []}, {"max_prs": 3}, {"kind": "bypass"}):
            with tempfile.TemporaryDirectory() as d:
                (Path(d) / "data").mkdir()
                (Path(d) / tempo.OVERRIDES).write_text(json.dumps([{**self.O, **bad}]))
                with self.assertRaises(ValueError, msg=bad):
                    tempo.load_overrides(Path(d))

    def test_override_file_is_add_only(self):
        self.assertTrue(check.loosening("data/ceo_overrides.json", [], ['    "expires": "2026-10-19T23:59-04:00",']))
        self.assertFalse(check.loosening("data/ceo_overrides.json", ['  {"id": "ovr-2026-10-20-x"}'], []))

    def test_the_repo_record_is_valid_and_expires_tonight(self):
        self.assertEqual(check.override_errors(), [])
        for o in tempo.load_overrides():
            self.assertLessEqual(o["expires"][:10], o["at"][:10])
