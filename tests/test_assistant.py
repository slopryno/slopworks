"""Trial's tests for the Executive Assistant (Ryno 2026-10-19 5:26 and 5:28 PM ET): only the EA applies ceo-approved,
only on Ryno's explicit yes for that PR, quoted on the PR, and every use is logged."""
import json, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check, build  # noqa: E402

YES = ('Executive Assistant applying ceo-approved on Ryno\'s explicit instruction.\n\n'
       '- Ryno (CEO), Mon 2026-10-19, 5:16 PM ET, in Slopbot chat: "Let #108 through and ship the rest tonight."')
REC = {"pr": 120, "quote": "Yes, let #120 through.", "said_at": "2026-10-20T09:00-04:00", "where": "Slopbot chat",
       "applied_by": "Executive Assistant", "applied_at": "2026-10-20T09:05-04:00",
       "evidence": "https://github.com/slopryno/slopworks/pull/120#issuecomment-1", "authority": "Ryno (CEO), 5:28 PM ET"}


class CeoLabel(unittest.TestCase):
    def test_no_label_no_check(self):
        self.assertEqual(check.ceo_label_errors(120, ["needs-ceo"], [], []), [])

    def test_label_without_quote_or_record_fails(self):
        self.assertTrue(check.ceo_label_errors(120, ["ceo-approved"], [{"body": "Sign-off: Lens\nok"}], []))

    def test_ea_comment_needs_prefix_time_and_quote(self):
        self.assertEqual(check.ceo_label_errors(120, ["ceo-approved"], [{"body": YES}], []), [])
        for bad in (YES.replace("Executive Assistant applying", "Applying"), YES.replace("5:16 PM ET", "today"),
                    YES.replace('"Let #108 through and ship the rest tonight."', "let it through")):
            self.assertTrue(check.ceo_label_errors(120, ["ceo-approved"], [{"body": bad}], []), bad[:40])

    def test_record_for_that_pr_passes_and_another_pr_does_not(self):
        self.assertEqual(check.ceo_label_errors(120, ["ceo-approved"], [], [REC]), [])
        self.assertTrue(check.ceo_label_errors(121, ["ceo-approved"], [], [REC]))
        self.assertTrue(check.ceo_label_errors(120, ["ceo-approved"], [], [dict(REC, quote=None)]))

    def test_not_retroactive(self):
        self.assertEqual(check.ceo_label_errors(14, ["ceo-approved"], [], []), [])
        self.assertEqual(check.ceo_label_errors(108, ["ceo-approved"], [], []), [])
        self.assertTrue(check.ceo_label_errors(check.EA_RULE_FROM_PR, ["ceo-approved"], [], []))

    def test_api_failure_fails_closed(self):
        import os, subprocess
        env = dict(os.environ, PR="999999", REPO="slopryno/slopworks", GH_TOKEN="x", SHA="0")
        env["HTTPS_PROXY"] = env["https_proxy"] = "http://127.0.0.1:9"  # no network answer
        r = subprocess.run([sys.executable, "scripts/check.py", "ceo-label"], cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("could not verify", r.stdout)


class DecisionLog(unittest.TestCase):
    def test_repo_log_is_valid_and_backfilled(self):
        self.assertEqual(check.ceo_decision_errors(), [])
        recs = {r["pr"]: r for r in json.loads((ROOT / "data/ceo_decisions.json").read_text())}
        self.assertEqual(recs[108]["quote"], "Let #108 through and ship the rest tonight.")
        self.assertEqual((recs[108]["said_at"], recs[108]["applied_by"], recs[108]["where"]),
                         ("2026-10-19T17:16-04:00", "Executive Assistant", "Slopbot chat"))
        self.assertIn("EA applies ceo-approved only after my explicit yes in chat, quoted on the PR", recs[108]["authority"])
        self.assertEqual(recs[14]["applied_by"], "Ryno (CEO)")

    def _errs(self, recs, log="[#120](x)"):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "data").mkdir(); (Path(d) / "bots").mkdir()
            (Path(d) / "data/ceo_decisions.json").write_text(json.dumps(recs))
            (Path(d) / "bots/assistant.md").write_text(log)
            return check.ceo_decision_errors(Path(d))

    def test_ea_record_rules(self):
        self.assertEqual(self._errs([REC]), [])
        self.assertTrue(self._errs([REC], log=""))  # every use is logged in bots/assistant.md
        self.assertTrue(self._errs([dict(REC, quote=None)]))
        self.assertTrue(self._errs([dict(REC, said_at="2026-10-20T09:10-04:00")]))  # label before the yes
        self.assertTrue(self._errs([dict(REC, applied_at="2026-10-19T12:00-04:00", said_at="2026-10-19T11:00-04:00")]))
        self.assertTrue(self._errs([REC, REC]))
        self.assertTrue(self._errs([dict(REC, evidence="https://github.com/slopryno/slopworks/pull/121")]))
        self.assertTrue(self._errs([dict(REC, applied_by="Coordinator")]))

    def test_add_only(self):
        self.assertFalse(check.loosening("data/ceo_decisions.json", ['  {"pr": 120}'], []))
        self.assertTrue(check.loosening("data/ceo_decisions.json", [], ['  {"pr": 108}']))


class Role(unittest.TestCase):
    def test_bot_file_states_the_exact_limit(self):
        t = (ROOT / "bots/assistant.md").read_text()
        for k in ("**Role:**", "**Owns:**", "**Bio:**", "**Can:**", "**Can't:**", "**Handoff:**", "**Research questions:**", "2 rounds"):
            self.assertIn(k, t)
        for limit in ("EA applies ceo-approved only after my explicit yes in chat, quoted on the PR", "No yes, no label",
                      "safety, secrets and personal-data cases", "only role that may apply `ceo-approved`", "Post to X",
                      check.EA_PREFIX, "## Log of each use", "[#108](https://github.com/slopryno/slopworks/pull/108)"):
            self.assertIn(limit, t)

    def test_team_page_and_docs(self):
        self.assertIn("Assistant", dict(build.GROUPS)["Leadership and Strategy"])
        html = build.build()["team/index.html"]
        self.assertIn("avatars/assistant.svg", html)
        self.assertIn("Executive Assistant", build.build()["team/assistant/index.html"])  # the title is on the sheet since the trading cards (Oct 20)
        self.assertEqual(check._role("EA"), "Assistant")
        self.assertIn("only the [Executive Assistant](bots/assistant.md)", (ROOT / "README.md").read_text())
        self.assertIn("Only the Executive Assistant applies `ceo-approved`", (ROOT / "plans/direction.md").read_text())
        self.assertIn("team/assistant/index.html", json.loads((ROOT / "data/word_limits.json").read_text())["enforced_pages"])

    def test_workflow_runs_on_label_changes_with_read_only_token(self):
        w = (ROOT / ".github/workflows/ceo-label.yml").read_text()
        self.assertIn("labeled, unlabeled", w)
        self.assertIn("python3 scripts/check.py ceo-label", w)
        self.assertNotRegex(w, r":\s*write\b|write-all|pull_request_target")


if __name__ == "__main__":
    unittest.main()
