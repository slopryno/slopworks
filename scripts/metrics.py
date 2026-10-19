"""Public metrics and trends (i45, Ryno 2026-10-18 8:37 and 8:39 AM ET). Analyst owns the definitions (c-thread in i45).

Every number comes from records: data/wins.json (merged PRs with open and merge times), data/aars.json, data/ci.json
(a daily summary of GitHub Actions runs, written by wins.py), data/refusals.json, data/ideas.json and data/tempo.json.
wins.py writes data/metrics.json; tests recompute it. Trends compare the newest day with the day before, using rates per
10 merged PRs where volume differs, and say so plainly: there are only a few days of history.
"""
import json, re, statistics
from datetime import datetime
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = "https://github.com/slopryno/slopworks/blob/main/"
DAY = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ESCAPED = ("incident", "data-correction")
# key, label, rate per 10 PRs?, which way is better (None: neither, say only the direction), definition
TRENDS = [
    ("prs", "Merged PRs", False, None, "PRs merged that day (ET)."),
    ("open_to_merge_min", "Median open to merge, minutes", False, None, "Median minutes from a PR opening to its merge, for PRs merged that day."),
    ("escaped", "Incidents and data corrections", True, "down", "Incident or data-correction AARs dated that day: problems that got past review."),
    ("corrections", "Data corrections", True, "down", "Data-correction AARs dated that day."),
    ("aars", "AARs", True, "down", "All after-action reviews dated that day."),
    ("ci_catches", "CI catches before merge", True, None, "Failed CI runs on bot PR branches: a mistake stopped before it merged."),
    ("main_failures", "Failures on main", False, "down", "Failed CI or Pages runs on main."),
    ("reverts", "Reverts", False, "down", "Merged PRs titled Revert."),
    ("blocks", "Blocks upheld", False, None, "Block-upheld AARs: a reviewer stopped a merge and was right."),
]


def nice(d):
    x = datetime.fromisoformat(d)
    return f"{DAY[x.weekday()]} {MON[x.month - 1]}\u00a0{x.day}"


