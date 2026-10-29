"""Quest board data (data/roadmap.json): each rule in scripts/roadmap.py fails on a broken board and passes on the real one."""
import copy, json, shutil, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check, roadmap  # noqa: E402

BOARD = json.loads((ROOT / "data/roadmap.json").read_text())


def errs_for(board):
    """roadmap.errors on a temp repo copy holding this board, with the real records beside it."""
    tmp = Path(tempfile.mkdtemp())
    try:
        for d in ("data", "bots", "plans"):
            shutil.copytree(ROOT / d, tmp / d)
        (tmp / "data/roadmap.json").write_text(json.dumps(board))
        return roadmap.errors(tmp, check.validate)
    finally:
        shutil.rmtree(tmp)


def quest(board, qid):
    return next(q for q in board["quests"] if q["id"] == qid)


def oath(board, oid):
    return next(o for o in board["oaths"] if o["id"] == oid)


class RealBoard(unittest.TestCase):
    def test_real_board_passes(self):
        self.assertEqual(roadmap.errors(ROOT, check.validate), [])
        self.assertIn("roadmap", check.roadmap_errors.__code__.co_names)

    def test_no_board_word_is_a_role_name(self):
        team = {r.lower() for r in roadmap.roles(ROOT)}
        for table in (roadmap.GROUPS, roadmap.STAGES, roadmap.VERDICTS, roadmap.WORDS):
            for game, plain in table.values():
                self.assertFalse(team & set(game.lower().split()), game)
                self.assertTrue(plain)  # every game word travels with a plain word


class BrokenBoards(unittest.TestCase):
    def broken(self, change, expect):
        b = copy.deepcopy(BOARD)
        change(b)
        errs = errs_for(b)
        self.assertTrue(any(expect in e for e in errs), errs)

    def test_unknown_ref(self):
        self.broken(lambda b: quest(b, "social-preview").update(ref="i9999"), "isn't a record")

    def test_unknown_role(self):
        self.broken(lambda b: quest(b, "item-pages").update(lead="Wizard"), "isn't a role")

    def test_stage_going_backwards(self):
        self.broken(lambda b: quest(b, "rpg-quests")["history"].reverse(), "move forward")

    def test_stage_dated_after_the_records(self):
        self.broken(lambda b: quest(b, "rpg-quests")["history"].append({"stage": "crafting", "date": "2099-01-01", "ref": "c163"}), "after the newest record")

    def test_empty_history_is_an_error_not_a_crash(self):
        self.broken(lambda b: quest(b, "social-preview").update(history=[]), "at least one history step")

    def test_too_many_active_quests(self):
        def seven(b):
            for q in b["quests"]:
                if q["group"] == "queued":
                    q["group"] = "active"
        self.broken(seven, "at most 6")

    def test_complete_needs_a_merged_pr(self):
        def fake(b):
            q = quest(b, "social-preview")
            q["group"] = "complete"
            q["history"].append({"stage": "complete", "date": "2026-10-20", "ref": "d2"})
        self.broken(fake, "merged PR")

    def test_abandoned_needs_a_reason(self):
        self.broken(lambda b: quest(b, "nav-tab-bar").pop("reason"), "needs its reason")

    def test_held_needs_a_reason(self):
        self.broken(lambda b: quest(b, "rpg-quests").pop("reason"), "held quest needs its reason")

    def test_unlocks_names_a_quest(self):
        self.broken(lambda b: quest(b, "rpg-quests").update(unlocks="nowhere"), "isn't a quest on the board")

    def test_oath_left_open_past_due(self):
        self.broken(lambda b: oath(b, "g2-showcase").update(due="2026-10-20"), "still open")

    def test_broken_oath_links_evidence_and_its_aar(self):
        def broke(b):
            oath(b, "g3-fast-features").update(verdict="broken", judged="2026-10-28", evidence="G3")
        self.broken(broke, "after-action review")

    def test_unjudged_oath_needs_a_reason(self):
        self.broken(lambda b: oath(b, "g1-get-found").update(verdict="unjudged", judged="2026-10-28"), "needs its reason")

    def test_oath_never_pre_dated(self):
        self.broken(lambda b: oath(b, "g2-showcase").update(sworn="2099-01-01", due="2099-02-01"), "never backdated")


class Count(unittest.TestCase):
    def test_kept_count_leaves_out_withdrawn_and_unjudged(self):
        o = [{"verdict": v} for v in ("kept", "kept_late", "broken", "withdrawn", "unjudged", "open")]
        self.assertEqual(roadmap.kept_count(o), (2, 3))


if __name__ == "__main__":
    unittest.main()
