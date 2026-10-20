"""Trial's tests for the team calendar (Ryno, 2026-10-19 9:34 PM ET): month grids, the agenda, the .ics feed, routines
from the schedule, and the holiday-theme rule (no avatar set or switch without plan, design and review on the calendar)."""
import json, re, shutil, sys, tempfile, unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build, cal, check  # noqa: E402

FILES = build.build()
CAL = json.loads((ROOT / "data/calendar.json").read_text())
SCHED = json.loads((ROOT / "data/schedule.json").read_text())


class Cron(unittest.TestCase):
    def test_weekly_and_first_monday(self):
        self.assertTrue(cal.matches(date(2026, 10, 22), "13 9 * * 4"))  # a Thursday
        self.assertFalse(cal.matches(date(2026, 10, 23), "13 9 * * 4"))
        self.assertTrue(cal.matches(date(2026, 11, 2), "13 9 1-7 * 1"))  # first Monday of November
        self.assertFalse(cal.matches(date(2026, 11, 9), "13 9 1-7 * 1"))
        self.assertFalse(cal.matches(date(2026, 11, 5), "13 9 1-7 * 1"))  # in 1-7 but a Thursday: both must hold
        self.assertTrue(cal.matches(date(2026, 10, 25), "0 0 * * 0") and cal.matches(date(2026, 10, 25), "0 0 * * 7"))

    def test_rrule_and_words(self):
        self.assertEqual(cal.rrule("13 9 * * 1"), "FREQ=WEEKLY;BYDAY=MO")
        self.assertEqual(cal.rrule("13 9 1-7 * 1"), "FREQ=MONTHLY;BYDAY=1MO")
        self.assertEqual(cal.cadence("13 9 1-7 * 1"), "First Monday of each month")
        self.assertEqual(cal.cadence("13 9 * * 5"), "Every Friday")

    def test_bad_cron_fails_loudly(self):
        for bad in ("* * *", "13 9 32 * *", "13 9 * * 9"):
            with self.assertRaises(ValueError):
                cal.parse_cron(bad)


class Page(unittest.TestCase):
    html = FILES["calendar/index.html"]

    def test_three_month_grids_with_headers_and_today(self):
        today = date.fromisoformat(json.loads((ROOT / "data/state.json").read_text())["updated"])
        self.assertEqual(self.html.count('<table class="cal" '), 3)
        self.assertEqual(self.html.count('<th scope="col">'), 21)
        for y, m in cal.months(today):
            self.assertIn(f'<table class="cal" aria-labelledby="m-{y}-{m:02d}">', self.html)
        self.assertEqual(self.html.count('aria-current="date"'), 1)
        self.assertIn(f'aria-current="date"><time datetime="{today.isoformat()}">', self.html)
        for y, m in cal.months(today):
            self.assertIn(f'<h2 id="m-{y}-{m:02d}">{cal.MONTH[m - 1]} {y}</h2>', self.html)

    def test_no_scripts_no_inputs_and_a11y(self):
        self.assertEqual(check.a11y_issues(self.html), [])
        body = self.html.split('<main', 1)[1]
        self.assertNotIn("<input", body)
        self.assertNotIn("<script", self.html)

    def test_reachable_in_two_taps_with_back_and_next(self):
        self.assertIn('href="../calendar/"', FILES["hood/index.html"])
        self.assertIn('href="hood/"', FILES["index.html"])
        self.assertIn('href="../calendar/"', FILES["schedule/index.html"])
        self.assertIn('class="back"><a href="../hood/">', self.html)
        self.assertIn('class="next"', self.html)
        self.assertIn('href="../calendar.ics"', self.html)

    def test_every_dated_event_in_window_is_in_the_agenda(self):
        today = date.fromisoformat(json.loads((ROOT / "data/state.json").read_text())["updated"])
        for x in cal.dated(CAL):
            self.assertIn(f'<time datetime="{x["date"].isoformat()}">{cal.nice(x["date"])}</time>', self.html, x["id"])

    def test_past_days_show_no_invented_routines(self):
        start = date.fromisoformat(CAL["recurring_from"])
        self.assertFalse([x for x in cal.recurring(CAL, SCHED, date(2026, 10, 1), date(2026, 12, 31)) if x["date"] < start])

    def test_word_limits_enforced_here(self):
        self.assertIn("calendar/index.html", json.loads((ROOT / "data/word_limits.json").read_text())["enforced_pages"])
        cfg = json.loads((ROOT / "data/word_limits.json").read_text())
        self.assertEqual(check.page_word_errors("calendar/index.html", self.html, cfg), [])

    def test_inline_style_keeps_shared_css_unchanged(self):
        self.assertIn("<style>.cal-month", self.html)
        self.assertNotIn(".cal{", (ROOT / "site/style.css").read_text())


