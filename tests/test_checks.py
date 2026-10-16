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
        for s in ["ghp_" + "a" * 36, "AKIA" + "B" * 16, "-----BEGIN RSA PRIVATE KEY", "password = hunter2hunter2xx"]:
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


class Files(unittest.TestCase):
    def test_blocked(self):
        for p in [".env", "a/.env.local", "k.pem", "id_rsa", "cookies.txt", "x/credentials.json"]:
            self.assertTrue(check.blocked_file(p), p)
        self.assertFalse(check.blocked_file("site/index.html"))


class A11y(unittest.TestCase):
    GOOD = '<!doctype html><html lang="en"><head><title>x</title><meta name="viewport" content="width=device-width"></head><body><main><h1>x</h1><img src="a.png" alt="a"></main></body></html>'

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

    def test_blocking_comment_wins(self):
        c = [{"body": "Sign-off: Lens"}, {"body": "Block: Lens\nsource is dead"}]
        self.assertTrue(check.review_gate(["data/x.json"], "Maker: Scout", c))


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


if __name__ == "__main__":
    unittest.main()
