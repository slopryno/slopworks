"""Trial's tests for scripts/check.py. Written before the checks; run: python3 -m unittest discover tests"""
import json, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check  # noqa: E402

ENTRY = {"id": "1", "date": "2026-10-01", "added": "2026-10-15", "added_by": "Scout",
         "status": "confirmed", "area": "app", "title": "T", "summary": "S",
         "source": "https://x.com/bot/status/1"}


class Schema(unittest.TestCase):
    def test_valid_entry_passes(self):
        self.assertEqual(check.validate([ENTRY], check.load_schema("updates")), [])

    def test_missing_source_fails(self):
        e = dict(ENTRY); del e["source"]
        self.assertTrue(check.validate([e], check.load_schema("updates")))

    def test_bad_status_fails(self):
        e = dict(ENTRY, status="maybe")
        self.assertTrue(check.validate([e], check.load_schema("updates")))

    def test_extra_field_fails(self):
        e = dict(ENTRY, author="someone")
        self.assertTrue(check.validate([e], check.load_schema("updates")))

    def test_duplicate_ids(self):
        self.assertTrue(check.duplicate_ids([ENTRY, dict(ENTRY)]))
        self.assertFalse(check.duplicate_ids([ENTRY, dict(ENTRY, id="2")]))


class Links(unittest.TestCase):
    def test_https_and_allowed_host(self):
        self.assertFalse(check.bad_source("https://x.com/i/status/123"))
        self.assertTrue(check.bad_source("http://x.com/i/status/123"))
        self.assertTrue(check.bad_source("https://x.com/i/status/123?s=20"))
        self.assertTrue(check.bad_source("https://evil.example/download.exe"))


class Secrets(unittest.TestCase):
    def test_finds_tokens(self):
        for s in ["ghp_" + "a" * 36, "AKIA" + "B" * 16, "-----BEGIN " + "RSA PRIVATE KEY", "pass" + "word = hunter2hunter2xx"]:
            self.assertTrue(check.secret_hits(s), s)

    def test_clean_text(self):
        self.assertFalse(check.secret_hits("Grok Bot can now send voice notes."))


class PII(unittest.TestCase):
    def test_allowlisted(self):
        self.assertFalse(check.pii_hits("Mail slopryno+corrections@mail.grokbot.com or see @bot https://x.com/poteto/status/1"))

    def test_regular_handle_email_phone(self):
        self.assertTrue(check.pii_hits("thanks @someuser"))
        self.assertTrue(check.pii_hits("mail me at jane@example.com"))
        self.assertTrue(check.pii_hits("call 555-123-4567"))
        self.assertTrue(check.pii_hits("https://x.com/someuser/status/1"))
        self.assertTrue(check.pii_hits("slopryno@mail.grokbot.com"))

    def test_view_transition_at_rule_is_not_a_handle(self):
        css = "@media(prefers-reduced-motion:no-preference){@view-transition{navigation:auto}}"
        self.assertEqual(check.pii_hits(css), [])
        self.assertTrue(check.pii_hits("see @view for the write-up"))


class Files(unittest.TestCase):
    def test_blocked(self):
        for p in [".env", "a/.env.local", "k.pem", "id_rsa", "cookies.txt", "x/credentials.json"]:
            self.assertTrue(check.blocked_file(p), p)
        self.assertFalse(check.blocked_file("site/index.html"))


class A11y(unittest.TestCase):
    GOOD = '<!doctype html><html lang="en"><head><title>x</title><meta name="viewport" content="width=device-width"></head><body><main><h1>x</h1><img src="a.png" alt="a" width="48" height="48"></main></body></html>'

    def test_good(self):
        self.assertEqual(check.a11y_issues(self.GOOD), [])

    def test_problems(self):
        self.assertTrue(check.a11y_issues(self.GOOD.replace(' lang="en"', "")))
        self.assertTrue(check.a11y_issues(self.GOOD.replace(' alt="a"', "")))
        self.assertTrue(check.a11y_issues(self.GOOD.replace("<h1>x</h1>", "")))
        self.assertTrue(check.a11y_issues(self.GOOD.replace("</main>", '<script src="https://cdn.example/x.js"></script></main>')))


