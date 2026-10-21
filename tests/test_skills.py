"""Role skills from pinned toolkits (Ryno, 2026-10-19 10:06 PM ET: "Ok have the team level up immediately using pstack
and adding to their profiles"). Trial's tests: bots/*.md skills match data/skills.json, and the drift check sees upstream changes."""
import hashlib, json, re, shutil, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check  # noqa: E402
import skills  # noqa: E402

MAN = json.loads((ROOT / "data/skills.json").read_text())
PSTACK, TEAMKIT = "d457567332aa6989e753ea289f30ea2bfbc80bc0", "2b8ae2ee306f823d54879d3da7f8496b73c31d5d"
SUPERPOWERS = "bb92a77741419a4ab5f06e711a283343f1ada0c3"  # obra/superpowers v7.0.0 release commit, reviewed 2026-10-21


def role(name, *lines):
    return f"# {name} (Test)\n\n**Role:** Tests.\n\n**Skills:** trained.\n" + "".join(l + "\n" for l in lines) + "\n**Handoff:** none.\n"


def line(name, source="Team Kit", use="Uses it well.", url=None):
    return f"- [{name}]({url or skills.link(MAN, source, name)}) ({source}): {use}"


class Fixture(unittest.TestCase):
    """A copy of the manifest with two used skills, and one role file per case."""
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "bots").mkdir()
        (self.root / "data/schema").mkdir(parents=True)
        shutil.copy(ROOT / "data/schema/skills.schema.json", self.root / "data/schema/")
        man = json.loads(json.dumps(MAN))
        man["skills"] = {k: v for k, v in man["skills"].items() if k in ("verify-this", "blast-radius")}
        self.man = man
        self.save()

    def save(self):
        (self.root / "data/skills.json").write_text(json.dumps(self.man))

    def write(self, text, name="trial"):
        (self.root / f"bots/{name}.md").write_text(text)

    def errs(self):
        return skills.errors(self.root, check.validate)


class Profiles(Fixture):
    def test_a_good_profile_passes(self):
        self.write(role("Trial", line("verify-this"), line("blast-radius", "pstack")))
        self.assertEqual(self.errs(), [])

    def test_a_skill_missing_from_the_manifest_fails(self):
        self.write(role("Trial", line("verify-this"), line("blast-radius", "pstack"), line("made-up-skill")))
        self.assertTrue(any("made-up-skill isn't in data/skills.json" in e for e in self.errs()))

    def test_a_skipped_skill_cant_be_listed(self):
        self.write(role("Trial", line("verify-this"), line("blast-radius", "pstack"), line("control-cli")))
        self.assertTrue(any("on the skipped list" in e for e in self.errs()))

    def test_the_wrong_source_fails(self):
        self.write(role("Trial", line("verify-this", "pstack"), line("blast-radius", "pstack")))
        self.assertTrue(any("is from Team Kit, not pstack" in e for e in self.errs()))

    def test_an_unpinned_link_fails(self):
        moving = "https://github.com/cursor/plugins/tree/main/cursor-team-kit/skills/verify-this"
        self.write(role("Trial", line("verify-this", url=moving), line("blast-radius", "pstack")))
        self.assertTrue(any("pinned commit" in e for e in self.errs()))

    def test_one_to_four_skills(self):
        self.write(role("Trial"))
        self.assertTrue(any("lists 0 skills" in e for e in self.errs()))
        self.man["skills"] = MAN["skills"]
        self.save()
        names = [n for n, v in MAN["skills"].items() if v["source"] == "Team Kit"][:5]
        self.write(role("Trial", *(line(n) for n in names)))
        self.assertTrue(any("lists 5 skills" in e for e in self.errs()))

    def test_a_role_without_a_skills_block_fails(self):
        self.write(role("Trial", line("verify-this"), line("blast-radius", "pstack")))
        self.write("# Lens (Reviewer)\n\n**Role:** Reviews.\n", "lens")
        self.assertTrue(any("bots/lens.md: needs a **Skills:** block" in e for e in self.errs()))

    def test_a_long_use_line_fails(self):
        self.write(role("Trial", line("verify-this", use=" ".join(["word"] * 26)), line("blast-radius", "pstack")))
        self.assertTrue(any("26 words" in e for e in self.errs()))

    def test_a_duplicate_fails(self):
        self.write(role("Trial", line("verify-this"), line("verify-this"), line("blast-radius", "pstack")))
        self.assertTrue(any("listed twice" in e for e in self.errs()))

    def test_a_malformed_line_fails(self):
        self.write(role("Trial", line("verify-this"), line("blast-radius", "pstack"), "- verify-this: no link"))
        self.assertTrue(any("isn't '- [name](link)" in e for e in self.errs()))

    def test_an_unused_manifest_skill_fails(self):
        self.write(role("Trial", line("verify-this")))
        self.assertTrue(any("blast-radius isn't used by any role" in e for e in self.errs()))

    def test_used_and_skipped_at_once_fails(self):
        self.man["skipped"]["verify-this"] = {"source": "Team Kit", "why": "x"}
        self.save()
        self.write(role("Trial", line("verify-this"), line("blast-radius", "pstack")))
        self.assertTrue(any("both used and skipped" in e for e in self.errs()))

    def test_a_bad_hash_fails_the_schema(self):
        self.man["skills"]["verify-this"]["sha256"] = "abc"
        self.save()
        self.write(role("Trial", line("verify-this"), line("blast-radius", "pstack")))
        self.assertTrue(any("sha256" in e for e in self.errs()))


