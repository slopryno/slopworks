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


if __name__ == "__main__":
    unittest.main()
