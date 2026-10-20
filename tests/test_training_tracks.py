"""Training tracks (Ryno, 2026-10-20 7:05 AM ET: "lets send polish and gamemaster to training. Mobile design and
development. Heavy on UI/UX design principles"). Trial's tests: the track in data/skills.json is sourced, tied to the
roles that name it, audited once per role by a different grader, earns no XP, and the small checks it added hold."""
import json, shutil, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check  # noqa: E402
import skills  # noqa: E402

MAN = json.loads((ROOT / "data/skills.json").read_text())
TRACK = MAN["tracks"]["mobile-uiux"]


class RepoTrack(unittest.TestCase):
    def test_repo_track_is_clean(self):
        self.assertEqual(check.track_errors(), [])

    def test_roles_share_fundamentals_and_differ_in_focus(self):
        p = {m["id"] for m in skills.track_modules(TRACK, "Polish")}
        g = {m["id"] for m in skills.track_modules(TRACK, "Gamemaster")}
        self.assertEqual(TRACK["roles"], ["Polish", "Gamemaster"])
        self.assertGreaterEqual(len(p & g), 4)
        self.assertTrue(p - g and g - p)

    def test_every_module_has_principle_use_practice_and_check(self):
        for m in TRACK["modules"]:
            for k in ("principle", "slopworks", "practice"):
                self.assertTrue(m[k].strip(), (m["id"], k))
            self.assertIn(m["check"]["state"], ("enforced", "proposed"))
            self.assertTrue(m["sources"])

    def test_audits_are_at_390_with_real_findings_and_no_xp(self):
        for role, x in TRACK["exercises"].items():
            self.assertEqual(x["width"], 390)
            self.assertNotEqual(x["grade"]["by"], role)
            self.assertTrue(any(g["kind"] in ("defect", "risk") for g in x["findings"]), role)
            self.assertFalse({"xp", "points", "award"} & set(x), role)  # training earns no XP (Gamemaster ruling, c393)
        ledger = (ROOT / "data/xp_ledger.json").read_text()
        self.assertNotIn("mobile-uiux", ledger)

    def test_sheets_and_cards_show_the_track(self):
        for role in ("polish", "gamemaster"):
            page = (ROOT / f"site/team/{role}/index.html").read_text()
            self.assertIn('id="track-mobile-uiux"', page)
            self.assertIn("Audit of the live site at 390px", page)
        team = (ROOT / "site/team/index.html").read_text()
        self.assertEqual(team.count("the Mobile UI/UX track"), 2)


