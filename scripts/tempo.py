"""Standing tempo with an automatic slowdown (i44, Ryno 2026-10-18 8:35 AM ET).

Normal: up to 6 PRs a sprint and 3 sprints a day, so at most 18 merged PRs a day.
Slowed: 1 sprint of 3 PRs a day. Any revert, CI failure on main, failed deploy, or incident or data-correction AAR
trips it (each of those gets a same-day AAR, so the AAR record is the trigger). The trip happens when the AAR's
change PR merges. It stays slowed until 10 clean PRs merge after the latest trip; a new trip resets the count.
On the trip day, only PRs merged after the trip count toward the slowed day's 3 (through Oct 18). From Oct 19 on
(Ryno 2026-10-19 7:27 AM ET, approving the training plan), every PR merged that ET day counts, before or after a trip:
a trip can't reopen a day that already used its slowed limit.

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
WHOLE_DAY_FROM = "2026-10-19"  # loophole fix: from this ET day, a trip no longer resets the day's count
PENDING = "9999-12-31T23:59-04:00"    # an AAR whose change PR hasn't merged yet trips "now"


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
    since = last[0] if (mode == "slowed" and last and last[0][:10] == day and day < WHOLE_DAY_FROM) else ""
    return sum(1 for _, m in prs if m[:10] == day and since < m < before)


def violations(wins, aars):
    """Every merged PR since the decision that went over its day's limit."""
    prs, tr, out = merged(wins), trips(wins, aars), []
    for n, m in prs:
        if m < EFFECTIVE:
            continue
        mode, last, _ = state_at(prs, tr, m)
        used = used_on(prs, mode, last, m[:10], m)
        if used >= LIMITS[mode]["prs_per_day"]:
            out.append(f"#{n} merged {m} as PR {used + 1} of the day in {mode} mode (limit {LIMITS[mode]['prs_per_day']})")
    return out


def derive(wins, aars):
    prs, tr = merged(wins), trips(wins, aars)
    mode, last, clean = state_at(prs, tr, PENDING)
    days = sorted({m[:10] for _, m in prs if m >= EFFECTIVE})
    return {"decision": "i44", "effective": EFFECTIVE, "limits": LIMITS, "clean_needed": CLEAN_NEEDED,
            "trip_triggers": list(TRIPS), "mode": mode, "clean_prs": clean if last else None,
            "tripped_by": last[1] if last else None, "trip_pr": last[2] if last else None,
            "trip_at": (None if not last or last[0] == PENDING else last[0]),
            "as_of_pr": prs[-1][0] if prs else None,
            "days": [{"date": d, "prs": sum(1 for _, m in prs if m[:10] == d and m >= EFFECTIVE)} for d in days],
            "violations": violations(wins, aars)}


def today(wins, aars, now):
    """(mode, used, limit) for a new PR at `now` (an aware datetime), for bot.py pr."""
    prs, tr = merged(wins), trips(wins, aars)
    when = now.isoformat(timespec="minutes")
    if any(t[0] == PENDING for t in tr):  # the AAR rides in an unmerged PR: slowed from now
        day = when[:10]
        used = sum(1 for _, m in prs if m[:10] == day and m < when) if day >= WHOLE_DAY_FROM else 0
        return "slowed", used, LIMITS["slowed"]["prs_per_day"]
    mode, last, _ = state_at(prs, tr, when)
    return mode, used_on(prs, mode, last, when[:10], when), LIMITS[mode]["prs_per_day"]


def write():
    load = lambda n: json.loads((ROOT / f"data/{n}.json").read_text())
    (ROOT / "data/tempo.json").write_text(json.dumps(derive(load("wins"), load("aars")), indent=2) + "\n")


if __name__ == "__main__":
    write()
    t = json.loads((ROOT / "data/tempo.json").read_text())
    print(f"tempo: {t['mode']}, {t['clean_prs']} of {t['clean_needed']} clean PRs since {t['tripped_by']}")
