"""Trial's tests for the decision record, scoring, and gates. Written before the code."""
import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check, build  # noqa: E402

S = {"impact": 4, "evidence": 3, "fit": 5, "effort": 2, "risk": 2, "reversibility": 4}
I = {"id": "i1", "date": "2026-10-19", "by": "Polish", "problem": "P", "helps": "H", "effort": "S", "builder": "Pixel",
     "state": "yes", "comments": [], "decided": "2026-10-19", "decided_by": "Coordinator", "reason": "r",
     "scores": S, "librarian_checked": True, "acceptance_criteria": ["works on mobile"], "evidence": ["r1"]}


class Scoring(unittest.TestCase):
    def test_priority(self):
        self.assertEqual(check.priority(S), 15.0)  # (4*3*5)/(2*2)

    def test_yes_gates(self):
        self.assertEqual(check.idea_errors([I]), [])
        for bad in (dict(I, scores=None), dict(I, scores=dict(S, evidence=1)), dict(I, scores=dict(S, risk=5)),
                    dict(I, librarian_checked=False), dict(I, acceptance_criteria=[]), dict(I, scores=dict(S, impact=6))):
            self.assertTrue(check.idea_errors([bad]), bad)

    def test_security_overrides(self):
        c = [{"date": "2026-10-19", "role": "Shield", "stance": "oppose", "text": "leaks data"}]
        self.assertTrue(check.idea_errors([dict(I, comments=c)]))

    def test_critic_only_advises(self):
        self.assertEqual(check.idea_errors([dict(I, challenge={"by": "Critic", "recommendation": "reject", "summary": "s"})]), [])
        self.assertTrue(check.idea_errors([dict(I, challenge={"by": "Lens", "recommendation": "reject", "summary": "s"})]))

    def test_shipped_needs_trial_and_experiment_when_uncertain(self):
        sh = dict(I, state="shipped", shipped="area filters", acceptance_verified_by="Trial", experiment="e", experiment_result="pass")
        self.assertEqual(check.idea_errors([sh]), [])
        self.assertTrue(check.idea_errors([dict(sh, acceptance_verified_by="Forge")]))
        self.assertTrue(check.idea_errors([dict(sh, experiment_result=None)]))  # evidence 3 = uncertain
        self.assertEqual(check.idea_errors([dict(sh, experiment_result=None, scores=dict(S, evidence=4))]), [])

    def test_schema(self):
        rec = dict(I, objections=["o"], outcome_met=None, stale=False, fresh_until="2027-01-01",
                   challenge={"by": "Critic", "recommendation": "proceed", "summary": "s"})
        self.assertEqual(check.validate([rec], check.load_schema("ideas")), [])


class ResearchRender(unittest.TestCase):
    def test_build_renders_standard_reports(self):
        html = build.build()["chat/index.html"]  # real data includes at least one report
        self.assertIn("Research", html)


class Cadence(unittest.TestCase):
    def test_weekly_cadence_on_schedule(self):
        page = build.build()["schedule/index.html"]
        for w in ("select the week", "challenge", "measure"):
            self.assertIn(w, page.lower())

    def test_research_questions_in_every_bot(self):
        for f in (ROOT / "bots").glob("*.md"):
            self.assertIn("**Research questions:**", f.read_text(), f.name)


if __name__ == "__main__":
    unittest.main()
