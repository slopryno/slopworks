"""Trial's tests for the Director of Strategy hire (i47), following docs/onboarding.md and the Game Master pattern."""
import json, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check, build, avatars  # noqa: E402

load = lambda n: json.loads((ROOT / f"data/{n}.json").read_text())


class StrategyHire(unittest.TestCase):
    def test_bot_file_and_limits(self):
        t = (ROOT / "bots/strategy.md").read_text()
        for k in ("**Role:**", "**Owns:**", "**Bio:**", "**Can:**", "**Can't:**", "**Handoff:**", "**Research questions:**", "2 rounds"):
            self.assertIn(k, t)
        self.assertIn("report progress from the records", t)
        self.assertIn("played by one daily routine", build.build()["team/index.html"])  # said once in the Team lede (V3)
        for limit in ("Run execution or the sprint (Coordinator does)", "Coordinator's scoring and a decision record",
                      "can't measure from real records", "the tempo limit or the no-visitor-input rule", "Post to X"):
            self.assertIn(limit, t)
        self.assertIn("Strategy on Sundays", t)

    def test_team_page_group_avatar(self):
        self.assertIn("Strategy", [n for n, *_ in build.team()])
        self.assertIn("Strategy", dict(build.GROUPS)["Leadership and Strategy"])
        html = build.build()["team/index.html"]
        self.assertIn("avatars/strategy.svg", html)
        f = ROOT / "site/assets/avatars/strategy.svg"
        self.assertLess(f.stat().st_size, 3000)
        self.assertIn("prefers-reduced-motion", f.read_text())
        colors = [c for c, *_ in avatars.ROLES.values()]
        self.assertEqual(colors.count(avatars.ROLES["strategy"][0]), 1)

    def test_enums_rotation_progression(self):
        for s in ("chat", "ideas", "research", "standup", "updates", "issues", "aars", "xp_ledger"):
            self.assertIn('"Strategy"', (ROOT / f"data/schema/{s}.schema.json").read_text(), s)
        sun = [d for d in load("schedule")["research"] if d["day"] == "Sunday"][0]
        self.assertIn("Strategy", [r["role"] for r in sun["roles"]])
        self.assertLessEqual(len(sun["roles"]), 3)
        self.assertEqual(check._role("Strategy"), "Strategy")
        self.assertIn("Strategy", json.dumps(load("progression")))

    def test_ceo_decision_and_onboarding_thread(self):
        i = {x["id"]: x for x in load("ideas")}["i47"]
        self.assertEqual((i["source"], i["decided_by"]), ("ceo", "CEO"))
        self.assertIn("11:00 PM ET", i["reason"])
        chat = load("chat")
        root = [c for c in chat if c["from"] == "Coordinator" and c["to"] == "Strategy" and not c.get("reply_to")][0]
        self.assertTrue(root["text"].startswith("Onboarding run: welcome, Director of Strategy"))
        who = {c["from"] for c in chat if c.get("reply_to") == root["id"]}
        self.assertTrue({"Lens", "Shield", "Critic", "Sketch", "Scoutmaster", "Strategy"} <= who)


if __name__ == "__main__":
    unittest.main()
