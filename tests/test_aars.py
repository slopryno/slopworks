"""Trial's tests for same-day after-action reviews (approved by Ryno 2026-10-17). Written to fail on each rule they guard."""
import copy, datetime as dt, json, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check, build  # noqa: E402

load = lambda n: json.loads((ROOT / f"data/{n}.json").read_text())
AARS, CHAT, RUNS = load("aars"), load("chat"), load("runs")
FILES = build.build()


def errs(aars=None, chat=None, runs=None):
    return check.aar_errors(AARS if aars is None else aars, CHAT if chat is None else chat, RUNS if runs is None else runs)


def bad(**change):
    a = copy.deepcopy(AARS)
    a[0].update(change)
    return a


class Aars(unittest.TestCase):
    def test_repo_data_passes(self):
        self.assertIn("aars", check.DATA_FILES)
        self.assertEqual(check.validate(AARS, check.load_schema("aars")), [])
        self.assertEqual(errs(), [])

    def test_schema_requires_every_field(self):
        for k in ("trigger", "links", "expected", "actual", "why", "change", "change_pr", "owner", "status", "thread"):
            a = copy.deepcopy(AARS); a[0].pop(k)
            self.assertTrue(check.validate(a, check.load_schema("aars")), k)
        self.assertTrue(check.validate(bad(trigger="vibes"), check.load_schema("aars")))
        self.assertTrue(errs(bad(why={"text": "Because reasons happened.", "cite": []})))

    def test_cites_must_be_real(self):
        self.assertTrue(errs(bad(why={"text": "Made-up cause for testing.", "cite": ["pr:999"]})))
        self.assertTrue(errs(bad(why={"text": "Made-up cause for testing.", "cite": ["chat:c9999"]})))
        self.assertTrue(errs(bad(why={"text": "Made-up cause for testing.", "cite": ["runlog:2099-01-01-daily"]})))
        self.assertTrue(errs(bad(why={"text": "Made-up cause for testing.", "cite": ["file:scripts/nope.py"]})))

    def test_change_cites_its_pr(self):
        self.assertTrue(errs(bad(change_pr=999)))

    def test_closed_needs_fix(self):
        a = bad(); a[0].pop("fix_pr")
        self.assertTrue(errs(a))
        self.assertTrue(errs(bad(status="open")))  # open with a closed date
        self.assertTrue(errs(bad(closed="2000-01-01")))

    def test_thread_is_aar_root(self):
        self.assertTrue(errs(bad(thread="c2")))

    def test_failed_run_needs_same_day_aar(self):
        runs = RUNS + [{"id": "2099-01-01-daily", "date": "2099-01-01", "status": "failed"}]
        self.assertTrue(any("same-day" in x for x in errs(runs=runs)))

    def test_chat_times_not_in_future(self):
        now = dt.datetime(2026, 10, 17, 7, 36, tzinfo=dt.timezone(dt.timedelta(hours=-4)))
        late = [{"id": "c79", "date": "2026-10-17", "time": "08:05"}]
        self.assertTrue(check.chat_future_errors(late, now))
        self.assertEqual(check.chat_future_errors([{"id": "c79", "date": "2026-10-17", "time": "07:34"}], now), [])
        self.assertEqual(check.chat_future_errors(CHAT), [])

    def test_lessons_page(self):
        html = FILES["lessons/index.html"]
        self.assertEqual(check.a11y_issues(html), [])
        self.assertNotIn("<script", html)
        self.assertLess(len(html.encode()) + (ROOT / "site/style.css").stat().st_size, 0.6 * check.PATTERNS["max_page_bytes"])
        main = [a for a in AARS if f'id="{a["id"]}"' in html]  # older reviews roll to lessons/archive/ (tests/test_lessons_archive.py)
        self.assertGreaterEqual(len(main), 10)
        for a in AARS:
            self.assertTrue(any(f'id="{a["id"]}"' in v for k, v in FILES.items() if k.startswith("lessons/")), a["id"])
        order = [html.index(f'id="{a["id"]}"') for a in sorted(main, key=lambda a: (a["date"], a["id"]), reverse=True)]
        self.assertEqual(order, sorted(order))  # newest first
        self.assertIn("lessons/", FILES["schedule/index.html"])
        self.assertIn('href="../lessons/"', FILES["team/index.html"])  # in the nav
        self.assertIn("site/lessons/index.html", check.SHOWCASE_PAGES)


if __name__ == "__main__":
    unittest.main()
