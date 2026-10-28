#!/usr/bin/env python3
"""The Quest board: the team's roadmap as team quests and dated oaths (data/roadmap.json). Standard library only.

Every quest and oath links a real record, a quest only moves forward, and an oath is judged once. Game words always
travel with a plain word (WORDS), so a visitor who doesn't play games, a screen reader or a search engine still reads
a roadmap. Coordinator edits the board at Monday planning and the Friday retro; check.py runs errors() on every PR.
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Board vocabulary: key -> (game word, plain word). Gamemaster keeps it consistent with data/progression.json and Comms
# owns the wording; no game word may be a role name, so a stage never blurs who did the work.
GROUPS = {"complete": ("Completed quests", "shipped"), "active": ("Active quests", "in progress"),
          "held": ("Held quests", "paused"), "queued": ("Queued quests", "next"),
          "rumor": ("Rumors", "being explored, not committed"), "abandoned": ("Abandoned quests", "dropped, with the reason")}
STAGES = {"discovered": ("Discovered", "explored"), "challenged": ("Challenged", "challenged by the team"), "crafting": ("Crafting", "building"),
          "inspection": ("Inspection", "in review"), "complete": ("Complete", "shipped")}
VERDICTS = {"open": ("Sworn", "not yet due"), "kept": ("Kept", "hit"), "kept_late": ("Kept late", "slipped"), "broken": ("Broken", "missed"),
            "withdrawn": ("Withdrawn", "cut"), "unjudged": ("Unjudged", "can't be measured yet")}
WORDS = {"board": ("Quest board", "the team's roadmap"), "quest": ("Team quest", "roadmap item"), "oath": ("Oath", "a dated call the team made"),
         "fog": ("Fog", "open question"), "unlocks": ("Unlocks", "what this makes possible next"), "raid": ("Raid", "a big quest for several roles"),
         "camp": ("Camp duties", "upkeep")}
ACTIVE_CAP = 6  # a party can carry six: the per-sprint PR limit in data/tempo.json, used here as a focus rule
OPEN_PAST_DUE_DAYS = 7  # the Friday retro judges oaths due that week, so one missed retro is the most an oath may wait
REF = re.compile(r"^(?:i\d+|d\d+|G\d+|pr\d+|c\d+|aar-[a-z0-9-]+|file:[A-Za-z0-9_./-]+)$")


def load(name, root):
    p = root / f"data/{name}.json"
    return json.loads(p.read_text()) if p.exists() else []


def known_refs(root):
    """Every id a quest, oath, history step or camp duty may cite, from the records themselves."""
    refs = {x["id"] for x in load("ideas", root)} | {x["id"] for x in load("design_backlog", root)} | {x["id"] for x in load("wins", root)}
    refs |= {x["id"] for x in load("chat", root)} | {x["id"] for x in load("aars", root)}
    goals = load("goals", root)
    refs |= {g["id"] for g in (goals.get("goals", []) if isinstance(goals, dict) else [])}
    return refs


def roles(root):
    """Role names from bots/*.md headings, the same source check.py uses."""
    return {m.group(1) for f in (root / "bots").glob("*.md") if (m := re.match(r"#\s*(\w+)", f.read_text()))}


def ref_ok(ref, refs, root):
    if not REF.match(ref):
        return False
    if ref.startswith("file:"):
        path = ref[5:]
        return ".." not in path and (root / path).is_file()
    return ref in refs


def kept_count(oaths):
    """(kept, judged): Kept and Kept late over Kept, Kept late and Broken. Withdrawn and Unjudged are listed, not counted."""
    kept = sum(o["verdict"] in ("kept", "kept_late") for o in oaths)
    return kept, kept + sum(o["verdict"] == "broken" for o in oaths)


def errors(root=None, validate=None):
    root = root or ROOT
    p = root / "data/roadmap.json"
    if not p.exists():
        return []
    board = json.loads(p.read_text())
    where = "data/roadmap.json"
    errs = []
    if validate:
        schema = json.loads((root / "data/schema/roadmap.schema.json").read_text())
        errs += [f"{where} {e}" for e in validate(board, schema)]
        if errs:
            return errs
    refs, team = known_refs(root), roles(root)
    state = json.loads((root / "data/state.json").read_text())
    today = state.get("updated") or state["last_run"]  # the record clock, not the wall clock (check.py's calendar rule)
    game = {w for table in (GROUPS, STAGES, VERDICTS, WORDS) for w, _ in table.values()}
    errs += [f"roadmap.py: board word '{w}' is a role name" for w in game for r in team if r.lower() in w.lower().split()]
    seen = set()
    for q in board["quests"]:
        at = f"{where} quest {q['id']}"
        if q["id"] in seen:
            errs.append(f"{at}: duplicate id")
        seen.add(q["id"])
        if not q["history"]:
            errs.append(f"{at}: needs at least one history step")
            continue
        for ref in [q["ref"]] + [h["ref"] for h in q["history"]]:
            if not ref_ok(ref, refs, root):
                errs.append(f"{at}: ref {ref} isn't a record (ideas, design backlog, goals, wins, chat, AARs or a repo file)")
        for r in [q["lead"]] + q.get("party", []):
            if r not in team:
                errs.append(f"{at}: {r} isn't a role in bots/")
        order = [list(STAGES).index(h["stage"]) for h in q["history"]]
        if order != sorted(order) or len(set(order)) != len(order):
            errs.append(f"{at}: stage history must move forward and never repeat a step")
        dates = [h["date"] for h in q["history"]]
        if dates != sorted(dates):
            errs.append(f"{at}: stage history dates go backwards")
        if any(d > today for d in dates):
            errs.append(f"{at}: a stage is dated after the newest record ({today})")
        last = q["history"][-1]["stage"]
        if (q["group"] == "complete") != (last == "complete"):
            errs.append(f"{at}: only a quest whose last stage is complete sits in Completed quests")
        if q["group"] == "complete" and not any(h["stage"] == "complete" and h["ref"].startswith("pr") for h in q["history"]):
            errs.append(f"{at}: a complete quest needs its merged PR (pr<N> in data/wins.json) on the complete step")
        if q["group"] == "abandoned" and not q.get("reason"):
            errs.append(f"{at}: an abandoned quest needs its reason")
        if q["group"] == "held" and not q.get("reason"):
            errs.append(f"{at}: a held quest needs its reason")
    for q in board["quests"]:
        if q.get("unlocks") and q["unlocks"] not in seen:
            errs.append(f"{where} quest {q['id']}: unlocks {q['unlocks']}, which isn't a quest on the board")
    active = sum(q["group"] == "active" for q in board["quests"])
    if active > ACTIVE_CAP:
        errs.append(f"{where}: {active} active quests; the party carries at most {ACTIVE_CAP}")
    for c in board.get("camp", []):
        if not ref_ok(c["ref"], refs, root):
            errs.append(f"{where} camp duty {c['title']!r}: ref {c['ref']} isn't a record")
    seen = set()
    for o in board["oaths"]:
        at = f"{where} oath {o['id']}"
        if o["id"] in seen:
            errs.append(f"{at}: duplicate id")
        seen.add(o["id"])
        for ref in [o["ref"]] + [o[k] for k in ("evidence", "aar") if o.get(k)]:
            if not ref_ok(ref, refs, root):
                errs.append(f"{at}: ref {ref} isn't a record")
        if o["lead"] not in team:
            errs.append(f"{at}: {o['lead']} isn't a role in bots/")
        if o["sworn"] > o["due"]:
            errs.append(f"{at}: due before it was sworn")
        if o["sworn"] > today:
            errs.append(f"{at}: sworn after the newest record ({today}); oaths are never backdated or pre-dated")
        if o["verdict"] == "open":
            if days_between(o["due"], today) > OPEN_PAST_DUE_DAYS:
                errs.append(f"{at}: due {o['due']} and still open more than {OPEN_PAST_DUE_DAYS} days later; the Friday retro judges it")
            continue
        if not o.get("judged"):
            errs.append(f"{at}: a {o['verdict']} oath needs the date it was judged")
        elif o["judged"] > today:
            errs.append(f"{at}: judged after the newest record ({today})")
        if o["verdict"] in ("kept", "kept_late", "broken") and not o.get("evidence"):
            errs.append(f"{at}: a {o['verdict']} oath needs the record that proves it")
        if o["verdict"] == "broken" and not o.get("aar"):
            errs.append(f"{at}: a broken oath links its after-action review")
        if o["verdict"] in ("withdrawn", "unjudged") and not o.get("reason"):
            errs.append(f"{at}: a {o['verdict']} oath needs its reason")
        if o["verdict"] == "kept_late" and o.get("judged", "") <= o["due"]:
            errs.append(f"{at}: kept late means judged after {o['due']}")
    return errs


def days_between(a, b):
    from datetime import date
    return (date.fromisoformat(b) - date.fromisoformat(a)).days