class ReviewGate(unittest.TestCase):
    def test_required_roles(self):
        self.assertEqual(check.required_roles(["data/updates.json"]), {"Lens"})
        self.assertEqual(check.required_roles(["site/style.css"]), {"Lens", "Trial"})
        self.assertEqual(check.required_roles(["bots/polish.md"]), {"Lens", "Coordinator"})
        self.assertEqual(check.required_roles([".github/workflows/ci.yml"]), {"Shield", "Atlas"})
        self.assertEqual(check.required_roles(["data/schema/allowed_handles.json"]), {"Shield", "Atlas"})

    def test_gate(self):
        c = [{"body": "Sign-off: Lens\nChecked: sources."}]
        self.assertEqual(check.review_gate(["data/x.json"], "Maker: Scout", c), [])
        self.assertTrue(check.review_gate(["data/x.json"], "Maker: Lens", c))  # self-approval
        self.assertTrue(check.review_gate(["data/x.json"], "", c))  # no maker
        self.assertTrue(check.review_gate(["site/a.css"], "Maker: Forge", c))  # missing Trial

    def test_outsider_signoff_ignored(self):
        c = [{"body": "Sign-off: Lens", "author_association": "NONE"}]
        self.assertTrue(check.review_gate(["data/x.json"], "Maker: Scout", c))
        c = [{"body": "Sign-off: Lens", "author_association": "OWNER"}]
        self.assertEqual(check.review_gate(["data/x.json"], "Maker: Scout", c), [])

    def test_blocking_comment_wins(self):
        c = [{"body": "Sign-off: Lens"}, {"body": "Block: Lens\nsource is dead"}]
        self.assertTrue(check.review_gate(["data/x.json"], "Maker: Scout", c))

    def test_critic_blocker_holds_until_cleared(self):
        ok = [{"body": "Sign-off: Lens"}]
        held = ok + [{"body": "Verdict: Critic (before)\nBlock: Critic\nbroken link"}]
        self.assertIn("Critic blocked this PR (BLOCKER); a later 'Sign-off: Critic' clears it",
                      check.review_gate(["data/x.json"], "Maker: Scout", held))
        self.assertEqual(check.review_gate(["data/x.json"], "Maker: Scout", held + [{"body": "Sign-off: Critic\nfixed"}]), [])
        self.assertEqual(check.review_gate(["data/x.json"], "Maker: Scout", ok + [{"body": "Verdict: Critic\nSIGNIFICANT: x"}]), [])



    def _verdicts(self, maker="Forge", flag="none", share="70%", skip=()):
        rows = []
        for r in check.TEAM_ROLES:
            if r == maker or r in skip:
                continue
            rows.append({"body": (
                f"Whole-screen verdict: {r} — opened 1280, 1440, 1920, 390; "
                f"content uses {share} of the 1920 viewport; leftover even side margin; Flag: {flag}"
            )})
        return rows

    def test_team_roles_match_bot_files(self):
        bots = {f.stem.capitalize() for f in (Path(__file__).resolve().parent.parent / "bots").glob("*.md")}
        self.assertEqual(set(check.TEAM_ROLES), bots)

    def test_data_pr_does_not_need_screenshot_verdicts(self):
        c = [{"body": "Sign-off: Lens\nChecked: sources."}]
        self.assertEqual(check.review_gate(["data/x.json"], "Maker: Scout", c), [])

    def test_visible_css_pr_needs_every_role_except_the_maker(self):
        sign = [{"body": "Sign-off: Lens\nok"}, {"body": "Sign-off: Trial\nok"}]
        errs = check.review_gate(["site/style.css"], "Maker: Forge", sign)
        # Lens and Trial are signed; whole-screen verdicts are still missing.
        missing = [e for e in errs if e.startswith("missing whole-screen verdict from ")]
        need = [r for r in check.TEAM_ROLES if r != "Forge"]
        self.assertEqual(sorted(e.rsplit(" from ", 1)[1].split(" (")[0] for e in missing), sorted(need))
        self.assertFalse(any("Forge" in e and "missing whole-screen verdict" in e for e in errs))

    def test_visible_css_pr_passes_with_verdicts_and_signoffs(self):
        sign = [{"body": "Sign-off: Lens\nok"}, {"body": "Sign-off: Trial\nok"}]
        comments = sign + self._verdicts("Forge")
        self.assertEqual(check.review_gate(["site/style.css"], "Maker: Forge", comments), [])

    def test_verdict_in_the_same_comment_as_a_signoff_counts(self):
        comments = self._verdicts("Forge")
        # attach Lens sign-off + verdict in one body
        comments = [c for c in comments if "Lens" not in c["body"][:40]]
        comments.append({"body": (
            "Sign-off: Lens\nChecked.\n"
            "Whole-screen verdict: Lens — opened 1280, 1440, 1920, 390; content uses 70% of the 1920 viewport; Flag: none"
        )})
        comments.append({"body": "Sign-off: Trial\nok"})
        self.assertEqual(check.review_gate(["scripts/deck.css"], "Maker: Forge", comments), [])

    def test_incomplete_verdict_is_rejected(self):
        sign = [{"body": "Sign-off: Lens\nok"}, {"body": "Sign-off: Trial\nok"}]
        comments = sign + self._verdicts("Forge", skip=("Polish",))
        comments.append({"body": "Whole-screen verdict: Polish — looks fine. Flag: none"})
        errs = check.review_gate(["site/style.css"], "Maker: Forge", comments)
        self.assertTrue(any("Polish's whole-screen verdict must name 1280" in e for e in errs))
        self.assertTrue(any("percentage" in e for e in errs))

    def test_large_empty_space_flag_is_a_blocker(self):
        sign = [{"body": "Sign-off: Lens\nok"}, {"body": "Sign-off: Trial\nok"}]
        comments = sign + self._verdicts("Forge", skip=("Critic",))
        comments.append({"body": (
            "Whole-screen verdict: Critic — opened 1280, 1440, 1920, 390; "
            "content uses 22% of the 1920 viewport; large side gutters; Flag: large empty space"
        )})
        errs = check.review_gate(["scripts/deck.css"], "Maker: Forge", comments)
        self.assertIn("Critic flagged large empty space (BLOCKER)", errs)
        # a later Flag: none from Critic clears it
        comments.append({"body": (
            "Whole-screen verdict: Critic — opened 1280, 1440, 1920, 390; "
            "content uses 70% of the 1920 viewport; leftover even margin; Flag: none"
        )})
        self.assertEqual(check.review_gate(["scripts/deck.css"], "Maker: Forge", comments), [])

    def test_outsider_verdict_is_ignored(self):
        sign = [{"body": "Sign-off: Lens\nok"}, {"body": "Sign-off: Trial\nok"}]
        comments = sign + self._verdicts("Forge", skip=("Polish",))
        comments.append({
            "body": (
                "Whole-screen verdict: Polish — opened 1280, 1440, 1920, 390; "
                "content uses 70% of the 1920 viewport; Flag: none"
            ),
            "author_association": "NONE",
        })
        errs = check.review_gate(["site/style.css"], "Maker: Forge", comments)
        self.assertTrue(any("missing whole-screen verdict from Polish" in e for e in errs))

    def test_design_branch_with_html_only_still_needs_verdicts(self):
        c = [{"body": "Sign-off: Trial\nok"}, {"body": "Sign-off: Lens\nok"}]
        errs = check.review_gate(["site/team/index.html"], "Maker: Forge", c, branch="bot/design-deck-grid")
        self.assertTrue(any("missing whole-screen verdict from Polish" in e for e in errs))
        self.assertEqual(check.review_gate(["site/team/index.html"], "Maker: Forge", c, branch="bot/data-morning"), [])

    def test_maker_verdict_does_not_count(self):
        sign = [{"body": "Sign-off: Lens\nok"}, {"body": "Sign-off: Trial\nok"}]
        comments = sign + self._verdicts("Forge")
        comments.append({"body": (
            "Whole-screen verdict: Forge — opened 1280, 1440, 1920, 390; "
            "content uses 70% of the 1920 viewport; Flag: none"
        )})
        errs = check.review_gate(["site/style.css"], "Maker: Forge", comments)
        self.assertTrue(any("Forge made this PR, so their whole-screen verdict does not count" in e for e in errs))


