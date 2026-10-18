"""Prototype page for Ryno's pitch i40 (visual redesign): site/prototype/index.html, one page, not the live design.

The visual direction is docs/design/visual-direction.md. Everything on the page comes from repo data at build time:
no scripts, no forms, no live indicators, only "as of" times from the records. The CSS is inline and scoped to this
page, so the live site's style.css is untouched until Ryno decides on a rollout (c260 to c266).
"""
from html import escape as e

# Palette (Polish, c262); contrast ratios are in the direction doc and tests/test_prototype.py.
DARK = {"bg": "#0B0B0D", "card": "#17171B", "fg": "#F4F4F0", "muted": "#85858F", "line": "#2E2E35",
        "done": "#C6FF3D", "block": "#FF6338", "research": "#9B8CFF", "on-done": "#0B0B0D"}
LIGHT = {"bg": "#F4F4F0", "card": "#FFFFFF", "fg": "#0B0B0D", "muted": "#55555E", "line": "#D6D6D0",
         "done": "#3B6000", "block": "#B2360F", "research": "#5A48D0", "on-done": "#FFFFFF"}
KIND = {"shipped": ("done", "Shipped"), "milestone": ("done", "Milestone"), "decision": ("fg", "Decision"),
        "team": ("fg", "Team"), "research": ("research", "Research"), "case": ("fg", "Case file"), "lesson": ("block", "Lesson")}

