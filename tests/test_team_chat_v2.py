"""Trial's tests for avatars, the leadership grid, threaded Team chat, and CEO pitches."""
import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check, build  # noqa: E402

C = lambda i, **k: dict({"id": i, "date": "2026-10-17", "from": "Scout", "to": "Verify", "text": "t"}, **k)
CEO = {"id": "i9", "date": "2026-10-17", "by": "CEO", "source": "ceo", "problem": "P", "helps": "H", "effort": "M",
       "builder": "Forge", "state": "pitched", "comments": []}
sup = lambda r: {"date": "2026-10-18", "role": r, "stance": "support", "text": "ok"}


class Avatars(unittest.TestCase):
    def test_every_role_has_small_avatar(self):
        for name in [n for n, *_ in build.team()] + ["Pixel", "Core"]:
            p = ROOT / f"site/assets/avatars/{name.lower()}.svg"
            self.assertTrue(p.exists(), name)
            self.assertLess(p.stat().st_size, 60_000)
            self.assertNotIn("<script", p.read_text())

    def test_v2_style(self):
        for f in (ROOT / "site/assets/avatars").glob("*.svg"):
            t = f.read_text()
            self.assertLess(len(t.encode()), 3000, f.name)
            self.assertIn("prefers-reduced-motion", t, f.name)  # static fallback
            self.assertIn("@keyframes", t, f.name)  # idle + blink
            self.assertNotIn('<rect width="100" height="100"', t, f.name)  # no tile background
            self.assertNotIn("<text", t, f.name)

    def test_avatar_changes_need_polish_and_shield(self):
        self.assertEqual(check.required_roles(["site/assets/avatars/lens.svg"]), {"Polish", "Shield"})

    def test_aliases_map_to_avatars(self):
        self.assertEqual(build.avatar_of("Verify"), "lens")
        self.assertEqual(build.avatar_of("Privacy"), "shield")
        self.assertEqual(build.avatar_of("CEO"), "ceo")


class Team(unittest.TestCase):
    def test_grid(self):
        html = build.build()["team/index.html"]
        self.assertIn("Built and designed by Grok Bots", html)
        self.assertIn('class="deck"', html)  # the trading-card grid (Oct 20)
        self.assertIn("avatars/coordinator.svg", html)
        self.assertNotIn("Recent wins", html)  # page budget (Ryno, Oct 20 7:27 AM ET): wins live on each sheet
        self.assertIn(">Character sheet</a>", html)

    def test_every_win_is_on_its_sheet(self):
        files, stems = build.build(), {n: f[:-3] for n, _, _, _, f in build.team()}
        wins = build.load("wins")
        for n in stems:  # the 3 wins Team used to list per role are on the sheet's Verified work
            for w in [x for x in wins if x["role"] == n][:3]:
                self.assertIn(w["pr"], files[f"team/{stems[n]}/index.html"], (n, w["pr"]))

    def test_every_bot_has_bio(self):
        for n, *_ in build.team():
            self.assertTrue(build.bio(n), n)


class Threads(unittest.TestCase):
    def test_reply_rules(self):
        self.assertEqual(check.chat_errors([C("a"), C("b", reply_to="a")]), [])
        self.assertTrue(check.chat_errors([C("b", reply_to="zz")]))
        self.assertTrue(check.chat_errors([C("a", reply_to="a")]))
        self.assertTrue(check.chat_errors([C("a"), C("b", reply_to="a"), C("c", reply_to="b")]))  # flat threads
        self.assertTrue(check.chat_errors([C("a", time="25:00")]))
        self.assertTrue(check.chat_errors([C("a", idea="nope")], ideas=[]))

    def test_schema_allows_thread_fields(self):
        self.assertEqual(check.validate([C("a", reply_to="x", time="09:14", idea="i1")], check.load_schema("chat")), [])

    def test_page(self):
        html = build.build()["chat/index.html"]
        self.assertNotIn("<script", html)
        self.assertIn("avatars/", html)


class CeoPitches(unittest.TestCase):
    def test_ceo_pitch_logged(self):
        self.assertEqual(check.idea_errors([CEO]), [])
        self.assertTrue(check.idea_errors([dict(CEO, source="team")]))

    def test_team_only_advises(self):
        adv = dict(CEO, state="advised", comments=[sup("Atlas")], recommendation="smaller", pros="a", cons="b", target_sprint="2026-W43")
        self.assertEqual(check.idea_errors([adv]), [])
        self.assertTrue(check.idea_errors([dict(adv, recommendation=None)]))
        no = dict(adv, state="no", decided="2026-10-19", decided_by="Coordinator", reason="x")
        self.assertTrue(check.idea_errors([no]))
        self.assertEqual(check.idea_errors([dict(no, decided_by="CEO")]), [])
        self.assertTrue(check.idea_errors([dict(adv, state="vetoed", decided="2026-10-19", decided_by="Shield", reason="r")]))

    def test_unanimous_auto_yes(self):
        y = dict(CEO, state="yes", recommendation="yes", pros="a", cons="b", target_sprint="2026-W43",
                 decided="2026-10-19", decided_by="Coordinator", reason="unanimous")
        self.assertEqual(check.idea_errors([dict(y, comments=[sup("Atlas"), sup("Trial")])]), [])
        self.assertTrue(check.idea_errors([dict(y, comments=[sup("Atlas")])]))
        self.assertTrue(check.idea_errors([dict(y, comments=[sup("Atlas"), dict(sup("Trial"), stance="concern")])]))


if __name__ == "__main__":
    unittest.main()
