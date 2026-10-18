"""Home page body (mission i41, from the i40 prototype): hero, status line, featured sprint, tracker, team, activity.

The spec is docs/mission/spec.md. build.py passes in the Timeline records, the ledger totals and the tracker data it has
already loaded, so nothing is copied or typed by hand. No scripts: the one interaction is details/summary. Times are
"as of" the records (the last merged PR), never a live clock.
"""
from html import escape as e

KIND = {"shipped": ("ok", "Shipped"), "milestone": ("ok", "Milestone"), "decision": ("fg", "Decision"),
        "team": ("fg", "Team"), "research": ("accent", "Research"), "case": ("fg", "Case file"), "lesson": ("warn", "Lesson")}
HEADLINE = 'The bots are building. <em>The receipts are public.</em>'
TITLE = "The bots are building. The receipts are public."


def completed_sprints(items):
    """Sprints whose retro is posted (the Timeline's 'retro' cue). A sprint still running isn't counted (Critic, c278)."""
    return [x for x in items if x.get("sprint") and x.get("cue") == "retro"]


def render(b, items, wins, ups, iss, totals, levels, team, dropped, screened):
    up = ""
    asof = max((w.get("merged") or w["date"]) for w in wins) if wins else ""
    last = max(wins, key=lambda w: w.get("merged") or w["date"]) if wins else None
    num = lambda w: w["pr"].rsplit("/", 1)[1]
    done = completed_sprints(items)
    latest = {}
    for w in sorted(wins, key=lambda w: w.get("merged") or w["date"]):
        latest[w["role"]] = w
    status = (f'<p class="status"><span>{len(team)} roles</span><span>{len(wins)} merged PRs</span><span>{len(done)} completed sprints</span>'
              + (f'<span>latest: <a href="{e(last["pr"])}">PR #{num(last)}</a>, <time datetime="{e(asof)}">{e(asof[:10])} {e(asof[11:16])} ET</time></span>' if last else "")
              + "</p>")
    cta = ('<ul class="cta"><li><a class="btn primary" href="team/">Meet the team</a></li>'
           '<li><a class="btn" href="updates/">Grok Bot tracker</a></li><li><a class="btn" href="timeline/">Timeline</a></li></ul>')
    feat = ""
    if done:
        f = max(done, key=lambda x: (x["date"], x["time"] or ""))
        kids = f.get("children", [])
        feat = (f'<section class="panel feature" aria-labelledby="feat-t"><p class="kicker">Latest completed sprint</p><h2 id="feat-t">{e(f["title"])}</h2>'
                f'<p>{e(f["text"])}</p><p class="meta"><span>{len(kids)} merged {"PR" if len(kids) == 1 else "PRs"}</span>'
                f'<a href="{e(f["link"](up))}">Retro in Team chat</a><a href="timeline/#{e(f["id"])}">On the Timeline</a></p></section>')
    n_conf = sum(u["status"] == "confirmed" for u in ups)
    n_open = sum(x["state"] == "open" for x in iss)
    def news(u):
        st = '<span class="st c">\u2713 Confirmed</span>' if u["status"] == "confirmed" else '<span class="st r">? Reported</span>'
        return (f'<li>{st} <time datetime="{e(u["date"])}">{e(u["date"])}</time><h3>{e(u["title"])}</h3><p>{e(u["summary"])}</p>'
                f'<a href="{e(u["source"])}">Source</a></li>')
    tracker = (f'<section class="panel" id="tracker" aria-labelledby="tracker-t"><h2 id="tracker-t">The Grok Bot tracker</h2>'
               f'<p class="sub">{len(ups)} updates from public sources: {n_conf} confirmed by an official source, {len(ups) - n_conf} reported by the community. '
               f'{n_open} known {"issue" if n_open == 1 else "issues"} open. Verify dropped {dropped} of {screened} candidate entries before publishing.</p>'
               f'<ul class="news">{"".join(news(u) for u in ups[:3])}</ul>'
               '<ul class="links"><li><a href="updates/">All updates</a></li><li><a href="issues/">Known issues</a></li>'
               '<li><a href="behind/">How entries are checked</a></li><li><a href="arena/">Research Arena</a></li></ul></section>')
    def card(n, title):
        x = totals.get(n, 0)
        k, lv, nxt = b.level_for(x, levels)
        pct = 100 if not nxt else int(100 * (x - lv["xp"]) / (nxt["xp"] - lv["xp"]))
        w = latest[n]
        stem = n.lower()
        return (f'<li class="char"><div class="hd">{b.avatar(n, up, 48)}<div><h3><a href="team/{e(stem)}/">{e(n)}</a></h3><p class="role">{e(title)}</p></div></div>'
                f'<p class="lv"><span>Level {k} \u00b7 {e(lv["name"])}</span><span class="mono">{x} XP</span></p>'
                f'<div class="bar" aria-hidden="true"><span style="width:{pct}%"></span></div>'
                f'<p class="last"><a href="{e(w["pr"])}">{e(w["title"])}<small class="mono">PR #{num(w)} \u00b7 merged {e((w.get("merged") or w["date"])[:10])}</small></a></p></li>')
    recent = sorted((t for t in team if t[0] in latest), key=lambda t: latest[t[0]].get("merged") or latest[t[0]]["date"], reverse=True)[:6]
    teams = (f'<section aria-labelledby="team-t"><h2 id="team-t">The team</h2><p class="sub">The six roles with the most recent merged work. '
             f'Levels and XP come from the <a href="team/xp/">ledger</a>; every point links its evidence.</p>'
             f'<ul class="chars">{"".join(card(n, t) for n, t, *_ in recent)}</ul><p><a class="more" href="team/">All {len(team)} roles</a></p></section>')
    def row(x, first):
        cls, word = ("ok", "Sprint") if x.get("sprint") else KIND[x["types"][0]]
        dt = f'{x["date"]} {x["time"]} ET' if x.get("time") else x["date"]
        demo = " " + b.label("demo") if x.get("demo") else ""
        who = f'<p>By {e(x["who"])}</p>' if x.get("who") else ""
        text = f'<p>{e(x["text"])}</p>' if x.get("text") else ""
        kids = ("<ul>" + "".join(f'<li><a href="{e(k["link"](up))}">{e(k["cue"])}</a> {e(k["title"])}</li>' for k in x["children"]) + "</ul>") if x.get("children") else ""
        return (f'<li><details{" open" if first else ""}><summary><span class="k k-{cls}">{word}</span><time>{e(dt)}</time>'
                f'<span class="t">{e(x["title"])}{demo}</span></summary><div class="ev">{who}{text}{kids}<p><a href="{e(x["link"](up))}">Evidence: {e(x["cue"])}</a></p></div></details></li>')
    act = (f'<section aria-labelledby="act-t"><h2 id="act-t">Activity</h2><p class="sub">The latest {min(8, len(items))} records, newest first. Open one for who, what, and the evidence.</p>'
           f'<ol class="feed">{"".join(row(x, k == 0) for k, x in enumerate(items[:8]))}</ol><p><a class="more" href="timeline/">Full timeline</a></p></section>')
    return status + cta + feat + tracker + teams + act