class GuardrailGate(unittest.TestCase):
    def test_loosening(self):
        self.assertTrue(check.loosening("data/schema/allowed_handles.json", added=['"someone",'], removed=[]))
        self.assertTrue(check.loosening("scripts/patterns.json", added=[], removed=['"jwt": "x",']))
        self.assertTrue(check.loosening(".github/workflows/ci.yml", added=["  contents: write"], removed=[]))
        self.assertTrue(check.loosening("scripts/check.py", added=[], removed=["    return hits"]))

    def test_tightening_ok(self):
        self.assertFalse(check.loosening("scripts/patterns.json", added=['"new": "y",'], removed=[]))
        self.assertFalse(check.loosening("data/updates.json", added=["x"], removed=["y"]))
        self.assertFalse(check.loosening("data/schema/allowed_handles.json", added=[], removed=['"grok",']))


class DraftFlow(unittest.TestCase):
    """Bots open PRs as drafts, sign off, then mark ready; ready_for_review re-runs CI with the sign-offs present."""
    def test_draft_defers_review_gate(self):
        self.assertTrue(check.review_deferred({"draft": True}))
        self.assertFalse(check.review_deferred({"draft": False}))
        self.assertFalse(check.review_deferred({}))

    def test_ci_reruns_on_ready_for_review(self):
        ci = (Path(__file__).resolve().parent.parent / ".github/workflows/ci.yml").read_text()
        self.assertIn("ready_for_review", ci)
        for t in ("opened", "synchronize", "reopened"):
            self.assertIn(t, ci)  # defaults kept, so nothing stops running

    def test_daily_data_pr_needs_verify_and_trial_only(self):
        self.assertEqual(check.required_roles(["data/updates.json", "site/index.html", "site/feed.json"]), {"Lens", "Trial"})


