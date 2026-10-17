"""Trial's tests for scripts/bot.py (i30): the helper must agree with CI and refuse the known pitfalls."""
import datetime, itertools, json, os, sys, unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import bot, check  # noqa: E402

PATHS = ["data/updates.json", "data/schema/chat.schema.json", "site/index.html", "scripts/build.py", "tests/test_x.py",
         "bots/forge.md", "docs/onboarding.md", ".github/workflows/ci.yml", "scripts/check.py", "site/assets/avatars/a.svg"]


class BranchKind(unittest.TestCase):
    def test_prototype_agrees_with_ci_path_rule(self):
        """Open question from docs/hardening.md: does the picked branch always pass CI's path rule? Every 1-3 path combination."""
        for n in (1, 2, 3):
            for combo in itertools.combinations(PATHS, n):
                kind = bot.branch_kind(list(combo))
                with mock.patch.object(check, "changed", return_value=list(combo)), \
                        mock.patch.object(check, "pr_context", return_value=("b", "h")), \
                        mock.patch.dict(os.environ, {"BRANCH": f"bot/{kind}-x"}):
                    self.assertEqual(check.run_paths(), [], (kind, combo))

    def test_kinds(self):
        self.assertEqual(bot.branch_kind(["data/updates.json", "site/index.html"]), "data")
        self.assertEqual(bot.branch_kind(["data/schema/chat.schema.json"]), "feature")
        self.assertEqual(bot.branch_kind(["scripts/check.py", "data/x.json"]), "ops")
        self.assertRaises(bot.Refused, bot.branch_kind, [])
        self.assertRaises(bot.Refused, bot.check_kind, "data", ["plans/direction.md"])  # the #35 mistake
        bot.check_kind("design", ["site/style.css"])


class Signoffs(unittest.TestCase):
    def test_refuses_self_signoff(self):
        with self.assertRaisesRegex(bot.Refused, "can't sign it off"):
            bot.plan_signoffs("Lens", ["site/index.html"], {"Lens": "ok", "Trial": "ok"})

    def test_refuses_maker_that_is_required(self):
        with self.assertRaisesRegex(bot.Refused, "required reviewer"):
            bot.plan_signoffs("Trial", ["site/index.html"], {"Lens": "ok"})

    def test_refuses_missing_role_like_38_and_42(self):
        with self.assertRaisesRegex(bot.Refused, "missing sign-off from Coordinator"):
            bot.plan_signoffs("Forge", ["bots/forge.md"], {"Lens": "ok"})

    def test_bodies_pass_review_gate(self):
        paths = ["bots/forge.md", "site/index.html", "data/chat.json"]
        bodies = bot.plan_signoffs("Forge", paths, {"Lens": "ok", "Coordinator": "ok", "Trial": "Sign-off: Trial\nok"})
        comments = [{"body": b, "author_association": "OWNER"} for b in bodies]
        self.assertEqual(check.review_gate(paths, bot.with_maker("x", "Forge"), comments), [])

    def test_aliases_and_unknown_roles(self):
        self.assertRaises(bot.Refused, bot.plan_signoffs, "Forge", ["data/a.json"], {"Lenz": "ok"})
        self.assertEqual(len(bot.plan_signoffs("Forge", ["data/a.json"], {"Verify": "ok"})), 1)
        self.assertRaises(bot.Refused, bot.with_maker, "Maker: Lens\n", "Forge")
        self.assertTrue(bot.with_maker("body", "Core").startswith("Maker: Core"))


class Chat(unittest.TestCase):
    chat = [{"id": "c1", "date": "2026-10-17", "time": "09:00", "from": "Coordinator", "to": "Team", "text": "root"},
            {"id": "c2", "date": "2026-10-17", "time": "09:01", "from": "Lens", "to": "Coordinator", "text": "reply", "reply_to": "c1"}]
    now = datetime.datetime(2026, 10, 17, 13, 50)

    def test_stamps_id_date_and_clock_time(self):
        m = bot.new_chat(self.chat, [], "Trial", "Team", "hi", reply_to="c1", now=self.now)
        self.assertEqual((m["id"], m["date"], m["time"]), ("c3", "2026-10-17", "13:50"))

    def test_refuses_what_ci_would_fail(self):
        self.assertRaises(bot.Refused, bot.new_chat, self.chat, [], "Trial", "Team", "x" * 281, now=self.now)
        self.assertRaises(bot.Refused, bot.new_chat, self.chat, [], "Trial", "Team", "hi", reply_to="c2", now=self.now)
        self.assertRaises(bot.Refused, bot.new_chat, self.chat, [], "Trial", "Team", "hi", idea="i999", now=self.now)
        self.assertRaises(bot.Refused, bot.new_chat, self.chat, [], "Nobody", "Team", "hi", now=self.now)

    def test_default_clock_is_eastern(self):
        before = datetime.datetime.now(bot.ET).replace(second=0, microsecond=0, tzinfo=None)
        m = bot.new_chat(self.chat, [], "Trial", "Team", "hi")
        t = datetime.datetime.strptime(f"{m['date']} {m['time']}", "%Y-%m-%d %H:%M")
        self.assertTrue(before <= t <= before + datetime.timedelta(minutes=1))


class Count(unittest.TestCase):
    def test_counts_from_files(self):
        self.assertEqual(bot.count(ROOT / "data/aars.json"), len(json.loads((ROOT / "data/aars.json").read_text())))
        sitemap = ROOT / "site/sitemap.xml"
        self.assertEqual(bot.count(sitemap, r"<loc>"), sitemap.read_text().count("<loc>"))


if __name__ == "__main__":
    unittest.main()