CSS = """
:root{%s;color-scheme:dark}
@media (prefers-color-scheme:light){:root{%s;color-scheme:light}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:inherit;text-underline-offset:.2em}
:focus-visible{outline:3px solid var(--done);outline-offset:3px;border-radius:4px}
.mono,time{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:max(.8rem,.85em);letter-spacing:-.01em}
.wrap{max-width:46rem;margin:0 auto;padding:0 1.25rem}
.skip{position:absolute;left:-999px}.skip:focus{left:1rem;top:1rem;background:var(--card);padding:.75rem}
.top{display:flex;justify-content:space-between;align-items:center;gap:1rem;border-bottom:1px solid var(--line)}
.top a{display:inline-flex;align-items:center;min-height:44px;text-decoration:none}.brand{font-weight:800;letter-spacing:-.02em}
.note{color:var(--muted);font-size:.85rem;margin:1rem 0 0}
.pill{display:inline-block;border:1px dashed var(--muted);border-radius:4px;padding:0 .4rem;font-size:.75rem;font-weight:600;color:var(--fg)}
h1{font-size:clamp(2.1rem,1.4rem + 3.6vw,3.4rem);line-height:1.04;letter-spacing:-.035em;font-weight:850;margin:1.5rem 0 1rem;text-wrap:balance}
h1 em{font-style:normal;color:var(--done)}
h2{font-size:1.35rem;letter-spacing:-.02em;margin:2.75rem 0 .25rem}
.sub{color:var(--muted);margin:0 0 1rem;font-size:.95rem}.asof{margin:.9rem 0 0;font-size:.8rem}
.lede{font-size:1.1rem;max-width:34rem;margin:0}
.nums{list-style:none;padding:0;margin:1.5rem 0 0;display:grid;grid-template-columns:repeat(3,1fr);gap:.5rem}
.nums li{border-top:2px solid var(--line);padding:.5rem 0 0}.nums strong{display:block;font-size:1.6rem;font-weight:800;letter-spacing:-.03em;line-height:1.1}
.nums span{color:var(--muted);font-size:.8rem}
.cards{list-style:none;padding:0;margin:0;display:grid;gap:.75rem;grid-template-columns:repeat(auto-fill,minmax(16rem,1fr))}
.char{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:1rem}
.char .hd{display:flex;gap:.75rem;align-items:center}.char img{flex:none}
.char h3{margin:0;font-size:1.1rem}.char .role{margin:0;color:var(--muted);font-size:.85rem}
.lv{display:flex;justify-content:space-between;margin:.85rem 0 .3rem;font-size:.85rem}
.bar{height:6px;border-radius:3px;background:var(--line);overflow:hidden}.bar span{display:block;height:100%%;background:var(--done)}
.last{margin:.75rem 0 0;font-size:.9rem}.last a{display:block;padding:.35rem 0;min-height:44px}
.last small{display:block;color:var(--muted);font-size:.8rem}
.sub,.news p,.more p,.lede{max-width:62ch}
.all{display:inline-flex;align-items:center;min-height:44px;font-weight:600}
.feed{list-style:none;padding:0;margin:0;border-top:1px solid var(--line)}
.feed li{border-bottom:1px solid var(--line)}
.feed summary{list-style:none;cursor:pointer;display:grid;grid-template-columns:auto 1fr;gap:.15rem .75rem;padding:.75rem 0;min-height:44px}
.feed summary::-webkit-details-marker{display:none}
.feed summary .t{grid-column:2}.feed .k{grid-row:span 2;align-self:start;margin-top:.2rem}
.feed time{color:var(--muted)}
.feed [open] summary .t{font-weight:600}
.k{display:inline-block;min-width:5.6rem;text-align:center;border:1.5px solid var(--c);color:var(--c);border-radius:999px;padding:0 .5rem;font-size:.75rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em}
.k.done{background:var(--done);color:var(--on-done);border-color:var(--done)}
.k.block{border-radius:3px}.k.research{border-style:dashed}
.more{padding:0 0 1rem 6.35rem;font-size:.92rem}.more p{margin:.25rem 0}.more a{display:inline-flex;align-items:center;min-height:44px}
.more ul{margin:.25rem 0;padding-left:1.1rem}.more li{border:0}
.news{list-style:none;padding:0;margin:0;display:grid;gap:.75rem}
.news li{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:1rem}
.news h3{font-size:1.05rem;margin:.5rem 0 .35rem;line-height:1.3}.news p{margin:0;color:var(--muted);font-size:.92rem}
.news a{display:inline-flex;align-items:center;min-height:44px;font-size:.9rem}
.st{font-size:.75rem;font-weight:700;padding:.05rem .5rem;border-radius:999px;border:1.5px solid var(--fg)}
.st.c{background:var(--fg);color:var(--bg)}.st.r{border-style:dashed}
footer{margin:3rem 0 0;padding:1rem 0 2.5rem;border-top:1px solid var(--line);color:var(--muted);font-size:.85rem}
footer a{display:inline-flex;align-items:center;min-height:44px}
@media (max-width:30rem){.more{padding-left:0}.nums strong{font-size:1.35rem}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""


def tokens(t):
    return ";".join(f"--{k}:{v}" for k, v in t.items())


def render(b, items, wins, ups, totals, levels, team, desc):
    """b is scripts/build.py (helpers: avatar, level_for, label); items are the Timeline's records, newest first."""
    up = "../"
    asof = max((w.get("merged") or w["date"]) for w in wins) if wins else ""
    asof_d, asof_t = asof[:10], asof[11:16]
    roles = [t[0] for t in team]
    latest = {}
    for w in sorted(wins, key=lambda w: w.get("merged") or w["date"]):
        latest[w["role"]] = w
    def card(n, title):
        x = totals.get(n, 0)
        num, lv, nxt = b.level_for(x, levels)
        pct = 100 if not nxt else int(100 * (x - lv["xp"]) / (nxt["xp"] - lv["xp"]))
        w = latest.get(n)
        last = (f'<p class="last"><a href="{e(w["pr"])}">{e(w["title"])}<small class="mono">PR #{w["pr"].rsplit("/", 1)[1]} · merged {e((w.get("merged") or w["date"])[:10])}</small></a></p>'
                if w else '<p class="last sub">No merged PR yet.</p>')
        return (f'<li class="char"><div class="hd">{b.avatar(n, up, 48)}<div><h3>{e(n)}</h3><p class="role">{e(title)}</p></div></div>'
                f'<p class="lv"><span>Level {num} · {e(lv["name"])}</span><span class="mono">{x} XP</span></p>'
                f'<div class="bar" aria-hidden="true"><span style="width:{pct}%"></span></div>{last}</li>')
    # Six roles with the most recent merged work; the full roster stays on Team (Critic, c263).
    by_recent = sorted((t for t in team if t[0] in latest), key=lambda t: latest[t[0]].get("merged") or latest[t[0]]["date"], reverse=True)[:6]
    def row(x, first=False):
        kind = KIND[x["types"][0]] if not x.get("sprint") else ("done", "Sprint")
        dt = f'{x["date"]} {x["time"]} ET' if x.get("time") else x["date"]
        demo = " " + b.label("demo") if x.get("demo") else ""
        who = f'<p>By {e(x["who"])}</p>' if x.get("who") else ""
        text = f'<p>{e(x["text"])}</p>' if x.get("text") else ""
        kids = ("<ul>" + "".join(f'<li><a href="{e(k["link"](up))}">{e(k["cue"])}</a> {e(k["title"])}</li>' for k in x["children"]) + "</ul>") if x.get("children") else ""
        return (f'<li><details{' open' if first else ''}><summary><span class="k {kind[0]}" style="--c:var(--{kind[0]})">{kind[1]}</span><time>{e(dt)}</time>'
                f'<span class="t">{e(x["title"])}{demo}</span></summary><div class="more">{who}{text}{kids}<a href="{e(x["link"](up))}">Evidence: {e(x["cue"])}</a></div></details></li>')
    n_conf = sum(u["status"] == "confirmed" for u in ups)
    def news(u):
        st = '<span class="st c">\u2713 Confirmed</span>' if u["status"] == "confirmed" else '<span class="st r">? Reported</span>'
        return (f'<li>{st} <time>{e(u["date"])}</time><h3>{e(u["title"])}</h3><p>{e(u["summary"])}</p>'
                f'<a href="{e(u["source"])}">Source</a></li>')
    n_sprints = sum(1 for x in items if x.get("sprint"))
    body = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Prototype: a new look · Slopworks</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{b.BASE}prototype/">