class Fixture(unittest.TestCase):
    """A copy of the repo's track with two role files; each case breaks one thing."""
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        (self.root / "bots").mkdir()
        (self.root / "data/schema").mkdir(parents=True)
        shutil.copy(ROOT / "data/schema/skills.schema.json", self.root / "data/schema/")
        shutil.copy(ROOT / "data/design_backlog.json", self.root / "data/")
        self.man = json.loads(json.dumps(MAN))
        for r in ("polish", "gamemaster"):
            shutil.copy(ROOT / f"bots/{r}.md", self.root / f"bots/{r}.md")
        self.save()

    @property
    def t(self):
        return self.man["tracks"]["mobile-uiux"]

    def save(self):
        (self.root / "data/skills.json").write_text(json.dumps(self.man))

    def errs(self):
        self.save()
        return skills.track_errors(self.root, check.validate)

    def assertFlags(self, text):
        e = self.errs()
        self.assertTrue(any(text in x for x in e), e)

    def test_fixture_is_clean(self):
        self.assertEqual(self.errs(), [])

    def test_source_host_must_be_on_the_list(self):
        self.t["sources"]["web" + "dev-vitals"]["url"] = "https://example.com/vitals"
        self.assertFlags("isn't on TRACK_HOSTS")

    def test_source_query_string_fails(self):
        self.t["sources"]["nng-touch"]["url"] += "?utm_source=x"
        self.assertFlags("no query string")

    def test_unknown_and_unused_sources_fail(self):
        self.t["modules"][0]["sources"].append("made-up")
        self.t["sources"]["spare"] = {"publisher": "W3C", "title": "Spare", "url": "https://www.w3.org/WAI/"}
        self.assertFlags("unknown source made-up")
        self.assertFlags("source spare isn't used")

    def test_unpinned_skill_fails(self):
        self.t["modules"][0]["skills"] = ["not-a-skill"]
        self.assertFlags("isn't a pinned skill")

    def test_role_cannot_grade_its_own_audit(self):
        self.t["exercises"]["Polish"]["grade"]["by"] = "Polish"
        self.assertFlags("can't grade its own audit")

    def test_no_xp_field_on_an_audit(self):
        self.t["exercises"]["Gamemaster"]["xp"] = 25
        self.assertFlags("unexpected field xp")

    def test_finding_must_cite_its_roles_module(self):
        self.t["exercises"]["Gamemaster"]["findings"][0]["module"] = "m7"  # a Polish-only module
        self.assertFlags("which isn't in Gamemaster's track")

    def test_finding_backlog_reference_must_exist(self):
        self.t["exercises"]["Polish"]["findings"][0]["next"] = "d99"
        self.assertFlags("d99, which isn't in data/design_backlog.json")

    def test_each_role_needs_one_audit(self):
        del self.t["exercises"]["Gamemaster"]
        self.assertFlags("exactly one audit per role")

    def test_role_file_line_both_ways(self):
        (self.root / "bots/gamemaster.md").write_text("# Gamemaster\n\n**Role:** Test.\n")
        (self.root / "bots/trial.md").write_text("# Trial\n\n**Training track:** `mobile-uiux` (test)\n")
        self.assertFlags("bots/gamemaster.md: needs a **Training track:** `mobile-uiux` line")
        self.assertFlags("bots/trial.md: names track mobile-uiux, which doesn't list it")

    def test_unknown_track_in_a_role_file(self):
        (self.root / "bots/polish.md").write_text((ROOT / "bots/polish.md").read_text() + "\n**Training track:** `ghost` (x)\n")
        self.assertFlags("names unknown track ghost")


class AddedChecks(unittest.TestCase):
    """The small checks this track added (enforce in code first): zoom, image boxes, reduced motion."""
    PAGE = '<!doctype html><html lang="en"><head><title>t</title><meta name="viewport" content="{vp}"></head><body><main><h1>t</h1>{body}</main></body></html>'

    def issues(self, vp="width=device-width, initial-scale=1", body=""):
        return check.a11y_issues(self.PAGE.format(vp=vp, body=body))

    def test_zoom_blocking_viewport_fails(self):
        self.assertEqual(self.issues(), [])
        for vp in ("width=device-width, user-scalable=no", "width=device-width, maximum-scale=1", "user-scalable=0"):
            self.assertTrue(any("blocks zoom" in i for i in self.issues(vp)), vp)
        self.assertEqual(self.issues("width=device-width, maximum-scale=5"), [])

    def test_img_needs_width_and_height(self):
        self.assertEqual(self.issues(body='<img src="a.svg" alt="" width="48" height="48">'), [])
        self.assertTrue(any("width and height" in i for i in self.issues(body='<img src="a.svg" alt="" width="48">')))

    def test_motion_needs_the_reduced_motion_rule(self):
        self.assertEqual(check.motion_errors((ROOT / "site/style.css").read_text()), [])
        self.assertEqual(check.motion_errors("a{color:red}"), [])
        self.assertTrue(check.motion_errors(".x{animation:hop 1s infinite}"))
        self.assertTrue(check.motion_errors(".x{transition:transform .2s}@media (prefers-reduced-motion:reduce){*{animation:none!important}}"))
        self.assertEqual(check.motion_errors(".x{transition:transform .2s}@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}"), [])

    def test_every_built_page_passes_the_added_checks(self):
        for f in (ROOT / "site").rglob("*.html"):
            bad = [i for i in check.a11y_issues(f.read_text()) if "blocks zoom" in i or "width and height" in i]
            self.assertEqual(bad, [], f.name)


if __name__ == "__main__":
    unittest.main()
