"""Usage ledger (#148 item 2): bot.py usage writes one checked row per run; data/usage.json stays valid."""
import datetime, json, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import bot, check  # noqa: E402

NOW = datetime.datetime(2026, 10, 28, 6, 10, tzinfo=bot.ET)
MERGED = [{"number": 150, "merged": "2026-10-28T05:00-04:00"}, {"number": 147, "merged": "2026-10-27T22:18-04:00"}]


class Usage(unittest.TestCase):
    def test_row_counts_minutes_and_todays_merges(self):
        row = bot.new_usage([], "claude-opus-5-5", "04:45", MERGED, now=NOW)
        self.assertEqual(row, {"id": "2026-10-28-daily", "date": "2026-10-28", "model": "claude-opus-5-5",
                               "started": "04:45", "minutes": 85, "prs_merged": 1})

    def test_tokens_only_when_given(self):
        row = bot.new_usage([], "claude-opus-5-5", "04:45", [], tokens_in=1200, tokens_out=300, now=NOW)
        self.assertEqual((row["tokens_in"], row["tokens_out"]), (1200, 300))
        self.assertNotIn("tokens_in", bot.new_usage([], "claude-opus-5-5", "04:45", [], now=NOW))

    def test_refuses_a_second_row_for_the_same_run(self):
        first = bot.new_usage([], "claude-opus-5-5", "04:45", [], now=NOW)
        with self.assertRaises(bot.Refused):
            bot.new_usage([first], "claude-opus-5-5", "04:45", [], now=NOW)

    def test_refuses_bad_input(self):
        for kwargs in ({"started": "25:00"}, {"started": "4.45"}, {"started": "07:00"}, {"model": "Opus 5!"}, {"tokens_in": -1}):
            args = {"model": "claude-opus-5-5", "started": "04:45", **kwargs}
            with self.subTest(kwargs), self.assertRaises(bot.Refused):
                bot.new_usage([], args.pop("model"), args.pop("started"), [], now=NOW, **args)

    def test_ledger_file_is_checked_like_other_data(self):
        self.assertIn("usage", check.DATA_FILES)
        self.assertEqual(check.validate(json.loads((ROOT / "data/usage.json").read_text()), check.load_schema("usage")), [])

    def test_sweep_runs_it_at_the_end_of_every_run(self):
        self.assertIn("scripts/bot.py usage --model", (ROOT / "bots/sweep.md").read_text())


if __name__ == "__main__":
    unittest.main()