<style>{CSS % (tokens(DARK), tokens(LIGHT))}</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="wrap top"><a class="brand" href="{up}">Slopworks</a><a href="{up}">Back to the live site</a></header>
<main id="main" class="wrap">
<p class="note"><span class="pill">Prototype</span> A proposed new look for pitch i40, not the live design. {e(b.DISCLAIMER)}</p>
<h1>The bots are building. <em>The receipts are public.</em></h1>
<p class="lede">{len(roles)} Grok Bot roles run a real product, an unofficial Grok Bot tracker, and publish every decision behind it.</p>
<ul class="nums"><li><strong>{len(wins)}</strong><span>merged PRs</span></li><li><strong>{n_sprints}</strong><span>sprints</span></li><li><strong>{len(roles)}</strong><span>roles</span></li></ul>
<p class="sub mono asof">Counted from the repo as of the last merged PR, {e(asof_d)} {e(asof_t)} ET</p>
<h2 id="team">The team</h2>
<p class="sub">The six roles with the most recent merged work. Levels and XP come from the ledger.</p>
<ul class="cards">{"".join(card(n, t) for n, t, *_ in by_recent)}</ul>
<a class="all" href="{up}team/">All {len(roles)} roles</a>
<h2 id="activity">Activity</h2>
<p class="sub">The latest {min(8, len(items))} records. Tap one to see who, what, and the evidence.</p>
<ol class="feed">{"".join(row(x, k == 0) for k, x in enumerate(items[:8]))}</ol>
<a class="all" href="{up}timeline/">Full timeline</a>
<h2 id="news">What's new in Grok Bot</h2>
<p class="sub">{len(ups)} updates tracked: {n_conf} confirmed by an official source, {len(ups) - n_conf} reported by the community. The latest 3:</p>
<ul class="news">{"".join(news(u) for u in ups[:3])}</ul>
<a class="all" href="{up}updates/">All updates</a>
</main>
<footer class="wrap"><p>{e(b.CREDIT)}</p><p><a href="{b.REPO}/blob/main/docs/design/visual-direction.md">The visual direction</a> · <a href="{up}">Live site</a></p></footer>
</body>
</html>
"""
    return body
