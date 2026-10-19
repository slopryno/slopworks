"""Standing tempo with an automatic slowdown (i44, Ryno 2026-10-18 8:35 AM ET).

Normal: up to 6 PRs a sprint and 3 sprints a day, so at most 18 merged PRs a day.
Slowed: 1 sprint of 3 PRs a day. Any revert, CI failure on main, failed deploy, or incident or data-correction AAR
trips it (each of those gets a same-day AAR, so the AAR record is the trigger). The trip happens when the AAR's
change PR merges. It stays slowed until 10 clean PRs merge after the latest trip; a new trip resets the count.
On the trip day, only PRs merged after the trip count toward the slowed day's 3.

Everything here comes from records (data/wins.json, data/aars.json), so anyone can re-derive the mode.
wins.py writes data/tempo.json; check.py and tests recompute it; bot.py pr refuses a PR over today's limit.
"""
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRIPS = ("revert", "failed-deploy", "ci-main", "incident", "data-correction")
LIMITS = {"normal": {"prs_per_day": 18, "sprints_per_day": 3, "prs_per_sprint": 6},
          "slowed": {"prs_per_day": 3, "sprints_per_day": 1, "prs_per_sprint": 3}}
CLEAN_NEEDED = 10
EFFECTIVE = "2026-10-18T08:35-04:00"  # Ryno's decision (i44); earlier days aren't held to it
PENDING = "9999-12-31T23:59-04:00"    # an AAR whose change PR hasn't merged yet trips "now"
OVERRIDES = "data/ceo_overrides.json"  # add-only CEO records that lift the slowdown for named branches until they expire


def merged(wins):
    """[(number, merged ISO)] oldest first, from wins.json entries or {"number", "merged"} dicts."""
    out = [(w["number"] if "number" in w else int(w["pr"].rsplit("/", 1)[1]), w["merged"]) for w in wins]
    return sorted(out, key=lambda x: x[1])


def trips(wins, aars):
    at = dict(merged(wins))
    return sorted(((at.get(a["change_pr"], PENDING), a["id"], a["change_pr"]) for a in aars if a["trigger"] in TRIPS))


def state_at(prs, tr, when):
    """Mode just before `when`, from trips and merges strictly earlier."""
    past = [t for t in tr if t[0] < when or (t[0] == PENDING and when == PENDING)]
    if not past:
        return "normal", None, 0
    last = past[-1]
    clean = sum(1 for _, m in prs if last[0] < m < when)
    return ("slowed" if clean < CLEAN_NEEDED else "normal"), last, clean


def used_on(prs, mode, last, day, before):
    """PRs merged on ET `day` before `before` that count toward that day's limit."""
    since = last[0] if (mode == "slowed" and last and last[0][:10] == day) else ""
    return sum(1 for _, m in prs if m[:10] == day and since < m < before)


def violations(wins, aars, overrides=None, excused=None):
    """Every merged PR since the decision that went over its day's limit. A PR over the slowed limit is excused only
    inside a CEO override's window, up to its max_prs, under the normal limit, and only if no trip came after the
    override (excused lists them)."""
    prs, tr, out = merged(wins), trips(wins, aars), []
    overrides = load_overrides() if overrides is None else overrides
    for n, m in prs:
        if m < EFFECTIVE:
            continue
        mode, last, _ = state_at(prs, tr, m)
        used = used_on(prs, mode, last, m[:10], m)
        o = lifted(overrides, prs, last, m) if mode == "slowed" and used >= LIMITS[mode]["prs_per_day"] else None
        if o and used < LIMITS["normal"]["prs_per_day"]:
            if excused is not None:
                excused.append(f"#{n} merged {m} as PR {used + 1} of the day, over the slowed limit, under {o['id']} ({o['by']}, {o['at']})")
        elif used >= LIMITS[mode]["prs_per_day"]:
            out.append(f"#{n} merged {m} as PR {used + 1} of the day in {mode} mode (limit {LIMITS[mode]['prs_per_day']})")
    return out


def derive(wins, aars, overrides=None):
    overrides = load_overrides() if overrides is None else overrides
    excused = []
    prs, tr = merged(wins), trips(wins, aars)
    mode, last, clean = state_at(prs, tr, PENDING)
    days = sorted({m[:10] for _, m in prs if m >= EFFECTIVE})
    return {"decision": "i44", "effective": EFFECTIVE, "limits": LIMITS, "clean_needed": CLEAN_NEEDED,
            "trip_triggers": list(TRIPS), "mode": mode, "clean_prs": clean if last else None,
            "tripped_by": last[1] if last else None, "trip_pr": last[2] if last else None,
            "trip_at": (None if not last or last[0] == PENDING else last[0]),
            "as_of_pr": prs[-1][0] if prs else None,
            "days": [{"date": d, "prs": sum(1 for _, m in prs if m[:10] == d and m >= EFFECTIVE)} for d in days],
            "violations": violations(wins, aars, overrides, excused), "excused": excused,
            "ceo_overrides": [{k: o[k] for k in ("id", "by", "quote", "at", "expires", "branches", "max_prs")} for o in overrides]}


