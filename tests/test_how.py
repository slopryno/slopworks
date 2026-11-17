"""Trial's tests for i48 (How this works) and i49 (tracker-first home), from the design huddle c359 to c366."""
import re, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build, check, tempo  # noqa: E402

FILES = build.build()


class HowThisWorks(unittest.TestCase):
    def test_glossary_terms_and_numbers_from_code(self):
        html = FILES["how/index.html"]
        for t in ("AAR", "Block", "Blast radius", "ceo-approved", "CI", "Maker", "needs-ceo", "Sign-off", "Tempo", "XP"):
            self.assertIn(f">{t}</dt>", html)
        self.assertIn(f"up to {tempo.LIMITS['normal']['prs_per_day']} PRs a day", html)
        self.assertIn(f"{tempo.LIMITS['slowed']['prs_per_day']} a day after", html)
        self.assertIn(f"until {tempo.CLEAN_NEEDED} clean PRs", html)
        for step in ("Scout", "Verify", "Privacy", "Build", "Review", "Publish"):
            self.assertIn(f"<strong>{step}</strong>", html)
        self.assertNotIn("<script", html)
        self.assertEqual(check.a11y_issues(html), [])

    def test_linked_without_a_new_header_item(self):
        self.assertEqual(len(build.TOP), 4)
        self.assertIn('href="../how/"', FILES["hood/index.html"])
        self.assertIn('href="how/"', FILES["index.html"])
        self.assertNotIn('href="how/"', re.search(r'<nav class="tabs" aria-label="Main">.*?</nav>', FILES["index.html"], re.S).group(0))

    def test_footer_lists_the_five_tabs_and_each_one_resolves(self):
        """The sitelist matches the five tabs (Home, Tracker, Team, Receipts, More), and every href is a built page."""
        import posixpath
        tabs = list(build.TABS)
        self.assertEqual([t for _, t in tabs], ["Home", "Tracker", "Team", "Receipts", "More"])
        for rel, html in FILES.items():
            if not rel.endswith(".html"):
                continue
            foot = re.search(r'<nav class="sitelist" aria-label="Sections"><ul>(.*?)</ul></nav>', html, re.S)
            self.assertIsNotNone(foot, rel)
            links = re.findall(r'<a href="([^"]*)">([^<]*)</a>', foot.group(1))
            up = "../" * rel.count("/")
            expected = [(up + s, title) for s, title in tabs]
            self.assertEqual(links, expected, rel)
            for href, _title in links:
                target = posixpath.normpath(posixpath.join(posixpath.dirname(rel), href)) if href else "index.html"
                if target.endswith("/") or target == ".":
                    target = (target.rstrip("/") + "/index.html") if target != "." else "index.html"
                elif not target.endswith(".html"):
                    target += "/index.html"
                self.assertIn(target, FILES, f"{rel} footer {href!r} -> missing {target}")

    def test_home_tracker_first_team_second(self):
        h = FILES["index.html"]
        order = [h.index(f'id="{k}-t"') for k in ("tracker", "team", "feat", "act")]
        self.assertEqual(order, sorted(order))
        # Polish UX depth: verified lead, then primary CTA to the tracker (Advocate), then section order.
        self.assertLess(h.index('id="verified"'), h.index('id="tracker-t"'))
        self.assertLess(h.index('href="updates/">What\'s new in Grok Bot'), h.index('id="tracker-t"'))


if __name__ == "__main__":
    unittest.main()
