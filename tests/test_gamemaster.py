"""Trial's tests for the Game Master hire (i33), following docs/onboarding.md and the Comms pattern."""
import json, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check, build, avatars  # noqa: E402

load = lambda n: json.loads((ROOT / f"data/{n}.json").read_text())


class GameMasterHire(unittest.TestCase):
    def test_bot_file(self):
        t = (ROOT / "bots/gamemaster.md").read_text()
        for k in ("**Role:**", "**Owns:**", "**Bio:**", "**Can:**", "**Can't:**", "**Handoff:**", "**Research questions:**", "2 rounds"):
            self.assertIn(k, t)
        self.assertIn("Never awards XP", t)
        self.assertIn("Can't:** Award, approve, or reverse XP", t)
        self.assertIn("Critic for a challenge", t)
        self.assertIn("final say on the rules", t)
        self.assertIn("I never award XP", t)
        self.assertIn("played by one daily routine", build.build()["team/index.html"])  # said once in the Team lede (V3)

    def test_team_page_group_bio_avatar(self):
        self.assertIn("Gamemaster", [n for n, *_ in build.team()])
        self.assertIn("Gamemaster", dict(build.GROUPS)["Operations and Measurement"])
        html = build.build()["team/index.html"]
        self.assertIn("avatars/gamemaster.svg", html)
        self.assertIn("I own the progression rules", build.build()["team/gamemaster/index.html"])  # bio on the sheet (trading cards, Oct 20)
        f = ROOT / "site/assets/avatars/gamemaster.svg"
        self.assertLess(f.stat().st_size, 3000)
        self.assertIn("prefers-reduced-motion", f.read_text())
        colors = [c for c, *_ in avatars.ROLES.values()]
        self.assertEqual(colors.count(avatars.ROLES["gamemaster"][0]), 1)

    def test_enums_and_rotation(self):
        for s in ("chat", "ideas", "research", "standup", "updates", "issues", "aars"):
            self.assertIn('"Gamemaster"', (ROOT / f"data/schema/{s}.schema.json").read_text(), s)
        fri = [d for d in load("schedule")["research"] if d["day"] == "Friday"][0]
        self.assertIn("Gamemaster", [r["role"] for r in fri["roles"]])
        self.assertLessEqual(len(fri["roles"]), 3)
        self.assertEqual(check._role("Gamemaster"), "Gamemaster")

    def test_ceo_decision_and_onboarding_thread(self):
        i = {x["id"]: x for x in load("ideas")}["i33"]
        self.assertEqual((i["source"], i["decided_by"]), ("ceo", "CEO"))
        self.assertIn(i["state"], ("yes", "shipped"))  # i43: closed as shipped once the hire merged (aar-2026-10-18-stale-ideas)
        self.assertIn("5:57 PM ET", i["reason"])
        chat = load("chat")
        root = [c for c in chat if c["from"] == "Coordinator" and c["to"] == "Gamemaster" and not c.get("reply_to")][0]
        self.assertTrue(root["text"].startswith("Onboarding run: welcome, Game Master"))
        who = {c["from"] for c in chat if c.get("reply_to") == root["id"]}
        self.assertTrue({"Lens", "Trial", "Shield", "Critic", "Comms", "Gamemaster"} <= who)


if __name__ == "__main__":
    unittest.main()
