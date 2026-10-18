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


class VisualReview(unittest.TestCase):
    """AAR 2026-10-17 (/work/ incident): design and CSS PRs need screenshots of every page and sign-offs that looked.
    Ryno, 2026-10-17 8:49 PM ET: the screenshots live on the box and in the PR's CI artifact, never in git."""
    good = {"Polish": "Screenshots reviewed: all 6 sets\nProblems found: none", "Trial": "Screenshots reviewed: all\nProblems found: tables, fixed",
            "Lens": "ok"}
    paths = ["site/style.css"]

    def make(self, drop=None, tamper=None):
        import shots, tempfile
        root, full = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
        for page in ("index.html", "work/index.html"):
            (root / "site" / page).parent.mkdir(parents=True, exist_ok=True)
            (root / "site" / page).write_text("<p>x")
            for theme in shots.THEMES:
                for w in shots.WIDTHS:
                    f = full / f"{theme}-{w}" / f"{shots.slug(page)}.part1.webp"
                    f.parent.mkdir(parents=True, exist_ok=True)
                    f.write_bytes(f"{theme}{w}{page}".encode())
        m = shots.manifest(9, full)
        if drop:
            del m["files"][drop]
        if tamper:
            (full / tamper).write_bytes(b"changed after the review")
        (full / "manifest.json").write_text(json.dumps(m))
        return root, full

    def check(self, root, full, signoffs=None, paths=None):
        bot.plan_review(9, "feature", paths or self.paths, signoffs or self.good, root, full=full)

    def test_which_prs_need_it(self):
        self.assertTrue(bot.needs_visual_review("feature", ["site/style.css"]))
        self.assertTrue(bot.needs_visual_review("feature", ["scripts/build.py"]))
        self.assertTrue(bot.needs_visual_review("feature", ["site/assets/avatars/a.svg"]))
        self.assertTrue(bot.needs_visual_review("design", ["data/design_backlog.json"]))
        self.assertFalse(bot.needs_visual_review("data", ["data/chat.json", "site/chat/index.html"]))

    def test_refuses_without_review_number(self):
        with self.assertRaisesRegex(bot.Refused, "--review N"):
            bot.plan_review(None, "feature", ["site/style.css"], self.good)

    def test_passes_with_every_page_and_real_signoffs(self):
        self.check(*self.make())

    def test_refuses_no_set_on_the_box(self):
        import tempfile
        root, _ = self.make()
        with self.assertRaisesRegex(bot.Refused, "no review set"):
            self.check(root, Path(tempfile.mkdtemp()))

    def test_refuses_a_missing_page_width_or_theme(self):
        with self.assertRaisesRegex(bot.Refused, "dark-768/work"):
            self.check(*self.make(drop="dark-768/work.part1.webp"))

    def test_refuses_files_changed_after_the_manifest(self):
        with self.assertRaisesRegex(bot.Refused, "don't match"):
            self.check(*self.make(tamper="light-390/home.part1.webp"))

    def test_refuses_signoffs_that_did_not_look(self):
        """The #72-#76 sign-offs: numbers only, no screenshots named, no problems listed."""
        for bad in ({"Polish": "0 overflow, looks good", "Trial": self.good["Trial"]},
                    {"Polish": self.good["Polish"], "Trial": "Screenshots reviewed: all"},
                    {"Trial": self.good["Trial"], "Lens": "ok"}):
            with self.assertRaisesRegex(bot.Refused, "visual review incomplete"):
                self.check(*self.make(), signoffs=bad)

    def test_refuses_images_in_git_on_any_pr(self):
        """Ryno, 8:49 PM ET: no screenshots in the repo, not even small ones. Real site assets stay."""
        for img in ("docs/design/review/9/light-360/home.part1.webp", "docs/design/x/after.png", "shot.jpg"):
            with self.assertRaisesRegex(bot.Refused, "can't be committed"):
                bot.plan_review(None, "data", ["data/chat.json", img], self.good)
        bot.plan_review(None, "data", ["site/badges/roles.svg", "data/x.json"], self.good)  # a real site asset is fine

    def test_artifact(self):
        self.assertEqual(bot.artifact_problems(9, [{"name": "review-shots-9", "expired": False}]), [])
        self.assertTrue(bot.artifact_problems(9, [{"name": "review-shots-8", "expired": False}]))
        self.assertTrue(bot.artifact_problems(9, [{"name": "review-shots-9", "expired": True}]))
        self.assertTrue(bot.artifact_problems(9, []))

    def test_review_note_names_the_artifact_not_a_path_in_git(self):
        root, full = self.make()
        note = bot.review_note(9, full)
        self.assertIn("review-shots-9", note)
        self.assertIn("12 files", note)
        self.assertNotIn("docs/design", note)


if __name__ == "__main__":
    unittest.main()