if __name__ == "__main__":
    unittest.main()


class CoAuthorTrailers(unittest.TestCase):
    def _banned_line(self):
        # Build the banned trailer from the same parts the check uses, so this file never stores the full literal.
        name = "Claude" + " " + "Opus" + " " + "5.5"
        mail = "noreply@" + "anthropic.com"
        return f"Co-Authored-By: {name} <{mail}>"

    def _personal_line(self):
        name = "Ryan" + " " + "Willis"
        mail = "ryan.willis.it" + "@" + "gmail.com"
        return f"Co-authored-by: {name} <{mail}>"

    def test_detects_anthropic_and_personal_trailers(self):
        self.assertTrue(check.coauthor_trailer_hits("msg\n\n" + self._banned_line() + "\n"))
        self.assertTrue(check.coauthor_trailer_hits("msg\n\n" + self._personal_line() + "\n"))

    def test_other_trailers_ok(self):
        self.assertFalse(check.coauthor_trailer_hits("msg\n\nSigned-off-by: Lens <lens@example.com>\n"))
        self.assertFalse(check.coauthor_trailer_hits("discussing Co-authored-by policy in a paragraph\n"))

    def test_scrub_removes_blocked_only(self):
        raw = "title\n\nbody\n\n" + self._banned_line() + "\n" + self._personal_line() + "\nCo-authored-by: Other Bot <other@example.com>\n"
        scrubbed = check.scrub_coauthor_trailers(raw)
        self.assertNotIn("anthropic.com", scrubbed)
        self.assertNotIn("willis", scrubbed.lower())
        self.assertIn("Other Bot", scrubbed)

    def test_text_errors_name_the_where(self):
        errs = check.coauthor_text_errors("x\n" + self._banned_line() + "\n", "PR 1 body")
        self.assertEqual(len(errs), 1)
        self.assertIn("PR 1 body", errs[0])
