"""Quest board page, board feed and oath calendar events (E2): built from data/roadmap.json, never typed."""
import json, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build, check, roadmap  # noqa: E402

FILES = build.build()
PAGE = FILES["roadmap/index.html"]
BOARD = json.loads((ROOT / "data/roadmap.json").read_text())


class Page(unittest.TestCase):
    def test_sections_come_proof_first(self):
        ids = re.findall(r'<h2 id="([a-z]+)"', PAGE)
        self.assertEqual(ids, ["complete", "active", "queued", "rumor", "abandoned", "oaths", "camp", "follow"])

    def test_every_heading_carries_its_plain_word(self):
        for g, (game, plain) in roadmap.GROUPS.items():
            self.assertIn(f'<h2 id="{g}">{game} <span class="sub">({plain})</span></h2>', PAGE)

    def test_every_quest_and_oath_has_an_anchor(self):
        done = sorted((q for q in BOARD["quests"] if q["group"] == "complete"), key=lambda q: q["history"][-1]["date"], reverse=True)
        shown = [q for q in BOARD["quests"] if q["group"] != "complete"] + done[:10]  # Completed shows the newest 10
        for q in shown:
            self.assertIn(f'id="q-{q["id"]}"', PAGE)
        for o in BOARD["oaths"]:
            self.assertIn(f'id="oath-{o["id"]}"', PAGE)

    def test_steps_are_text_never_a_percentage(self):
        self.assertNotRegex(re.sub(r"<[^>]+>", " ", PAGE), r"\d+\s*%")
        for q in BOARD["quests"]:
            if q["group"] not in ("complete", "abandoned"):
                self.assertIn(roadmap.step_label(q["history"][-1]["stage"]), PAGE)

    def test_kept_count_is_computed(self):
        kept, judged = roadmap.kept_count(BOARD["oaths"])
        self.assertIn(f"Oaths kept: {kept} of {judged} judged so far.", PAGE)

    def test_static_and_in_the_work_hub(self):
        self.assertNotIn("<script", PAGE)
        self.assertNotIn("<form", PAGE)
        self.assertIn('href="../roadmap/"', FILES["work/index.html"])
        self.assertIn(f"{build.BASE}roadmap/", FILES["sitemap.xml"])
        self.assertIn("roadmap/index.html", json.loads((ROOT / "data/word_limits.json").read_text())["enforced_pages"])


class Feed(unittest.TestCase):
    def test_feeds_are_valid(self):
        self.assertEqual(check.feed_errors("site/roadmap/feed.xml", FILES["roadmap/feed.xml"]), [])
        self.assertEqual(check.feed_errors("site/roadmap/feed.json", FILES["roadmap/feed.json"]), [])

    def test_one_item_per_event_with_stable_unique_ids(self):
        items = roadmap.feed_items(BOARD)
        ids = [x["id"] for x in items]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, [x["id"] for x in roadmap.feed_items(json.loads(json.dumps(BOARD)))])
        steps = sum(len(q["history"]) for q in BOARD["quests"]) + sum(q["group"] == "abandoned" for q in BOARD["quests"])
        self.assertEqual(len(items), steps + len(BOARD["oaths"]) + sum(o["verdict"] != "open" for o in BOARD["oaths"]))

    def test_a_judged_oath_adds_an_item_and_keeps_the_sworn_one(self):
        b = json.loads(json.dumps(BOARD))
        b["oaths"][1].update(verdict="kept", judged="2026-11-18", evidence="G2")
        ids = {x["id"] for x in roadmap.feed_items(b)}
        self.assertIn(f'roadmap-oath-{b["oaths"][1]["id"]}-kept-2026-11-18', ids)
        self.assertTrue({x["id"] for x in roadmap.feed_items(BOARD)} <= ids)


class Calendar(unittest.TestCase):
    ICS = FILES["calendar.ics"]

    def test_calendar_stays_valid_with_a_refresh_hint(self):
        self.assertEqual(check.ics_errors(self.ICS), [])
        self.assertIn("REFRESH-INTERVAL;VALUE=DURATION:P1D\r\n", self.ICS)

    def test_every_oath_is_an_event(self):
        for o in BOARD["oaths"]:
            self.assertIn(f'UID:oath-{o["id"]}.slopworks-calendar', self.ICS)

    def test_withdrawn_oath_stays_cancelled_with_a_higher_sequence(self):
        b = json.loads(json.dumps(BOARD))
        b["oaths"][0].update(verdict="withdrawn", judged="2026-11-18", reason="Measurement stayed on hold.")
        uid, _, _, _, status, seq = next(x for x in roadmap.calendar_events(b) if x[0] == f'oath-{b["oaths"][0]["id"]}')
        self.assertEqual((status, seq), ("CANCELLED", 1))
        self.assertEqual(next(x for x in roadmap.calendar_events(BOARD) if x[0] == uid)[5], 0)


if __name__ == "__main__":
    unittest.main()
