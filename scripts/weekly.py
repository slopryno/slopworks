"""Weekly recap (i42) and per-week pages (d3 / level-up 2.5): built only from real records.
Analyst and Comms (c297, c298): a week still running shows "days 1 to N so far" with its dates and counts
only, never a projected total; it turns final once a record lands on day 8. Weeks start on the first
merged PR. "So far" runs to the newest record, not the clock, so the build stays repeatable.
Permanent pages live at /weekly/YYYY-wNN/ (ISO week of that week's start day) for sharing.
"""
from datetime import date, timedelta
from html import escape as e

DAY = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def nice(d):
    return f"{DAY[d.weekday()]} {MON[d.month - 1]}\u00a0{d.day}"


def week_key(start):
    """Permanent URL segment: ISO week of the week's start day, e.g. 2026-w42."""
    y, w, _ = start.isocalendar()
    return f"{y}-w{w:02d}"


def weeks(launch, asof):
    """[(n, start, end, days_so_far, final)] from the launch date to the newest record date."""
    out, n, start = [], 1, launch
    while start <= asof:
        end = start + timedelta(days=6)
        final = asof > end
        out.append((n, start, end, 7 if final else (asof - start).days + 1, final))
        n, start = n + 1, end + timedelta(days=1)
    return out


def _pick(title, xs, empty, up):
    if not xs:
        return f'<li><strong>{title}:</strong> <span class="sub">{empty}</span></li>'
    x = max(xs, key=lambda x: (len(x.get("children", [])), x["date"], x["time"] or ""))
    return f'<li><strong>{title}:</strong> {e(x.get("short") or x["title"])} <a href="{e(x["link"](up))}">{e(x["cue"])}</a></li>'


def _updates_block(ups, s, t, up):
    """This week in Grok Bot: confirmed updates whose added date falls in the week (i53 gap)."""
    inside = lambda d: s <= date.fromisoformat(d[:10]) <= t
    confirmed = [u for u in ups if u.get("status") == "confirmed" and inside(u.get("added") or u["date"])]
    confirmed.sort(key=lambda u: (u.get("added") or u["date"], u["date"]), reverse=True)
    if not confirmed:
        return ('<h3>This week in Grok Bot</h3>'
                '<p class="sub">No confirmed updates added this week. '
                f'<a href="{up}updates/">All updates</a></p>')
    items = "".join(
        f'<li><time datetime="{e(u["date"])}">{e(u["date"])}</time> '
        f'<a href="{up}updates/{e(u["id"])}/">{e(u["title"])}</a></li>'
        for u in confirmed)
    return (f'<h3>This week in Grok Bot</h3>'
            f'<p class="sub">{len(confirmed)} confirmed '
            f'{"update" if len(confirmed) == 1 else "updates"} added this week. '
            f'<a href="{up}updates/">All updates</a></p>'
            f'<ul class="news">{items}</ul>')


def render_week(b, n, s, t, days, final, items, wins, ups, iss, aars, objectives, up="../", *, link_self=False):
    """One week panel. link_self=True makes the title a link to the permanent page (index only)."""
    inside = lambda d, s, t: s <= date.fromisoformat(d[:10]) <= t
    newest = max(items, key=lambda x: (x["date"], x["time"] or ""))
    stamp = f'{newest["date"]} {newest["time"]} ET' if newest.get("time") else newest["date"]
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
    latest = lambda xs: [max(xs, key=lambda x: (x["date"], x["time"] or ""))] if xs else []
    iss_line = ('<li><strong>Issue tracked:</strong> <span class="sub">none added or fixed this week</span></li>' if not issues else
                "".join(f'<li><strong>Issue tracked:</strong> {e(i["title"])} ({e(i["state"])}) <a href="{up}issues/#e{e(i["id"])}">known issue</a></li>' for i in issues[-1:]))
    day = lambda d: d.isoformat()
    by_day = "".join(
        f'<li><strong>{nice(d)}</strong>: {n_} merged {"PR" if n_ == 1 else "PRs"}, {k} {"AAR" if k == 1 else "AARs"}</li>'
        for d in (s + timedelta(days=j) for j in range(days))
        for n_, k in [(sum((w.get("merged") or w["date"])[:10] == day(d) for w in wins), sum(x["date"] == day(d) for x in aars))])
    nxt = "".join(f'<li>{e(o["role"])}: {e(o["objective"])}</li>' for o in objectives) or '<li class="sub">No open objectives on record.</li>'
    key = week_key(s)
    title = f"Week {n}: {nice(s)} to {nice(t)}"
    if link_self:
        heading = f'<h2 id="w{n}"><a href="{e(key)}/">{e(title)}</a></h2>'
        share = f'<p class="sub"><a href="{e(key)}/">Permanent page</a> · shareable link for this week</p>'
    else:
        heading = f'<h2 id="w{n}">{e(title)}</h2>'
        share = ""
    return (
        f'<section class="panel week" aria-labelledby="w{n}"><p class="kicker">{"\u2713 " if final else ""}{label}</p>'
        + heading + share
        + ("" if final else f'<p class="sub">Partial week, counted to the newest record ({e(stamp)}). Nothing here is projected to a full week.</p>')
        + _updates_block(ups, s, t, up)
        + '<ul class="status wk">' + "".join(f"<li><strong>{v}</strong> {l}</li>" for v, l in counts) + "</ul>"
        + f'<h3>By day</h3><ul class="byday">{by_day}</ul><h3>Highlights</h3>'
        + "<ul class=\"recap\">" + _pick("Top accomplishment (the completed sprint with the most PRs)", sprints, "no sprint completed yet", up)
        + _pick("Discovery (newest research round)", latest(research), "no research round yet", up)
        + iss_line + _pick("Lesson (newest after-action review)", latest(lessons), "none needed this week", up)
        + "</ul>" + (f"<h3>Next objectives</h3><ul>{nxt}</ul>" if not final else "") + "</section>")


def iter_weeks(items, wins):
    """[(n, start, end, days, final, key)] newest first."""
    if not wins:
        return []
    launch = date.fromisoformat(min(w["date"] for w in wins))
    newest = max(items, key=lambda x: (x["date"], x["time"] or ""))
    asof = date.fromisoformat(newest["date"])
    return [(n, s, t, days, final, week_key(s)) for n, s, t, days, final in reversed(weeks(launch, asof))]


def render(b, items, wins, ups, iss, aars, objectives, up="../"):
    """Index: every week as a panel, with a link to its permanent page."""
    if not wins:
        return '<p class="empty">No weeks yet. The first one starts with the first merged PR.</p>'
    return "".join(
        render_week(b, n, s, t, days, final, items, wins, ups, iss, aars, objectives, up, link_self=True)
        for n, s, t, days, final, _ in iter_weeks(items, wins))


def render_page(b, n, s, t, days, final, items, wins, ups, iss, aars, objectives):
    """Body for /weekly/YYYY-wNN/ (up is ../../ from that slug depth)."""
    return render_week(b, n, s, t, days, final, items, wins, ups, iss, aars, objectives, up="../../", link_self=False)