class Feed(unittest.TestCase):
    text = FILES["calendar.ics"]

    def test_valid_shape(self):
        self.assertEqual(check.ics_errors(self.text), [])
        self.assertNotIn("@", self.text)  # no addresses: UIDs carry no domain part
        self.assertEqual(check.pii_hits(self.text), [])

    def test_routines_recur_and_themes_span_their_window(self):
        self.assertIn("RRULE:FREQ=WEEKLY;BYDAY=FR", self.text)
        self.assertIn("RRULE:FREQ=MONTHLY;BYDAY=1MO", self.text)
        self.assertIn("DTSTART;VALUE=DATE:20261201\r\nDTEND;VALUE=DATE:20270101", self.text)  # Ryno 9:52 PM ET: Dec 1-31
        self.assertIn("DTSTART;VALUE=DATE:20261020\r\nDTEND;VALUE=DATE:20261101", self.text)  # Halloween live from Oct 20

    def test_ics_errors_catch_bad_feeds(self):
        self.assertTrue(check.ics_errors("BEGIN:VCALENDAR\nEND:VCALENDAR\n"))
        long = "BEGIN:VCALENDAR\r\n" + "X" * 80 + "\r\nEND:VCALENDAR\r\n"
        self.assertTrue(check.ics_errors(long))
        dup = "BEGIN:VCALENDAR\r\n" + "BEGIN:VEVENT\r\nUID:a\r\nEND:VEVENT\r\n" * 2 + "END:VCALENDAR\r\n"
        self.assertTrue(check.ics_errors(dup))

    def test_folding_never_splits_a_character(self):
        line = "DESCRIPTION:" + "\u2713" * 60
        folded = cal._fold(line)
        self.assertTrue(all(len(p.encode()) <= 75 for p in folded.split("\r\n")))
        self.assertEqual(folded.replace("\r\n ", ""), line)


