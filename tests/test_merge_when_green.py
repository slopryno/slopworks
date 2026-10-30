"""Trial's tests for bot.py merge_when_green after the merge (evening-wrap item, crashed 5 times Oct 21-27).

bot.py pr --merge runs from a PR's own worktree. After GitHub merges, the run must finish cleanly and report
the merged commit, whether it ran from a linked worktree or from the main clone."""
import contextlib, io, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import bot  # noqa: E402

REAL_RUN = subprocess.run


def sh(cwd, *args):
    return REAL_RUN(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, check=True,
                    capture_output=True, text=True).stdout


class MergeWhenGreen(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        d = Path(self.dir.name)
        self.origin, self.clone, self.wt = d / "origin.git", d / "clone", d / "wt"
        sh(d, "init", "-q", "--bare", "-b", "main", str(self.origin))
        sh(d, "clone", "-q", str(self.origin), str(self.clone))
        (self.clone / "a.txt").write_text("a\n")
        sh(self.clone, "add", "a.txt")
        sh(self.clone, "commit", "-q", "-m", "first")
        sh(self.clone, "push", "-q", "origin", "main")
        sh(self.clone, "worktree", "add", "-q", "-b", "bot/feature-x", str(self.wt))
        (self.wt / "b.txt").write_text("b\n")
        sh(self.wt, "add", "b.txt")
        sh(self.wt, "commit", "-q", "-m", "work")

    def tearDown(self):
        self.dir.cleanup()

    def squash_on_github(self):
        """What GitHub's squash merge does: a new commit on origin's main."""
        other = Path(self.dir.name) / "gh"
        sh(Path(self.dir.name), "clone", "-q", str(self.origin), str(other))
        (other / "b.txt").write_text("b\n")
        sh(other, "add", "b.txt")
        sh(other, "commit", "-q", "-m", "Squashed work (#7)")
        sh(other, "push", "-q", "origin", "main")

    def run_merge(self, root):
        def fake_run(cmd, *a, **k):
            if cmd[0] == "gh":
                return subprocess.CompletedProcess(cmd, 0, "ci\tpass\t1m\thttps://x\n", "")
            return REAL_RUN(cmd, *a, **k)

        def fake_gh(*args):
            if args[:2] == ("pr", "view"):
                anth = "Co-Authored-By: " + "Claude" + " " + "Opus" + " " + "5.5" + " <" + "noreply@" + "anthropic.com>"
                import json as _json
                return _json.dumps({"labels": [], "title": "Squashed work", "body": "what\n\n" + anth + "\n"})
            if args[:2] == ("pr", "merge"):
                self.assertIn("--subject", args)
                self.assertIn("--body", args)
                body = args[args.index("--body") + 1]
                self.assertNotIn("anthropic.com", body.lower())
                self.assertNotRegex(body, r"(?i)co-authored-by:")
                self.squash_on_github()
                return ""
            raise AssertionError(args)

        out = io.StringIO()
        with mock.patch.object(bot, "ROOT", root), mock.patch.object(bot, "gh", fake_gh), \
                mock.patch.object(bot.subprocess, "run", fake_run), mock.patch.object(bot.time, "sleep"), \
                contextlib.redirect_stdout(out):
            bot.merge_when_green("7")
        return out.getvalue()

    def test_merge_from_a_worktree_finishes_and_reports_the_merged_commit(self):
        out = self.run_merge(self.wt)
        self.assertIn("merged 7:", out)
        self.assertIn("Squashed work (#7)", out)

    def test_merge_from_the_main_clone_still_updates_main(self):
        sh(self.clone, "worktree", "remove", "--force", str(self.wt))
        sh(self.clone, "checkout", "-q", "bot/feature-x")
        out = self.run_merge(self.clone)
        self.assertIn("Squashed work (#7)", out)
        self.assertEqual(sh(self.clone, "rev-parse", "--abbrev-ref", "HEAD").strip(), "main")
        self.assertIn("Squashed work (#7)", sh(self.clone, "log", "--oneline", "-1"))


if __name__ == "__main__":
    unittest.main()
