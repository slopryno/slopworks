"""Trial's tests for the Lessons archive rollover (sprint i31): nothing dropped, open reviews stay, every link resolves."""
import json, re, sys, unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import build  # noqa: E402
from test_timeline import resolve_all  # noqa: E402

AARS = json.loads((ROOT / "data/aars.json").read_text())


def lesson_pages(files):
    return {k: v for k, v in files.items() if k.startswith("lessons/") and k.endswith(".html")}


class LessonsArchive(unittest.TestCase):
    def test_today_every_review_is_on_exactly_one_page(self):
        files = build.build()  # the 14th review (Oct 18) rolled the oldest into the archive, as designed
        pages = lesson_pages(files)
        for a in AARS:
            self.assertEqual(sum(f'id="{a["id"]}"' in v for v in pages.values()), 1, a["id"])
            if a["status"] == "open" or a["date"] == max(x["date"] for x in AARS):
                self.assertIn(f'id="{a["id"]}"', pages["lessons/index.html"])

    def test_rollover_drops_nothing_and_keeps_links_working(self):
        with mock.patch.object(build, "CHAT_TARGET", 0.2):
            files = build.build()
        pages = lesson_pages(files)
        self.assertGreater(len(pages), 1, "a small target should roll older reviews into the archive")
        for a in AARS:
            self.assertEqual(sum(f'id="{a["id"]}"' in v for v in pages.values()), 1, a["id"])
            if a["status"] == "open":
                self.assertIn(f'id="{a["id"]}"', pages["lessons/index.html"])
        self.assertIn('href="archive/', pages["lessons/index.html"])
        for k, v in pages.items():
            if k != "lessons/index.html":
                self.assertNotIn('href="../chat/', v)  # archive pages sit one level deeper
        resolve_all(files, self, "lessons/", check_prs=False)  # archive pages: every relative link resolves (fix PRs can be the PR itself)
        resolve_all(files, self)  # the Timeline's lesson links follow each review to its archive page
        for k, v in files.items():
            if k.startswith("timeline/"):
                for frag in re.findall(r'href="[^"]*lessons/[^"#]*#([^"]+)"', v):
                    self.assertTrue(any(f'id="{frag}"' in p for p in pages.values()), frag)


if __name__ == "__main__":
    unittest.main()
