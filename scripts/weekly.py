"""Weekly recap (i42): one section per week, built only from real records. Analyst and Comms decided (c297, c298):
a week still running shows "days 1 to N so far" with its dates and counts only, never a projected total; it turns final
once a record lands on day 8. Weeks start on the first merged PR. "So far" runs to the newest record, not the clock,
so the build stays repeatable.
"""
from datetime import date, timedelta
from html import escape as e

DAY = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def nice(d):
    return f"{DAY[d.weekday()]} {MON[d.month - 1]}\u00a0{d.day}"


def weeks(launch, asof):
    """[(n, start, end, days_so_far, final)] from the launch date to the newest record date."""
    out, n, start = [], 1, launch
    while start <= asof:
        end = start + timedelta(days=6)
        final = asof > end
        out.append((n, start, end, 7 if final else (asof - start).days + 1, final))
        n, start = n + 1, end + timedelta(days=1)
    return out


def render(b, items, wins, ups, iss, aars, objectives, up="../"):
    if not wins:
        return '<p class="empty">No weeks yet. The first one starts with the first merged PR.</p>'
    launch = date.fromisoformat(min(w["date"] for w in wins))
    newest = max(items, key=lambda x: (x["date"], x["time"] or ""))
    asof = date.fromisoformat(newest["date"])
    stamp = f'{newest["date"]} {newest["time"]} ET' if newest.get("time") else newest["date"]
    inside = lambda d, s, t: s <= date.fromisoformat(d[:10]) <= t
    out = []
    for n, s, t, days, final in reversed(weeks(launch, asof)):
        wk = [x for x in items if inside(x["date"], s, t)]
        prs = [w for w in wins if inside(w.get("merged") or w["date"], s, t)]
        sprints = [x for x in wk if x.get("capped") and x.get("cue") == "retro"]
        research = [x for x in wk if "research" in x["types"] and not x.get("demo")]
        lessons = [x for x in wk if "lesson" in x["types"]]
        decisions = [x for x in wk if "decision" in x["types"]]
        added = [u for u in ups if inside(u["added"], s, t)]
        issues = [i for i in iss if inside(i["date"], s, t) or (i.get("fixed_date") and inside(i["fixed_date"], s, t))]
        label = "Final" if final else f"Days 1 to {days} so far"
        counts = [(len(prs), "merged PRs"), (len(sprints), "sprints completed"), (len(decisions), "CEO decisions"),
                  (len(research), "research rounds"), (len(lessons), "lessons written up"), (len(added), "Grok Bot updates added")]
        def pick(title, xs, empty):
            if not xs:
                return f'<li><strong>{title}:</strong> <span class="sub">{empty}</span></li>'
            x = max(xs, key=lambda x: (len(x.get("children", [])), x["date"], x["time"] or ""))
            return f'<li><strong>{title}:</strong> {e(x.get("short") or x["title"])} <a href="{e(x["link"](up))}">{e(x["cue"])}</a></li>'
        latest = lambda xs: [max(xs, key=lambda x: (x["date"], x["time"] or ""))] if xs else []
        iss_line = ('<li><strong>Issue tracked:</strong> <span class="sub">none added or fixed this week</span></li>' if not issues else
                    "".join(f'<li><strong>Issue tracked:</strong> {e(i["title"])} ({e(i["state"])}) <a href="{up}issues/#e{e(i["id"])}">known issue</a></li>' for i in issues[-1:]))
        day = lambda d: d.isoformat()
        by_day = "".join(
            f'<li><strong>{nice(d)}</strong>: {n} merged {"PR" if n == 1 else "PRs"}, {k} {"AAR" if k == 1 else "AARs"}</li>'
            for d in (s + timedelta(days=j) for j in range(days))
            for n, k in [(sum((w.get("merged") or w["date"])[:10] == day(d) for w in wins), sum(x["date"] == day(d) for x in aars))])
        nxt = "".join(f'<li>{e(o["role"])}: {e(o["objective"])}</li>' for o in objectives) or '<li class="sub">No open objectives on record.</li>'
        out.append(
            f'<section class="panel week" aria-labelledby="w{n}"><p class="kicker">{"\u2713 " if final else ""}{label}</p>'
            f'<h2 id="w{n}">Week {n}: {nice(s)} to {nice(t)}</h2>'
            + ("" if final else f'<p class="sub">Partial week, counted to the newest record ({e(stamp)}). Nothing here is projected to a full week.</p>')
            + '<ul class="status wk">' + "".join(f"<li><strong>{v}</strong> {l}</li>" for v, l in counts) + "</ul>"
            + f'<h3>By day</h3><ul class="byday">{by_day}</ul><h3>Highlights</h3>'
            + "<ul class=\"recap\">" + pick("Top accomplishment (the completed sprint with the most PRs)", sprints, "no sprint completed yet")
            + pick("Discovery (newest research round)", latest(research), "no research round yet")
            + iss_line + pick("Lesson (newest after-action review)", latest(lessons), "none needed this week")
            + "</ul>" + (f"<h3>Next objectives</h3><ul>{nxt}</ul>" if not final else "") + "</section>")
    return "".join(out)