class Drift(Fixture):
    """scripts/skills.py --drift against a fake checkout of cursor/plugins."""
    def setUp(self):
        super().setUp()
        self.up = Path(tempfile.mkdtemp())
        for kind in ("skills", "skipped"):
            for n, v in self.man[kind].items():
                d = self.up / self.man["sources"][v["source"]]["path"] / "skills" / n
                d.mkdir(parents=True)
                (d / "SKILL.md").write_text(f"# {n}\n")
        for n, v in self.man["skills"].items():
            v["sha256"] = hashlib.sha256(f"# {n}\n".encode()).hexdigest()
        self.save()

    def test_no_drift(self):
        self.assertEqual(skills.drift(self.up, self.root), [])

    def test_changed_removed_and_new(self):
        (self.up / "cursor-team-kit/skills/verify-this/SKILL.md").write_text("# verify-this, edited\n")
        shutil.rmtree(self.up / "pstack/skills/blast-radius")
        (self.up / "pstack/skills/brand-new").mkdir()
        (self.up / "pstack/skills/brand-new/SKILL.md").write_text("new")
        self.assertEqual(sorted(skills.drift(self.up, self.root)),
                         [("Team Kit", "verify-this", "changed"), ("pstack", "blast-radius", "removed"), ("pstack", "brand-new", "new")])


class Superpowers(Fixture):
    """Superpowers (Ryno, 2026-10-21): skills/ at the repo root, its own trained date, and drift run per repo."""
    def test_a_root_level_source_links_without_a_dot(self):
        self.assertEqual(skills.link(MAN, "Superpowers", "brainstorming"), "https://github.com/obra/superpowers/tree/bb92a77/skills/brainstorming")

    def test_a_path_other_than_a_folder_name_or_dot_fails(self):
        self.man["sources"]["Superpowers"]["path"] = "../x"
        self.save()
        self.write(role("Trial", line("verify-this"), line("blast-radius", "pstack")))
        self.assertTrue(any("path" in e for e in self.errs()))

    def test_drift_compares_only_the_named_repo(self):
        up = Path(tempfile.mkdtemp())
        (up / "skills/brainstorming").mkdir(parents=True)
        (up / "skills/brainstorming/SKILL.md").write_text("x")
        got = skills.drift(up, ROOT, "https://github.com/obra/superpowers")
        self.assertEqual({s for s, _, _ in got}, {"Superpowers"})
        self.assertIn(("Superpowers", "brainstorming", "changed"), got)
        self.assertIn(("Superpowers", "writing-plans", "removed"), got)

    def test_sheets_show_both_training_days(self):
        sketch = (ROOT / "site/team/sketch/index.html").read_text().split('id="training"')[1]
        self.assertIn("Trained Oct 20 and 21, 2026", sketch)
        self.assertIn("Trained Oct 20, 2026", (ROOT / "site/team/critic/index.html").read_text())


class Repo(unittest.TestCase):
    def test_the_repo_passes(self):
        self.assertEqual(check.skills_errors(), [])

    def test_pins_match_the_reviewed_baseline(self):
        self.assertEqual(MAN["sources"]["pstack"]["commit"], PSTACK)
        self.assertEqual(MAN["sources"]["pstack"]["version"], "0.15.28")
        self.assertEqual(MAN["sources"]["Team Kit"]["commit"], TEAMKIT)
        self.assertEqual(MAN["sources"]["Superpowers"]["commit"], SUPERPOWERS)
        self.assertEqual(MAN["sources"]["Superpowers"]["version"], "7.0.0")
        self.assertEqual({s["license"] for s in MAN["sources"].values()}, {"MIT"})

    def test_every_upstream_skill_is_used_or_skipped(self):
        for src, s in MAN["sources"].items():
            seen = sum(v["source"] == src for k in ("skills", "skipped") for v in MAN[k].values())
            self.assertEqual(seen, s["skills_upstream"], src)

    def test_every_role_page_shows_its_training(self):
        for f in sorted((ROOT / "bots").glob("*.md")):
            page = (ROOT / f"site/team/{f.stem}/index.html").read_text()
            got = skills.role_skills(f.read_text())
            self.assertIn('<h2 id="training">Training</h2>', page, f.stem)
            for name, url, _, _ in got:
                self.assertIn(f'<a href="{url}">{name}</a>', page, f.stem)

    def test_team_cards_link_the_training(self):
        # Trading cards (Oct 20): the card links the sheet, and the sheet's Training section lists the skills.
        page = (ROOT / "site/team/index.html").read_text()
        self.assertIn('href="trial/">Character sheet', page)
        self.assertNotIn("verify-this", page, "skills live on the sheet, not the card")
        self.assertIn("verify-this", (ROOT / "site/team/trial/index.html").read_text().split('id="training"')[1])

    def test_training_earns_no_xp_on_its_own(self):
        prog = json.loads((ROOT / "data/progression.json").read_text())
        self.assertFalse([k for k in prog["events"] if "train" in k or "skill" in k])


if __name__ == "__main__":
    unittest.main()
