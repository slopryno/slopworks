"""Lean repo checks (Ryno, 2026-10-17): no screenshots or temp files in git, a tree-size and file-size budget."""
import sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check  # noqa: E402


class Lean(unittest.TestCase):
    def errs(self, files, sizes=None, ignored=()):
        return check.lean_errors(files, sizes or {f: 10 for f in files}, ignored)

    def test_screenshots_and_images_outside_site_assets_fail(self):
        for f in ("docs/design/review/77/dark-390/work.webp", "docs/design/xp/after.png", "shot.JPG", "docs/x.svg"):
            self.assertTrue(self.errs([f]), f)

    def test_real_site_assets_pass(self):
        self.assertEqual(self.errs(["site/assets/avatars/forge.svg", "site/badges/roles.svg", "site/index.html"]), [])

    def test_temp_cache_and_build_output_fail(self):
        for f in ("scripts/__pycache__/x.cpython-312.pyc", "notes.tmp", "run.log", "a.md~", "x.py.orig", ".DS_Store",
                  "tmp/x.json", "build/out.html", "docs/design/review/81/manifest.json", "site/a.swp", "dump.zip"):
            self.assertTrue(self.errs([f]), f)

    def test_ordinary_files_pass(self):
        self.assertEqual(self.errs(["data/chat.json", "scripts/build.py", "docs/design/mobile/audit.md", "site/feed.xml"]), [])

    def test_file_and_tree_budgets(self):
        self.assertTrue(self.errs(["data/big.json"], {"data/big.json": check.LEAN_FILE_BYTES + 1}))
        many = [f"data/{i}.json" for i in range(20)]
        self.assertTrue(self.errs(many, {f: check.LEAN_TREE_BYTES // 19 for f in many}))

    def test_tracked_files_that_gitignore_excludes_fail(self):
        self.assertTrue(self.errs(["data/a.json"], ignored=["data/a.json"]))

    def test_this_repo_is_lean(self):
        files = check.tracked_files()
        self.assertEqual(check.lean_errors(files, {f: (ROOT / f).stat().st_size for f in files}, check.tracked_ignored()), [])


if __name__ == "__main__":
    unittest.main()
