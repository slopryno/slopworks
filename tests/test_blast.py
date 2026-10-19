"""Trial's tests for Atlas's blast-radius duty (i46, Ryno 2026-10-18 10:48 PM ET)."""
import json, sys, tempfile, unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import bot, check  # noqa: E402

ET = ZoneInfo("America/New_York")
NOTE = ("Blast radius: Atlas\nScope: scripts/build.py, read by every page\nCould break: every page's header\n"
        "Detect: tests/test_mobile.py\nRollback: revert the squash commit\nSize: medium")
c = lambda body, who="OWNER": {"body": body, "author_association": who}


class Gate(unittest.TestCase):
    def test_only_shared_paths_need_a_note(self):
        self.assertEqual(check.blast_radius_errors(["data/chat.json", "site/index.html", "bots/atlas.md"], "Maker: Forge", []), [])
        for p in ("scripts/build.py", ".github/workflows/ci.yml", "data/schema/chat.schema.json", "site/style.css", ".gitignore"):
            self.assertTrue(check.blast_radius_errors([p], "Maker: Forge", []), p)

    def test_atlas_note_passes(self):
        self.assertEqual(check.blast_radius_errors(["scripts/bot.py"], "Maker: Forge", [c("Sign-off: Lens\nok"), c(NOTE)]), [])

    def test_maker_note_or_outsider_does_not_count(self):
        forge = NOTE.replace("Blast radius: Atlas", "Blast radius: Forge")
        self.assertTrue(check.blast_radius_errors(["scripts/bot.py"], "Maker: Forge", [c(forge)]))
        self.assertTrue(check.blast_radius_errors(["scripts/bot.py"], "Maker: Forge", [c(NOTE, "NONE")]))

    def test_atlas_cannot_assess_its_own_pr(self):
        self.assertIn("own blast radius", check.blast_radius_errors(["scripts/bot.py"], "Maker: Atlas", [c(NOTE)])[0])
        with self.assertRaises(bot.Refused):
            bot.plan_blast("Atlas", ["scripts/bot.py"], NOTE)

    def test_fields_and_size_required(self):
        self.assertTrue(check.blast_note_errors(NOTE.replace("Rollback: revert the squash commit\n", "")))
        self.assertIn("Size must be", check.blast_note_errors(NOTE.replace("Size: medium", "Size: tiny"))[0])
        self.assertEqual(check.blast_size(NOTE), "medium")
        latest = check.blast_radius_errors(["scripts/bot.py"], "Maker: Forge", [c(NOTE), c(NOTE.replace("Size: medium", "Size: huge"))])
        self.assertTrue(latest)  # the latest note counts

    def test_bot_refuses_before_pushing(self):
        self.assertIsNone(bot.plan_blast("Forge", ["data/chat.json"], None))
        with self.assertRaises(bot.Refused):
            bot.plan_blast("Forge", ["scripts/bot.py"], None)
        with self.assertRaises(bot.Refused):
            bot.plan_blast("Forge", ["scripts/bot.py"], "Blast radius: Atlas\nScope: x")
        self.assertTrue(bot.plan_blast("Forge", ["scripts/bot.py"], NOTE).startswith("Blast radius: Atlas"))


class PostMerge(unittest.TestCase):
    now = datetime(2026, 10, 19, 9, 0, tzinfo=ET)

    def test_trial_or_lens_compares_after_merge(self):
        e = bot.new_blast_check([], 100, "Trial", "matched", "only bot.py and check.py moved", [NOTE], True, self.now)
        self.assertEqual((e["predicted"], e["result"], e["by"]), ("medium", "matched", "Trial"))
        for args in (("Atlas", True, [NOTE]), ("Trial", False, [NOTE]), ("Trial", True, ["Sign-off: Lens"])):
            with self.assertRaises(bot.Refused):
                bot.new_blast_check([], 100, args[0], "matched", "x", args[2], args[1], self.now)
        with self.assertRaises(bot.Refused):
            bot.new_blast_check([e], 100, "Lens", "bigger", "x", [NOTE], True, self.now)

    def test_check_validates_the_record(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "data").mkdir()
            (root / "data/wins.json").write_text(json.dumps([{"pr": "https://github.com/slopryno/slopworks/pull/100"}]))
            good = {"pr": 100, "date": "2026-10-19", "by": "Trial", "predicted": "medium", "result": "matched", "note": "ok"}
            (root / "data/blast_checks.json").write_text(json.dumps([good]))
            self.assertEqual(check.blast_check_errors(root), [])
            (root / "data/blast_checks.json").write_text(json.dumps([good, dict(good, pr=101), dict(good, by="Atlas")]))
            errs = " ".join(check.blast_check_errors(root))
            self.assertIn("Trial", errs)
            (root / "data/blast_checks.json").write_text(json.dumps([good, dict(good, pr=101), good]))
            errs = " ".join(check.blast_check_errors(root))
            self.assertIn("101 isn't merged", errs)
            self.assertIn("checked twice", errs)
        self.assertEqual(check.blast_check_errors(), [])

    def test_atlas_guide_has_every_part(self):
        doc = (ROOT / "bots/atlas.md").read_text()
        for part in ("What could break", "Who or what is affected", "Likelihood and severity", "How we'd notice",
                     "Rollback", "Shrink it", "Blast radius: Atlas", "Size: small|medium|large"):
            self.assertIn(part, doc)


if __name__ == "__main__":
    unittest.main()
