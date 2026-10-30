"""Trial's tests for the bot.py run lock (F2, pstack statechart review 2026-10-21).

Two bot.py runs must never both hold the lock, and a run may only delete a lock it holds."""
import multiprocessing, os, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import bot  # noqa: E402


def _racer(path, start, wins, hold):
    """Wait for the start signal, try the lock, and keep holding it until told to stop."""
    start.wait()
    try:
        bot.take_lock(path)
    except bot.Refused:
        wins.put(0)
        return
    wins.put(os.getpid())
    hold.wait(5)


class RunLock(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "bot-pr.lock"

    def tearDown(self):
        self.dir.cleanup()

    def test_two_racing_runs_never_both_hold_the_lock(self):
        ctx = multiprocessing.get_context("fork")
        for attempt in range(40):
            self.path.unlink(missing_ok=True)
            start, hold, wins = ctx.Event(), ctx.Event(), ctx.Queue()
            procs = [ctx.Process(target=_racer, args=(self.path, start, wins, hold)) for _ in range(4)]
            for p in procs:
                p.start()
            start.set()
            winners = [w for w in (wins.get(timeout=10) for _ in procs) if w]
            hold.set()
            for p in procs:
                p.join(5)
            self.assertLessEqual(len(winners), 1, f"attempt {attempt}: {len(winners)} runs held the lock at once")

    def test_release_keeps_a_lock_held_by_another_run(self):
        other = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        try:
            bot.take_lock(self.path, pid=other.pid)
            bot.release_lock(self.path)
            self.assertTrue(self.path.exists(), "release_lock deleted a lock another live run holds")
            self.assertEqual(self.path.read_text().split()[0], str(other.pid))
        finally:
            other.kill()
            other.wait()

    def test_release_removes_our_own_lock(self):
        bot.release_lock(bot.take_lock(self.path))
        self.assertFalse(self.path.exists())

    def test_live_holder_refuses_a_second_run(self):
        other = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        try:
            bot.take_lock(self.path, pid=other.pid)
            self.assertRaises(bot.Refused, bot.take_lock, self.path)
        finally:
            other.kill()
            other.wait()

    def test_lock_left_by_a_dead_run_is_replaced(self):
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        self.path.write_text(f"{dead.pid}\n")
        bot.take_lock(self.path)
        self.assertEqual(self.path.read_text().split()[0], str(os.getpid()))

    def test_unreadable_lock_is_treated_as_stale(self):
        self.path.write_text("garbage\n")
        bot.take_lock(self.path)
        self.assertEqual(self.path.read_text().split()[0], str(os.getpid()))


    def test_reclaim_three_run_schedule_no_dual_holders(self):
        """Deterministic S1 replay-step.json schedule against bot.take_lock.

        A holds and releases; B is forced down the reclaim path; A reholds in the
        observe→rename window; C links into the post-rename gap. Old reclaim deleted
        the aside on put-back busy and left A believing it still held while C owned
        the file. Fixed reclaim re-checks before rename and never deletes a live aside.
        """
        from unittest import mock
        sleepers = [subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"]) for _ in range(3)]
        p1, p2, p3 = [s.pid for s in sleepers]
        took = {"p1": False, "p2": False, "p3": False}
        try:
            bot.take_lock(self.path, pid=p1)
            took["p1"] = True
            bot.release_lock(self.path, pid=p1)
            took["p1"] = False

            real_link, real_rename, real_holder = os.link, os.rename, bot._holder
            phase = {"links": 0, "seen_missing": False}

            def link_hook(src, dst, *a, **kw):
                if Path(dst) == self.path:
                    phase["links"] += 1
                    if phase["links"] == 1:
                        raise FileExistsError  # force B into observe/reclaim
                return real_link(src, dst, *a, **kw)

            def holder_hook(path):
                # After observe saw missing, the next _holder (re-verify) must see A's retake.
                if phase["seen_missing"] and Path(path) == self.path and not took["p1"]:
                    with mock.patch("os.link", real_link), mock.patch.object(bot, "_holder", real_holder):
                        bot.take_lock(self.path, pid=p1)
                        took["p1"] = True
                h = real_holder(path)
                if Path(path) == self.path and h is None:
                    phase["seen_missing"] = True
                return h

            def rename_hook(src, dst, *a, **kw):
                if Path(src) == self.path:
                    # Old code reaches here without re-verify: plant A, steal, then C fills the gap.
                    if not self.path.exists():
                        with mock.patch("os.link", real_link), mock.patch("os.rename", real_rename), mock.patch.object(bot, "_holder", real_holder):
                            bot.take_lock(self.path, pid=p1)
                            took["p1"] = True
                    real_rename(src, dst, *a, **kw)
                    with mock.patch("os.link", real_link), mock.patch("os.rename", real_rename), mock.patch.object(bot, "_holder", real_holder):
                        bot.take_lock(self.path, pid=p3)
                        took["p3"] = True
                    return
                return real_rename(src, dst, *a, **kw)

            with mock.patch("os.link", link_hook), mock.patch("os.rename", rename_hook), mock.patch.object(bot, "_holder", holder_hook):
                try:
                    bot.take_lock(self.path, pid=p2)
                    took["p2"] = True
                except bot.Refused:
                    took["p2"] = False

            logical = [pid for flag, pid in (("p1", p1), ("p2", p2), ("p3", p3)) if took[flag]]
            file_holder = int(self.path.read_text().split()[0]) if self.path.exists() else None
            self.assertLessEqual(
                len(logical), 1,
                f"dual holders logical={logical} file={file_holder} (replay-step reclaim steal)",
            )
            if logical:
                self.assertEqual(file_holder, logical[0], f"file holder {file_holder} != logical {logical[0]}")
        finally:
            for s in sleepers:
                s.kill()
                s.wait()


if __name__ == "__main__":
    unittest.main()
