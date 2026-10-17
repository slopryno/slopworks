"""Trial's tests for the four new hires, org groups, avatar contrast, and onboarding. Written before the code."""
import json, re, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check, build, avatars  # noqa: E402

HIRES = ["Scoutmaster", "Critic", "Advocate", "Librarian"]


def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= .03928 else ((x + .055) / 1.055) ** 2.4 for x in c]
    return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]


class Hires(unittest.TestCase):
    def test_files_bios_avatars(self):
        names = [n for n, *_ in build.team()]
        for h in HIRES:
            self.assertIn(h, names)
            self.assertTrue(build.bio(h))
            f = ROOT / f"site/assets/avatars/{h.lower()}.svg"
            self.assertTrue(f.exists())
            self.assertLess(f.stat().st_size, 3000)

    def test_roles_known_to_schemas_and_gate(self):
        enum = json.loads((ROOT / "data/schema/chat.schema.json").read_text())["items"]["properties"]["from"]["enum"]
        for h in HIRES:
            self.assertIn(h, enum)
        self.assertEqual(check._role("Librarian"), "Librarian")

    def test_unique_colors_and_eye_contrast(self):
        cols = [v[0] for v in avatars.ROLES.values()]
        self.assertEqual(len(cols), len(set(cols)))
        for n, v in avatars.ROLES.items():
            ratio = (lum(v[0]) + .05) / (lum("#1b1f24") + .05)
            self.assertGreaterEqual(ratio, 3.0, n)

    def test_unique_silhouettes(self):
        specs = [(v[1], v[2]) for v in avatars.ROLES.values()]
        self.assertEqual(len(specs), len(set(specs)))


class Groups(unittest.TestCase):
    def test_team_page_groups(self):
        html = build.build()["team/index.html"]
        for g in ["Leadership and Strategy", "Research and Intelligence", "Architecture and Development", "Quality and Governance", "Operations and Measurement"]:
            self.assertIn(g, html)
        self.assertIn("avatars/critic.svg", html)


class Onboarding(unittest.TestCase):
    def test_threads_and_checklist(self):
        chat = json.loads((ROOT / "data/chat.json").read_text())
        for h in HIRES:
            roots = [c for c in chat if c["to"] == h and c["from"] == "Coordinator" and not c.get("reply_to")]
            self.assertTrue(roots, h)
            replies = [c for c in chat if c.get("reply_to") == roots[0]["id"]]
            self.assertTrue(any(c["from"] == h for c in replies), h)
        self.assertTrue((ROOT / "docs/onboarding.md").exists())


if __name__ == "__main__":
    unittest.main()


class Offboarding(unittest.TestCase):
    SCHED = {"research": [{"day": "Monday", "roles": [{"role": "Critic", "focus": "x"}]}]}

    def test_docs(self):
        for f in ("docs/onboarding.md", "docs/offboarding.md"):
            self.assertTrue((ROOT / f).exists())
        self.assertIn("alumni", (ROOT / "docs/offboarding.md").read_text())

    def test_no_active_references(self):
        gone = [{"role": "Critic", "date": "2026-11-01", "reason": "merged", "successor": "Coordinator"}]
        self.assertTrue(check.alumni_errors(gone, self.SCHED, active_bots=["critic"]))  # still in rotation and bots/
        self.assertTrue(check.alumni_errors(gone, {"research": []}, active_bots=["critic"]))
        self.assertEqual(check.alumni_errors(gone, {"research": []}, active_bots=[]), [])
        self.assertIn("alumni", check.DATA_FILES)
