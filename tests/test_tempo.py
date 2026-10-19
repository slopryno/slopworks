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
        mode, used, limit = tempo.today([pr(1, "18T09:00")], [aar("ci-main", 2)], datetime(2026, 10, 18, 10, tzinfo=ET))
        self.assertEqual((mode, used, limit), ("slowed", 0, 3))  # through Oct 18 a pending trip started the count at 0
        mode, used, limit = tempo.today([pr(1, "20T09:00")], [aar("ci-main", 2)], datetime(2026, 10, 20, 10, tzinfo=ET))
        self.assertEqual((mode, used, limit), ("slowed", 1, 3))  # from Oct 19 the day's earlier PR still counts

    def test_slowed_day_counts_only_after_the_trip_through_oct_18(self):
        wins = [pr(n, f"18T0{n}:00") for n in range(1, 6)]  # trip at #5, 05:00; #1-#4 don't count (old rule)
        self.assertEqual(tempo.today(wins, [aar("incident", 5)], datetime(2026, 10, 18, 9, tzinfo=ET)), ("slowed", 0, 3))
        more = wins + [pr(6, "18T06:00"), pr(7, "18T07:00"), pr(8, "18T08:00")]
        self.assertEqual(tempo.today(more, [aar("incident", 5)], datetime(2026, 10, 18, 9, tzinfo=ET)), ("slowed", 3, 3))

    def test_a_trip_cannot_reopen_the_day_from_oct_19(self):
        """The loophole (Ryno 2026-10-19 7:27 AM ET): 3 PRs, then a trip, used to allow 3 more the same day."""
        wins = [pr(n, f"20T0{n}:00") for n in range(1, 4)]
        self.assertEqual(tempo.today(wins, [aar("data-correction", 3)], datetime(2026, 10, 20, 9, tzinfo=ET)), ("slowed", 3, 3))
        self.assertEqual(tempo.today(wins, [aar("data-correction", 4)], datetime(2026, 10, 20, 9, tzinfo=ET)), ("slowed", 3, 3))  # pending
        with self.assertRaises(bot.Refused):
            bot.tempo_gate(wins, [aar("data-correction", 3)], datetime(2026, 10, 20, 9, tzinfo=ET))
        late = wins + [pr(4, "20T10:00")]
        self.assertTrue(tempo.violations(late, [aar("data-correction", 3)]))

    def test_violations_after_the_decision_only(self):
        wins = [pr(n, f"18T{9 + n:02d}:00") for n in range(1, 6)]
        self.assertEqual(len(tempo.violations(wins, [aar("incident", 1)])), 1)  # Oct 18 rule: #2, #3, #4 ok; #5 is the 4th after the trip
        wins = [pr(n, f"20T{9 + n:02d}:00") for n in range(1, 6)]
        self.assertEqual(len(tempo.violations(wins, [aar("incident", 1)])), 2)  # from Oct 19 the trip PR counts too: #4 and #5 are over
        self.assertEqual(tempo.violations([pr(n, "17T10:00") for n in range(1, 31)], []), [])  # before 2026-10-18 08:35


class Enforced(unittest.TestCase):
    def test_bot_refuses_over_the_limit(self):
        wins = [pr(n, f"18T0{n}:00") for n in range(1, 9)]
        with self.assertRaisesRegex(bot.Refused, "slowed mode allows 3"):
            bot.tempo_gate(wins, [aar("incident", 5)], datetime(2026, 10, 18, 9, tzinfo=ET))
        self.assertEqual(bot.tempo_gate(wins[:6], [aar("incident", 5)], datetime(2026, 10, 18, 9, tzinfo=ET))[1], 1)
        with self.assertRaisesRegex(bot.Refused, "slowed mode allows 3"):  # from Oct 19, every PR that day counts
            bot.tempo_gate([pr(n, f"20T0{n}:00") for n in range(1, 7)], [aar("incident", 5)], datetime(2026, 10, 20, 9, tzinfo=ET))

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