def minutes(a, b):
    return (datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds() / 60


def derive(wins, aars, ci, ideas, refusals, tempo, blast=(), month1=None):
    by_num = {int(w["pr"].rsplit("/", 1)[1]): w for w in wins}
    cid = {c["date"]: c for c in ci["days"]}
    start = min(w["date"] for w in wins)
    dates = sorted({w["date"] for w in wins} | {a["date"] for a in aars} | {d for d in cid if d >= start})
    days = []
    for d in dates:
        ws = [w for w in wins if w["date"] == d]
        av = [a for a in aars if a["date"] == d]
        c = cid.get(d, {})
        waits = [minutes(w["opened"], w["merged"]) for w in ws if w.get("opened")]
        days.append({"date": d, "prs": len(ws), "open_to_merge_min": round(statistics.median(waits)) if waits else None,
                     "escaped": sum(a["trigger"] in ESCAPED for a in av), "corrections": sum(a["trigger"] == "data-correction" for a in av),
                     "aars": len(av), "ci_catches": c.get("pr_ci_failed_bot", 0), "ci_recorded": d in cid,
                     "main_failures": c.get("main_ci_failed", 0) + c.get("pages_failed", 0),
                     "reverts": sum(w["title"].lower().startswith("revert") for w in ws),
                     "blocks": sum(a["trigger"] == "block-upheld" for a in av),
                     "refusals": sum(r["at"][:10] == d for r in refusals)})
    waits = [minutes(w["opened"], w["merged"]) for w in wins if w.get("opened")]
    sprints = []
    for i in ideas:
        m = re.match(r"#(\d+) (?:to|and) #(\d+)", i.get("shipped") or "")
        if i.get("short_title") and i["state"] == "shipped" and m and int(m.group(1)) in by_num and int(m.group(2)) in by_num:
            a, b = by_num[int(m.group(1))], by_num[int(m.group(2))]
            sprints.append({"idea": i["id"], "title": i["short_title"], "prs": int(m.group(2)) - int(m.group(1)) + 1,
                            "minutes": round(minutes(a.get("opened") or a["merged"], b["merged"]))})
    trends = []
    if len(days) >= 2:
        p, n = days[-2], days[-1]
        for key, label, rate, better, _ in TRENDS:
            val = lambda x: (round(10 * x[key] / x["prs"], 1) if x["prs"] else None) if rate else x[key]
            a, b = val(p), val(n)
            way = "n/a" if a is None or b is None else ("flat" if a == b else ("up" if b > a else "down"))
            verdict = None if better is None or way in ("flat", "n/a") else ("better" if way == better else "worse")
            trends.append({"key": key, "label": label + (" per 10 PRs" if rate else ""), "prev": a, "new": b, "direction": way, "verdict": verdict})
    extra = {"goals": goal_progress(**month1)} if month1 else {}
    return {"as_of": max(w["merged"] for w in wins), "newest_day": dates[-1], "days_of_history": len(days),
            "ci_window_start": ci["window_start"],
            "totals": {"prs": len(wins), "open_to_merge_min": round(statistics.median(waits)) if waits else None,
                       "ci_catches": sum(x["ci_catches"] for x in days), "main_failures": sum(x["main_failures"] for x in days),
                       "reverts": sum(x["reverts"] for x in days), "aars": len(aars), "escaped": sum(x["escaped"] for x in days),
                       "blocks": sum(x["blocks"] for x in days), "refusals": len(refusals),
                       "blast_checked": len(blast), "blast_matched": sum(b["result"] == "matched" for b in blast)},
            "pace": {"mode": tempo["mode"], "clean_prs": tempo["clean_prs"], "clean_needed": tempo["clean_needed"]},
            "days": days, "sprints": sprints, "trends": trends,
            "worsening": [t["key"] for t in trends if t["verdict"] == "worse"], **extra}


# ---------- Month-1 goals (Strategy's G1 to G3, Ryno approved 2026-10-19, i60): progress from records only ----------
def month1_inputs(load, exists):
    """The records goal_progress reads. reach.json holds aggregate GitHub traffic counts only, and doesn't exist until Ryno picks the access route."""
    return {"goals": load("goals"), "cases": load("cases"), "arena": load("arena"), "challenges": load("challenges"),
            "updates": load("updates"), "reach": load("reach") if exists("reach") else None}


def goal_progress(goals, cases, arena, challenges, updates, reach=None):
    start, out = goals["start"], []
    for g in goals["goals"]:
        row = {"id": g["id"], "title": g["title"], "target": g["target"], "source": g["source"]}
        if g["id"] == "G1":
            if not reach:
                row.update(status="On hold (CEO decision, Oct 19)", source="", now="Ryno put visitor measurement on hold on Oct 19. Nothing reads, fetches or counts traffic until he decides.")
            else:
                r = reach[-1]
                met = r["uniques_14d"] >= 50 and r["stars"] >= 5 and len(r["outside_referrers"]) >= 2
                row.update(status="met" if met else "in progress",
                           now=f'{r["uniques_14d"]} unique repo visitors in the 14 days to {nice(r["date"])}, {r["stars"]} stars, '
                               f'{len(r["outside_referrers"])} outside referrer domains. These are repo visitors, not site visitors.')
        elif g["id"] == "G2":
            n = len(cases) + len(arena) + len(challenges)
            row.update(status="met" if n >= g["goal"] else "in progress", now=f'{n} of {g["goal"]} entries ({n - g["baseline"]} new since {nice(start)}). New formats: none yet.')
        elif g["id"] == "G3":
            new = [u for u in updates if u["added"] >= start]
            fast = sum((datetime.fromisoformat(u["added"]) - datetime.fromisoformat(u["date"])).days <= 1 for u in new)
            demos = sum(1 for c in cases if c.get("update") in {u["id"] for u in new})
            met = new and fast == len(new) and demos >= 2
            row.update(status="met" if met else "in progress",
                       now=f'{fast} of {len(new)} new tracker items logged within 1 day since {nice(start)}; {demos} of 2 demos.')
        out.append(row)
    return out


def goals_html(m, src):
    if not m.get("goals"):
        return ""
    items = "".join(f'<li><strong>{e(g["id"])} {e(g["title"])}: {e(g["status"])}</strong>. {e(g["now"])} '
                    f'<span class="def">Target by Nov 18: {e(g["target"])}. {" Source: " + ", ".join(src(s.strip()) for s in g["source"].split(",")) if g["source"] else ""}</span></li>' for g in m["goals"])
    return (f'<h2 id="goals">Month-1 goals</h2><p>Strategy\'s 3 goals for Oct 19 to Nov 18, approved by Ryno and tracked from records. '
            f'Defined in {src("data/goals.json")}.</p><ul class="sprints">{items}</ul>')


def hm(m):
    return f"{m // 60} h {m % 60} min" if m >= 60 else f"{m} min"


def render(m, up="../"):
    t, src = m["totals"], lambda f: f'<a href="{SRC}{f}">{f}</a>'
    big = [(t["prs"], "PRs merged", "Merged PRs with a Maker line, since the first on Oct 15.", "data/wins.json"),
           (hm(t["open_to_merge_min"]), "median open to merge", "Median time from a PR opening to its merge. Bots open a PR when the work is done, so this is review and CI time, not build time.", "data/wins.json"),
           (t["main_failures"], "failures on main", "Failed CI or Pages runs on main since the run records start.", "data/ci.json"),
           (t["ci_catches"], "CI catches before merge", "Failed CI runs on bot PR branches. Each is a mistake stopped before merge.", "data/ci.json"),
           (t["reverts"], "reverts", "Merged PRs titled Revert.", "data/wins.json"),
           (t["aars"], "AARs", f"After-action reviews; {t['escaped']} were incidents or data corrections.", "data/aars.json"),
           (t["blocks"], "Blocks upheld", "A reviewer stopped a merge and was proven right.", "data/aars.json"),
           (m["pace"]["mode"], "pace", f'Slowed until {m["pace"]["clean_needed"]} clean PRs; {m["pace"]["clean_prs"]} so far.' if m["pace"]["mode"] == "slowed" else "Up to 18 merged PRs a day.", "data/tempo.json")]
    out = ['<ul class="nums">' + "".join(f'<li><strong>{e(str(v))}</strong> <span class="lbl-n">{e(l)}</span><span class="def">{e(d)} Source: {src(f)}</span></li>' for v, l, d, f in big) + "</ul>"]
    out.append(goals_html(m, src))  # i60
    n, newest = m["days_of_history"], nice(m["newest_day"])
    if m["trends"]:
        p = nice(m["days"][-2]["date"])
        arrow = {"up": "\u2191 up", "down": "\u2193 down", "flat": "\u2192 flat", "n/a": "n/a"}
        rows = "".join(f'<tr><th scope="row">{e(x["label"])}</th><td>{"" if x["prev"] is None else x["prev"]}</td><td>{"" if x["new"] is None else x["new"]}</td>'
                       f'<td>{arrow[x["direction"]]}{", " + x["verdict"] if x["verdict"] else ""}</td></tr>' for x in m["trends"])
        out.append(f'<h2 id="trends">Trends</h2><p>{newest} so far against {p}. Counts that depend on volume are per 10 merged PRs. '
                   f'<strong>Only {n} days of history</strong>: one AAR moves a day\'s rate a lot, so read these as early signals, not proof. '
                   f'"Better" or "worse" appears only where the right direction is clear.</p>'
                   f'<div class="scroll fit"><table class="trend"><caption>Newest day against the day before</caption><thead><tr><th scope="col">Metric</th>'
                   f'<th scope="col">{p}</th><th scope="col">{newest} (so far)</th><th scope="col">Direction</th></tr></thead><tbody>{rows}</tbody></table></div>'
                   + (f'<p class="warn-t"><strong>Getting worse:</strong> {e(", ".join(x["label"] for x in m["trends"] if x["verdict"] == "worse"))}. '
                      'Advisor turns a worsening trend into a rule or a check at the Friday retro.</p>' if m["worsening"] else "<p>Nothing is getting worse.</p>"))
    top = max(x["prs"] for x in m["days"]) or 1
    rows = "".join(f'<tr><th scope="row">{nice(x["date"])}</th><td><span class="bar" style="--w:{round(100 * x["prs"] / top)}" aria-hidden="true"></span>{x["prs"]}</td>'
                   f'<td>{x["ci_catches"] if x["ci_recorded"] else "no record"}</td>'
                   f'<td>{x["aars"]} ({x["escaped"]})</td></tr>' for x in m["days"])
    out.append(f'<h2 id="days">By day</h2><div class="scroll fit"><table class="days"><caption>Each day from the records (ET). Slips are incidents and data corrections.</caption><thead><tr><th scope="col">Day</th>'
               f'<th scope="col">PRs</th><th scope="col">CI catches</th><th scope="col">AARs (slips)</th></tr></thead><tbody>{rows}</tbody></table></div>'
               f'<p class="sub">CI run records start {e(m["ci_window_start"][:16].replace("T", " "))} ET, so the first day\'s CI count is partial.</p>')
    out.append('<h2 id="sprints">Sprint durations</h2><p>From the first PR opening to the last PR merging, for completed sprints whose retro names its PR range.</p><ul class="sprints">'
               + "".join(f'<li><strong>{e(s["title"])}</strong>: {s["prs"]} PRs in {hm(s["minutes"])}</li>' for s in m["sprints"]) + "</ul>")
    out.append(f'<p class="sub">Generated by {src("scripts/metrics.py")} into {src("data/metrics.json")} from records only, as of the newest merged PR ({e(m["as_of"][:16].replace("T", " "))} ET). '
               f'Nothing is projected or estimated.</p>')
    return "".join(out)


def write():
    load = lambda n: json.loads((ROOT / f"data/{n}.json").read_text())
    m = derive(load("wins"), load("aars"), load("ci"), load("ideas"), load("refusals"), load("tempo"),
               load("blast_checks") if (ROOT / "data/blast_checks.json").exists() else (),  # i46: Atlas's predictions checked after merge
               month1_inputs(load, lambda n: (ROOT / f"data/{n}.json").exists()))  # i60
    (ROOT / "data/metrics.json").write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    write()
