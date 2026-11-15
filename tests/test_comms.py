"""Trial's tests for the Head of Comms hire (i28) and its decision rights (i29), following docs/onboarding.md."""
import json, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check, build, avatars  # noqa: E402

load = lambda n: json.loads((ROOT / f"data/{n}.json").read_text())


class CommsHire(unittest.TestCase):
    def test_bot_file(self):
        t = (ROOT / "bots/comms.md").read_text()
        for k in ("**Role:**", "**Owns:**", "**Bio:**", "**Can:**", "**Can't:**", "**Handoff:**", "**Research questions:**", "2 rounds"):
            self.assertIn(k, t)
        self.assertIn("Post to X or anywhere else", t)
        self.assertIn("only drafts posts, for Ryno", t)
        self.assertIn("final say", t)
        self.assertIn("Can't:** Post to X", t)

    def test_team_page_group_bio_avatar(self):
        self.assertIn("Comms", [n for n, *_ in build.team()])
        self.assertIn("Comms", dict(build.GROUPS)["Leadership and Strategy"])
        html = build.build()["team/index.html"]
        self.assertIn("avatars/comms.svg", html)
        self.assertIn("final call is mine but never a solo one", build.build()["team/comms/index.html"])  # bio on the sheet (trading cards, Oct 20)
        f = ROOT / "site/assets/avatars/comms.svg"
        self.assertLess(f.stat().st_size, 3000)
        self.assertIn("prefers-reduced-motion", f.read_text())
        self.assertIn("comms", avatars.ROLES)

    def test_enums_and_rotation(self):
        for s in ("chat", "ideas", "research", "standup", "updates", "issues", "aars"):
            self.assertIn('"Comms"', (ROOT / f"data/schema/{s}.schema.json").read_text(), s)
        thu = [d for d in load("schedule")["research"] if d["day"] == "Thursday"][0]
        self.assertIn("Comms", [r["role"] for r in thu["roles"]])
        self.assertLessEqual(len(thu["roles"]), 3)
        self.assertEqual(check._role("Comms"), "Comms")

    def test_ceo_decisions_and_onboarding_threads(self):
        ideas = {i["id"]: i for i in load("ideas")}
        for k, t in (("i28", "1:23 PM ET"), ("i29", "1:25 PM ET")):
            self.assertEqual((ideas[k]["source"], ideas[k]["decided_by"]), ("ceo", "CEO"))
            self.assertIn(ideas[k]["state"], ("yes", "shipped"))  # i43: closed as shipped once the hire merged (aar-2026-10-18-stale-ideas)
            self.assertIn(t, ideas[k]["reason"])
        chat = load("chat")
        root = [c for c in chat if c["from"] == "Coordinator" and c["to"] == "Comms" and not c.get("reply_to")][0]
        self.assertTrue(root["text"].startswith("Onboarding run"))
        who = {c["from"] for c in chat if c.get("reply_to") == root["id"]}
        self.assertTrue({"Polish", "Lens", "Shield", "Atlas", "Advocate", "Comms"} <= who)


if __name__ == "__main__":
    unittest.main()