class HolidayRule(unittest.TestCase):
    """The rule in code: copy the repo's data into a temp root, break one thing, and check.calendar_errors must say so."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for d in ("data", "data/schema", "bots", "site/assets/avatars"):
            (self.tmp / d).mkdir(parents=True, exist_ok=True)
        for f in ("data/calendar.json", "data/schedule.json", "data/state.json", "data/schema/calendar.schema.json"):
            shutil.copy(ROOT / f, self.tmp / f)
        for f in (ROOT / "bots").glob("*.md"):
            shutil.copy(f, self.tmp / "bots" / f.name)
        shutil.copy(ROOT / "site/calendar.ics", self.tmp / "site/calendar.ics")
        self.cal = json.loads((self.tmp / "data/calendar.json").read_text())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def errs(self):
        (self.tmp / "data/calendar.json").write_text(json.dumps(self.cal))
        return check.calendar_errors(self.tmp)

    def drop(self, theme, step):
        self.cal["events"] = [x for x in self.cal["events"] if not (x.get("theme") == theme and x.get("step") == step)]

    def test_repo_calendar_passes(self):
        self.assertEqual(check.calendar_errors(), [])
        self.assertEqual(self.errs(), [])

    def test_switch_without_plan_design_or_review_fails(self):
        for step in ("plan", "design", "review", "ceo-yes"):
            self.setUp()
            self.drop("winter-2026", step)
            self.assertTrue(any(f"without a {step} event" in x for x in self.errs()), step)

    def test_avatar_set_without_a_theme_fails(self):
        (self.tmp / "site/assets/avatars/forge-thanksgiving.svg").write_text("<svg/>")
        self.assertTrue(any("holiday set 'thanksgiving'" in x for x in self.errs()))
        (self.tmp / "site/assets/avatars/forge-halloween.svg").write_text("<svg/>")
        self.assertFalse(any("'halloween'" in x for x in self.errs()))
        (self.tmp / "site/assets/avatars/easter").mkdir()
        (self.tmp / "site/assets/avatars/easter/forge.svg").write_text("<svg/>")
        self.assertTrue(any("holiday set 'easter'" in x for x in self.errs()))

    def test_everyday_avatars_and_still_copies_are_not_a_set(self):
        (self.tmp / "site/assets/avatars/forge.svg").write_text("<svg/>")
        (self.tmp / "site/assets/avatars/still").mkdir()
        (self.tmp / "site/assets/avatars/still/forge.svg").write_text("<svg/>")
        self.assertEqual(self.errs(), [])

    def seasons(self, text):
        (self.tmp / "scripts").mkdir(exist_ok=True)
        (self.tmp / "scripts/avatars.py").write_text(text)
        return self.errs()

    def test_avatars_py_seasons_must_match_the_calendar(self):
        ok = 'SEASONS = {"halloween": ((10, 1), (10, 31)), "winter": ((12, 1), (12, 31))}\n'
        self.assertEqual(self.seasons(ok), [])
        old = 'SEASONS = {"halloween": ((10, 15), (10, 31)), "winter": ((12, 1), (12, 26))}\n'
        self.assertTrue(any("doesn't match scripts/avatars.py" in x for x in self.seasons(old)))
        extra = ok.replace("}\n", ', "easter": ((4, 1), (4, 30))}\n')
        self.assertTrue(any("season 'easter' switches with no scheduled theme" in x for x in self.seasons(extra)))

    def test_a_season_needs_next_years_dates_once_this_one_ends(self):
        ok = 'SEASONS = {"halloween": ((10, 1), (10, 31)), "winter": ((12, 1), (12, 31))}\n'
        self.cal["themes"] = [t for t in self.cal["themes"] if t["id"] != "winter-2027"]
        self.cal["events"] = [x for x in self.cal["events"] if x.get("theme") != "winter-2027"]
        state = json.loads((self.tmp / "data/state.json").read_text())
        state["updated"] = "2027-01-02"
        (self.tmp / "data/state.json").write_text(json.dumps(state))
        self.assertTrue(any("season 'winter' has no current or upcoming theme" in x for x in self.seasons(ok)))

    def test_placeholder_cannot_carry_a_set_or_switch(self):
        t = next(t for t in self.cal["themes"] if t["status"] == "placeholder")
        t["switch_on"], t["switch_off"] = "2027-02-07", "2027-02-14"
        self.assertTrue(any("placeholder has no avatar set or switch" in x for x in self.errs()))

    def test_placeholder_is_plan_only(self):
        tid = next(t["id"] for t in self.cal["themes"] if t["status"] == "placeholder")
        self.cal["events"].append({"id": "x-design", "date": "2027-01-20", "title": "Design", "owner": "Polish", "type": "holiday-theme",
                                   "status": "planned", "theme": tid, "step": "design"})
        self.assertTrue(any("only has planned plan events" in x for x in self.errs()))

    def test_only_ryno_gives_the_yes(self):
        x = next(x for x in self.cal["events"] if x.get("step") == "ceo-yes")
        x["owner"] = "Assistant"
        self.assertTrue(any("only Ryno gives the yes" in e for e in self.errs()))

    def test_review_after_switch_or_out_of_order_fails(self):
        x = next(x for x in self.cal["events"] if x["id"] == "wi26-review")
        x["date"] = "2026-12-05"
        self.assertTrue(any("on or before the switch" in e for e in self.errs()))
        x["date"] = "2026-10-01"
        self.assertTrue(any("in that order" in e for e in self.errs()))

    def test_review_needs_a_week_of_lead_time(self):
        x = next(x for x in self.cal["events"] if x["id"] == "wi26-review")
        x["date"] = "2026-11-28"
        self.assertTrue(any("at least a week before" in e for e in self.errs()))

    def test_designer_cannot_review_own_set(self):
        x = next(x for x in self.cal["events"] if x["id"] == "wi26-review")
        x["owner"], x["with"] = "Polish", []
        self.assertTrue(any("never the same role" in e for e in self.errs()))

    def test_done_in_the_future_and_unknown_owner_fail(self):
        x = next(x for x in self.cal["events"] if x["id"] == "wi26-design")
        x["status"] = "done"
        self.assertTrue(any("marked done" in e for e in self.errs()))
        x["status"], x["owner"] = "planned", "Santa"
        self.assertTrue(any("Santa isn't a role" in e for e in self.errs()))

    def test_routine_must_exist_in_schedule(self):
        self.cal["recurring"][0]["schedule_id"] = "nope"
        self.assertTrue(any("not an item in data/schedule.json" in e for e in self.errs()))

    def test_long_titles_and_notes_fail(self):
        self.cal["events"][0]["note"] = " ".join(["word"] * 21)
        self.assertTrue(any("note over" in e for e in self.errs()))


class Switch(unittest.TestCase):
    def test_active_set_needs_window_and_yes(self):
        self.assertEqual(cal.active_set(CAL, date(2026, 10, 20)), "halloween")
        self.assertIsNone(cal.active_set(CAL, date(2026, 11, 1)))
        self.assertIsNone(cal.active_set(CAL, date(2026, 12, 5)))  # winter yes not done yet: stays off
        c = json.loads(json.dumps(CAL))
        next(x for x in c["events"] if x["id"] == "wi26-yes")["status"] = "done"
        self.assertEqual(cal.active_set(c, date(2026, 12, 31)), "winter")
        self.assertIsNone(cal.active_set(c, date(2027, 1, 1)))
        self.assertEqual(cal.active_set(CAL, date(2026, 10, 1)), "halloween")  # full month (Ryno, 9:52 PM ET)


if __name__ == "__main__":
    unittest.main()