def today(wins, aars, now, branch=None, overrides=None):
    """(mode, used, limit) for a new PR at `now` (an aware datetime), for bot.py pr. A CEO override can lift the
    slowed limit to the normal one, only for a branch it names, only inside its window (see lifted)."""
    prs, tr = merged(wins), trips(wins, aars)
    when = now.isoformat(timespec="minutes")
    if any(t[0] == PENDING for t in tr):  # the AAR rides in an unmerged PR: slowed from now, nothing counted yet
        return "slowed", 0, LIMITS["slowed"]["prs_per_day"]
    mode, last, _ = state_at(prs, tr, when)
    used, limit = used_on(prs, mode, last, when[:10], when), LIMITS[mode]["prs_per_day"]
    if mode == "slowed" and used >= limit and branch:
        o = lifted(load_overrides() if overrides is None else overrides, prs, last, when, branch)
        if o:
            return f"slowed, lifted for {branch} by {o['id']}", used, LIMITS["normal"]["prs_per_day"]
    return mode, used, limit


# ---------- CEO overrides (Ryno 2026-10-19 4:31 PM ET: "Im lifting the slowdown for this work only.") ----------
# Scoped, auditable and expiring: each record names its branches, its CEO quote and an expiry at most 24 hours on.
# The file is add-only (check.py loosening flags any removed line). Tripwires stay: a pending AAR still slows "now"
# (today returns before any override), and a trip after the override's start ends it.
BRANCH = r"^bot/(data|design|feature|ops)-[\w.-]+$"


def load_overrides(root=None):
    """The CEO override records, validated; a bad record raises ValueError so CI fails closed."""
    import re
    from datetime import datetime as dt
    p = (root or ROOT) / OVERRIDES
    recs = json.loads(p.read_text()) if p.exists() else []
    if not isinstance(recs, list):
        raise ValueError(f"{OVERRIDES} must be a list")
    seen = set()
    for o in recs:
        need = {"id", "kind", "by", "quote", "source", "at", "expires", "branches", "max_prs"}
        if not isinstance(o, dict) or set(o) != need:
            raise ValueError(f"{OVERRIDES}: each record has exactly {sorted(need)}")
        if o["kind"] != "lift-slowdown" or o["by"] != "Ryno (CEO)" or not o["quote"].strip() or o["id"] in seen:
            raise ValueError(f"{OVERRIDES} {o['id']}: kind lift-slowdown, by Ryno (CEO), a quote, and a unique id")
        seen.add(o["id"])
        at, exp = dt.fromisoformat(o["at"]), dt.fromisoformat(o["expires"])
        if not at.tzinfo or not (at < exp <= at.replace(hour=23, minute=59)) or (exp - at).total_seconds() > 86400:
            raise ValueError(f"{OVERRIDES} {o['id']}: expires after it starts, by 23:59 the same ET day")
        if not o["branches"] or len(set(o["branches"])) != len(o["branches"]) or not all(re.match(BRANCH, b) for b in o["branches"]):
            raise ValueError(f"{OVERRIDES} {o['id']}: branches must be distinct bot/<kind>-<slug> names")
        if not isinstance(o["max_prs"], int) or not 0 < o["max_prs"] <= len(o["branches"]):
            raise ValueError(f"{OVERRIDES} {o['id']}: max_prs is between 1 and the number of branches")
    return recs


def lifted(overrides, prs, last, when, branch=None):
    """The override covering a merge at `when` (for branch, when known), or None. It needs: its window open, the
    branch named, no trip since it started, and fewer than max_prs PRs already merged in its window."""
    for o in overrides:
        if not (o["at"] <= when < o["expires"]) or (branch is not None and branch not in o["branches"]):
            continue
        if not last or last[0] >= o["at"]:
            continue  # no slowdown to lift, or a trip came after the override: the slowdown stands
        if sum(1 for _, m in prs if o["at"] <= m < when) < o["max_prs"]:
            return o
    return None


def write():
    load = lambda n: json.loads((ROOT / f"data/{n}.json").read_text())
    (ROOT / "data/tempo.json").write_text(json.dumps(derive(load("wins"), load("aars")), indent=2) + "\n")


if __name__ == "__main__":
    write()
    t = json.loads((ROOT / "data/tempo.json").read_text())
    print(f"tempo: {t['mode']}, {t['clean_prs']} of {t['clean_needed']} clean PRs since {t['tripped_by']}")
