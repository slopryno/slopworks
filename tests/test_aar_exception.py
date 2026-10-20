"""Trial's tests for the same-day AAR exception (Ryno 2026-10-20 11:02 AM ET: "Yes, let same-day incident write-ups
through the PR limit"). Narrow: one new same-day AAR plus its Team chat thread passes a used-up limit; anything else
in the PR fails the exception, and sign-offs and checks still apply."""
import copy, os, sys, unittest
from datetime import datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import bot, check, tempo  # noqa: E402

ET = ZoneInfo("America/New_York")
DAY = "2026-10-20"
pr = lambda n, t: {"number": n, "merged": f"2026-10-{t}-04:00"}
OLD_AAR = {"id": "aar-old", "date": "2026-10-19", "trigger": "ci-pr", "change_pr": 1, "thread": "c1"}
NEW_AAR = {"id": "aar-new", "date": DAY, "trigger": "incident", "change_pr": 9, "thread": "c3", "shipped_in": 10}
BASE_CHAT = [{"id": "c1", "date": "2026-10-19", "time": "09:00", "from": "Sweep", "to": "Team", "text": "AAR: old"}]
ROOT_MSG = {"id": "c3", "date": DAY, "time": "11:10", "from": "Sweep", "to": "Team", "text": "AAR: the run stopped"}
REPLY = {"id": "c4", "date": DAY, "time": "11:11", "from": "Coordinator", "to": "Sweep", "text": "Thanks", "reply_to": "c3"}
PATHS = ["data/aars.json", "data/chat.json", "data/tempo.json", "data/metrics.json", "site/lessons/index.html"]


def problems(paths=PATHS, aars=None, chat=None, day=DAY, n=10, base_aars=None, base_chat=None):
    return tempo.aar_exception_problems(paths, base_aars or [OLD_AAR], [OLD_AAR, NEW_AAR] if aars is None else aars,
                                        base_chat or BASE_CHAT, BASE_CHAT + [ROOT_MSG, REPLY] if chat is None else chat, day, n)


class Exception_(unittest.TestCase):
    def test_a_same_day_aar_and_its_thread_pass(self):
        self.assertEqual(problems(), [])

    def test_any_other_file_fails(self):
        for extra in ("bots/sweep.md", "scripts/bot.py", "data/updates.json", "data/wins.json", "data/ceo_overrides.json",
                      "data/schema/aars.schema.json", "plans/tracker.md"):
            self.assertTrue(problems(PATHS + [extra]), extra)

    def test_needs_exactly_one_new_same_day_aar(self):
        self.assertTrue(problems(paths=["data/chat.json"]))
        self.assertTrue(problems(aars=[OLD_AAR]))
        self.assertTrue(problems(aars=[OLD_AAR, NEW_AAR, {**NEW_AAR, "id": "aar-two"}]))
        self.assertTrue(problems(aars=[OLD_AAR, {**NEW_AAR, "date": "2026-10-19"}]))
        self.assertTrue(problems(day="2026-10-21"))  # written today, shipped tomorrow: not same-day

    def test_existing_aars_and_chat_stay_untouched(self):
        self.assertTrue(problems(aars=[{**OLD_AAR, "status": "closed"}, NEW_AAR]))
        self.assertTrue(problems(chat=[{**BASE_CHAT[0], "text": "AAR: edited"}, ROOT_MSG, REPLY]))

    def test_chat_must_be_the_aar_thread(self):
        self.assertTrue(problems(chat=BASE_CHAT + [REPLY]))  # no root
        self.assertTrue(problems(chat=BASE_CHAT + [{**ROOT_MSG, "text": "Run note"}, REPLY]))  # root doesn't start with AAR
        self.assertTrue(problems(chat=BASE_CHAT + [ROOT_MSG, {**REPLY, "reply_to": None, "id": "c5"}]))  # stray message
        self.assertTrue(problems(chat=BASE_CHAT + [ROOT_MSG, {**REPLY, "date": "2026-10-19"}]))

    def test_shipped_in_names_this_pr(self):
        self.assertTrue(problems(n=11))
        self.assertTrue(problems(aars=[OLD_AAR, {k: v for k, v in NEW_AAR.items() if k != "shipped_in"}]))

    def test_not_before_ryno_said_yes(self):
        self.assertTrue(problems(day="2026-10-19", aars=[OLD_AAR, {**NEW_AAR, "date": "2026-10-19"}],
                                 chat=BASE_CHAT + [{**ROOT_MSG, "date": "2026-10-19"}]))


