"""Trial's tests for the Timeline (i32): every item resolves to a real artifact, no time is in the future,
dates are ET, and archive rollover keeps every link working."""
import datetime, json, posixpath, re, sys, unittest
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build  # noqa: E402

ET = ZoneInfo("America/New_York")
load = lambda n: json.loads((ROOT / f"data/{n}.json").read_text())


def resolve_all(files, test, prefix="timeline/", check_prs=True):
    merged = {w["pr"] for w in load("wins")}
    pages = [k for k in files if k.startswith(prefix) and k.endswith(".html")]
    n = 0
    for k in pages:
        doc = files[k]
        main = doc[doc.index('<main'):doc.index('</main>')]
        for h in re.findall(r'href="([^"]+)"', main):
            if h.startswith("https://github.com/slopryno/slopworks/pull/"):
                if check_prs:
                    test.assertIn(h, merged, f"{k}: {h} is not a merged PR")
                n += 1
                continue
            if h.startswith(("http", "mailto:")):
                continue
            path, _, frag = h.partition("#")
            target = posixpath.normpath(posixpath.join(posixpath.dirname(k), path)) if path else k
            if target.endswith("/") or target == ".":
                target = target.rstrip("/") + "/index.html" if target != "." else "index.html"
            elif not target.endswith(".html"):
                target += "/index.html"
            test.assertIn(target, files, f"{k}: {h} points at a missing page")
            if frag:
                test.assertIn(f'id="{frag}"', files[target], f"{k}: {h} points at a missing anchor"); n += 1
    return pages, n


class Timeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = build.build()
        # i42: older days roll to archive pages, so record checks read the main page and its archives together.
        cls.doc = cls.files["timeline/index.html"] + "".join(v for k, v in sorted(cls.files.items()) if k.startswith("timeline/archive/"))

    def test_every_item_resolves_to_a_real_artifact(self):
        pages, n = resolve_all(self.files, self)
        self.assertGreater(n, 50)
        items = re.findall(r'<li class="tl-item', "".join(self.files[p] for p in pages))
        self.assertGreater(len(items), 30)

    def test_no_future_times(self):
        now = datetime.datetime.now(ET)
        for k in (k for k in self.files if k.startswith("timeline/")):
            for t in re.findall(r'<time datetime="([^"]+)"', self.files[k]):
                if "T" in t:
                    self.assertLessEqual(datetime.datetime.fromisoformat(t), now + datetime.timedelta(minutes=10), t)
                else:
                    self.assertLessEqual(t, now.strftime("%Y-%m-%d"), t)

    def test_win_dates_are_et(self):
        """AAR 2026-10-17 wins-utc-dates: the date is the ET date of the merge."""
        for w in load("wins"):
            m = datetime.datetime.fromisoformat(w["merged"])
            self.assertEqual(m.astimezone(ET).strftime("%Y-%m-%d"), w["date"], w["id"])
            self.assertEqual(m.utcoffset(), m.astimezone(ET).utcoffset(), w["id"])

    def test_sprints_match_their_retros(self):
        for sid, nums in (("i16", range(30, 35)), ("i24", range(37, 45)), ("i27", range(50, 56)), ("i30", range(56, 60))):
            m = re.search(rf'id="tl-sprint-{sid}".*?<ul class="tl-prs">(.*?)</ul>', self.doc)
            self.assertIsNotNone(m, sid)
            self.assertEqual(sorted(int(x) for x in re.findall(r"PR #(\d+)", m.group(1))), list(nums), sid)

    def test_filters_labels_and_links(self):
        for k in ("shipped", "milestone", "decision", "team", "research", "case", "lesson"):
            self.assertIn(f'href="#type-{k}"', self.doc)
        self.assertNotIn("<script", self.doc)
        self.assertRegex(self.doc, r'data-type="research"[^>]*>.*?lbl-demo.*?Demo challenge')
        self.assertIn('href="../timeline/"', self.files["team/index.html"])  # nav
        self.assertIn('href="timeline/"', self.files["index.html"])  # landing
        self.assertIn(build.BASE + "timeline/", self.files["sitemap.xml"])
        self.assertIn(build.BASE + "timeline/", self.files["llms.txt"])

    def test_rollover_keeps_links_working(self):
        with mock.patch.object(build, "CHAT_TARGET", 0.2):
            files = build.build()
        parts = [k for k in files if k.startswith("timeline/archive/")]
        self.assertTrue(parts, "a small target should roll older days into the archive")
        self.assertIn('href="archive/', files["timeline/index.html"])
        resolve_all(files, self)

    def test_rollover_helper(self):
        units = [("2026-10-17", 30), ("2026-10-16", 30), ("2026-10-15", 30), ("2026-09-30", 30)]
        main, parts = build.rollover(units, lambda u: u[1], 50)
        self.assertEqual([u[0] for u in main], ["2026-10-17"])
        self.assertEqual([(k, [u[0] for u in us]) for k, _, _, us in parts],
                         [("2026-09", ["2026-09-30"]), ("2026-10", ["2026-10-15"]), ("2026-10-2", ["2026-10-16"])])


class SprintGroups(unittest.TestCase):
    """AAR 2026-10-17 timeline-sprint-groups: a shipped decision with no retro range took every later PR (#65, #66)."""
    def test_each_pr_in_one_group_and_decisions_only_take_named_prs(self):
        doc = build.build()["timeline/index.html"]
        ideas = {i["id"]: i for i in load("ideas")}
        seen = []
        for sid, chunk in re.findall(r'id="tl-sprint-(i\d+)"(.*?)</details>', doc, re.S):
            nums = [int(n) for n in re.findall(r'href="https://github.com/slopryno/slopworks/pull/(\d+)"', chunk)]
            seen += nums
            i = ideas[sid]
            if "cap" not in (i["problem"] + " " + (i.get("reason") or "")).lower():
                named = {int(n) for n in re.findall(r"#(\d+)", i.get("shipped") or "")}
                self.assertTrue(set(nums) <= named, f"{sid} groups {nums}, but it only names {sorted(named)}")
        self.assertEqual(len(seen), len(set(seen)), "a PR sits in two sprint groups")


if __name__ == "__main__":
    unittest.main()