class Gate(unittest.TestCase):
    WINS = [pr(n, f"20T0{n}:00") for n in range(1, 10)]  # 9 merged today
    NOW = datetime(2026, 10, 20, 11, 30, tzinfo=ET)
    PENDING = [{"id": "aar-new", "trigger": "incident", "change_pr": 99}]  # unmerged change PR: slowed from now

    def test_used_up_limit_still_refuses_without_the_exception(self):
        with self.assertRaisesRegex(bot.Refused, "slowed mode allows 3"):
            bot.tempo_gate(self.WINS, self.PENDING, self.NOW)
        with self.assertRaisesRegex(bot.Refused, "not a same-day-AAR-only PR: changes more"):
            bot.tempo_gate(self.WINS, self.PENDING, self.NOW, exception=["changes more than a same-day AAR and its thread: x"])

    def test_aar_only_pr_passes(self):
        mode, used, limit = bot.tempo_gate(self.WINS, self.PENDING, self.NOW, exception=[])
        self.assertIn("same-day AAR exception", mode)
        self.assertEqual((used, limit), (9, 3))

    def test_under_the_limit_nothing_changes(self):
        self.assertEqual(bot.tempo_gate(self.WINS[:1], [], self.NOW, exception=[]), ("normal", 1, 18))


class Violations(unittest.TestCase):
    def test_the_aar_pr_is_excused_and_still_counts_toward_the_day(self):
        wins = [pr(n, f"20T0{n}:00") for n in range(1, 4)] + [pr(4, "20T09:30"), pr(5, "20T09:40")]
        trip = {"id": "aar-t", "date": DAY, "trigger": "incident", "change_pr": 1, "thread": "c1"}  # slowed after #1
        carried = {"id": "aar-x", "date": DAY, "trigger": "incident", "change_pr": 4, "thread": "c2", "shipped_in": 5}
        self.assertEqual(len(tempo.violations(wins, [trip])), 2)  # #4 and #5 are over the slowed 3
        excused = []
        v = tempo.violations(wins, [trip, carried], {}, excused)
        self.assertEqual([x.split()[0] for x in v], ["#4"])
        self.assertIn("#5", excused[0])

    def test_shipped_in_from_another_day_excuses_nothing(self):
        wins = [pr(n, f"20T0{n}:00") for n in range(1, 6)]
        trip = {"id": "aar-t", "date": DAY, "trigger": "incident", "change_pr": 1, "thread": "c1"}
        stale = {"id": "aar-x", "date": "2026-10-19", "trigger": "incident", "change_pr": 4, "thread": "c2", "shipped_in": 5}
        self.assertEqual(len(tempo.violations(wins, [trip, stale], {})), 2)


class CI(unittest.TestCase):
    def test_paths_check_runs_the_exception_on_shipped_in(self):
        env = {"BASE": "b", "HEAD": "h", "GITHUB_REF": "refs/pull/10/merge", "BRANCH": "bot/feature-x"}
        files = {("b", "data/aars.json"): [OLD_AAR], ("h", "data/aars.json"): [OLD_AAR, NEW_AAR],
                 ("b", "data/chat.json"): BASE_CHAT, ("h", "data/chat.json"): BASE_CHAT + [ROOT_MSG, REPLY]}
        import json as j

        def fake_run(cmd, **kw):
            ref, _, path = cmd[2].partition(":")
            return mock.Mock(stdout=j.dumps(files[(ref, path)]))
        with mock.patch.dict(os.environ, env), mock.patch.object(check.subprocess, "run", fake_run), \
                mock.patch.object(tempo, "aar_exception_problems", wraps=tempo.aar_exception_problems) as spy:
            with mock.patch.object(check, "changed", lambda b, h: PATHS):
                errs = check.shipped_in_errors()
            self.assertEqual(spy.call_args.args[-1], 10)
            self.assertTrue(all("shipped_in" in e for e in errs))
            with mock.patch.object(check, "changed", lambda b, h: PATHS + ["bots/sweep.md"]):
                self.assertTrue(any("bots/sweep.md" in e for e in check.shipped_in_errors()))

    def test_no_shipped_in_no_check(self):
        env = {"BASE": "b", "HEAD": "h", "GITHUB_REF": "refs/pull/10/merge"}
        same = lambda cmd, **kw: mock.Mock(stdout="[]")
        with mock.patch.dict(os.environ, env), mock.patch.object(check.subprocess, "run", same):
            self.assertEqual(check.shipped_in_errors(), [])

    def test_the_rule_is_quoted(self):
        self.assertEqual(tempo.AAR_EXCEPTION_QUOTE, "Yes, let same-day incident write-ups through the PR limit")
        self.assertIn(tempo.AAR_EXCEPTION_QUOTE, (ROOT / "scripts/tempo.py").read_text())


if __name__ == "__main__":
    unittest.main()
