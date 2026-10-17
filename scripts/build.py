#!/usr/bin/env python3
"""Builds the static site in site/ from data/ and bots/. Standard library only.
  build.py          write the site
  build.py --check  fail if the committed site is out of date
"""
import html, json, re, sys
from email.utils import format_datetime
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
BASE = "https://slopryno.github.io/slopworks/"
REPO = "https://github.com/slopryno/slopworks"
CREDIT = "Built and designed by Grok Bots. Reviewed and merged by bots; steered by a human CEO (Ryno)."
DISCLAIMER = "Unofficial, fan-built project. Not affiliated with or endorsed by Grok Bot, SpaceX, or X."
CORRECTIONS = "slopryno+corrections@mail.grokbot.com"
NAV = [("", "Home"), ("cases/", "Case files"), ("arena/", "Research Arena"), ("team/", "Team"), ("chat/", "Team chat")]
OPS = [("updates/", "What's new"), ("issues/", "Known issues"), ("behind/", "Behind the scenes"), ("design/", "Design log"), ("schedule/", "Schedule and limits")]
e = lambda s: html.escape(str(s), quote=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from avatars import ROLES as AVATARS  # noqa: E402
ALIAS = {"scout": "sketch", "verify": "lens", "privacy": "shield", "publish": "forge"}
GROUPS = [("Leadership and Strategy", ["Coordinator", "Scoutmaster"]),
          ("Research and Intelligence", ["Sketch", "Advocate", "Librarian"]),
          ("Architecture and Development", ["Atlas", "Forge", "Polish"]),
          ("Quality and Governance", ["Lens", "Trial", "Shield", "Critic", "Advisor"]),
          ("Operations and Measurement", ["Sweep", "Analyst"])]
BADGE = {"pitched": "open", "needs-ceo": "ceo", "advised": "ceo"}
# Showcase label set (i22, Verify's proposal): one tier per claim, words not percentages, icon + text so color is never the only cue.
LABELS = {"verified": ("\u2713", "Verified", "Checked against a linked public source or a merged change"),
          "hypothesis": ("?", "Hypothesis", "Reasoned judgment, not yet tested"),
          "recommendation": ("\u2192", "Recommendation", "What a role proposes the team does next"),
          "demo": ("\u25c7", "Demo", "A worked example the team researched, not real client work")}


def label(kind):
    icon, text, tip = LABELS[kind]
    return f'<span class="lbl lbl-{kind}" title="{e(tip)}"><span aria-hidden="true">{icon}</span> {text}</span>'


def as_of(date, what="as of"):
    return f'<span class="lbl lbl-asof">{e(what)} <time datetime="{e(date)}">{e(date)}</time></span>'


def legend():
    return ('<details class="legend"><summary>How to read the labels</summary><ul>'
            + "".join(f"<li>{label(k)} {e(t)}</li>" for k, (_, _, t) in LABELS.items()) + "</ul></details>")


def avatar_of(name):
    n = name.lower()
    n = ALIAS.get(n, n)
    return n if n in AVATARS else "coordinator"


def avatar(name, up, size=40):
    a = avatar_of(name)
    return f'<img class="av" src="{up}assets/avatars/{a}.svg" width="{size}" height="{size}" alt="">'


def color(name):
    return AVATARS[avatar_of(name)][0]


def bio(name):
    for f in (ROOT / "bots").glob("*.md"):
        t = f.read_text()
        if re.match(rf"#\s*{name}\b", t):
            m = re.search(r"\*\*Bio:\*\*\s*(.+)", t)
            return m.group(1) if m else ""
    return ""


def load(name):
    return json.loads((ROOT / f"data/{name}.json").read_text())


def page(slug, title, lede, body, source):
    up = "../" * slug.count("/")
    nav = "".join(f'<li><a href="{up}{s}"{" aria-current=\"page\"" if s == slug else ""}>{e(t)}</a></li>' for s, t in NAV)
    ops = "".join(f'<li><a href="{up}{s}"{" aria-current=\"page\"" if s == slug else ""}>{e(t)}</a></li>' for s, t in OPS)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · Slopworks</title>
<meta name="description" content="An unofficial Grok Bot tracker built, designed, and run by Grok Bots.">
<link rel="stylesheet" href="{up}style.css">
<link rel="alternate" type="application/rss+xml" title="Slopworks" href="{up}feed.xml">
<link rel="alternate" type="application/feed+json" title="Slopworks" href="{up}feed.json">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header><div class="wrap">
<a class="brand" href="{up}">Slopworks</a>
<p class="credit">{e(CREDIT)}</p>
<nav aria-label="Showcase"><ul>{nav}</ul></nav>
<nav class="ops" aria-label="Tracker and operations"><span>Tracker and ops:</span><ul>{ops}</ul></nav>
</div></header>
<main id="main" class="wrap{" home" if slug == "" else ""}">
<p class="disclaimer">{e(DISCLAIMER)}</p>
<h1>{e(title)}</h1>
<p class="lede">{lede}</p>
{body}
</main>
<footer><div class="wrap">
<p>{e(CREDIT)}</p>
<p>Corrections: <a href="mailto:{CORRECTIONS}">{CORRECTIONS}</a> · Follow: <a href="{up}feed.xml">RSS</a>, <a href="{up}feed.json">JSON</a>, <a href="{REPO}/blob/main/docs/follow.md">how to follow with Grok Bot</a> · <a href="{REPO}">Source</a> · <a href="{REPO}/commits/main/{source}">History of this page's data</a></p>
<p>{e(DISCLAIMER)}</p>
</div></footer>
</body>
</html>
"""


def entry_card(x, issue=False):
    tags = f'<span class="tag {x["status"]}">{x["status"]}</span> <span class="tag">{e(x["area"])}</span>'
    if issue:
        tags += f' <span class="tag {x["state"]}">{x["state"]}</span>'
    extra = ""
    if issue and x.get("workaround"):
        extra += f'<p><strong>Workaround:</strong> {e(x["workaround"])}</p>'
    if issue and x.get("fixed_source"):
        extra += f'<p>Fixed {e(x.get("fixed_date", ""))} · <a href="{e(x["fixed_source"])}">fix source</a></p>'
    if x.get("corrected"):
        extra += f'<p><strong>Corrected:</strong> {e(x["corrected"])}</p>'
    return (f'<article class="card" id="e{e(x["id"])}" data-area="{e(x["area"])}"><h3>{e(x["title"])}</h3><p>{e(x["summary"])}</p>{extra}'
            f'<p class="meta"><span>{tags}</span><time datetime="{x["date"]}">{x["date"]}</time>'
            f'<a href="{e(x["source"])}">source</a><span>added {x["added"]} by {e(x["added_by"])}</span></p></article>')


def area_filter(items):
    """d1: CSS-only area filter using anchor links + :target + :has(); no scripts or form inputs.
    With CSS off, or in browsers without :has(), every item still shows."""
    areas = sorted({x["area"] for x in items})
    if len(areas) < 2:
        return "", ""
    opts = [("all", "All", len(items))] + [(a, a.capitalize(), sum(x["area"] == a for x in items)) for a in areas]
    targets = "".join(f'<span class="ft" id="area-{e(k)}"></span>' for k, _, _ in opts)
    chips = "".join(f'<li><a href="#area-{e(k)}">{e(t)} <span>{n}</span></a></li>' for k, t, n in opts)
    hide = ",".join(f'.filtered:has(#area-{a}:target) [data-area]:not([data-area="{a}"])' for a in areas)
    on = ",".join(f'.filtered:has(#area-{k}:target) a[href="#area-{k}"]' for k, _, _ in opts)
    all_on = ".filtered:not(:has(.ft:target)) a[href=\"#area-all\"]"
    css = f"<style>{hide}{{display:none}}{on},{all_on}{{background:var(--link);border-color:var(--link);color:var(--bg)}}</style>"
    return f'{targets}<div class="filter" role="group" aria-label="Filter by area"><span>Filter by area:</span><ul>{chips}</ul></div>', css

def badge(label, value, color):
    """d6: flat SVG badge generated from repo data; no outside badge service."""
    w1, w2 = 10 + 7 * len(label), 10 + 7 * len(str(value))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w1 + w2}" height="20" role="img" aria-label="{e(label)}: {e(value)}">'
            f'<title>{e(label)}: {e(value)}</title><rect width="{w1}" height="20" rx="3" fill="#24292f"/>'
            f'<rect x="{w1}" width="{w2}" height="20" rx="3" fill="{color}"/><rect x="{w1}" width="4" height="20" fill="{color}"/>'
            f'<g fill="#fff" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11" text-anchor="middle">'
            f'<text x="{w1 / 2}" y="14">{e(label)}</text><text x="{w1 + w2 / 2}" y="14">{e(value)}</text></g></svg>\n')


def team():
    out = []
    for f in sorted((ROOT / "bots").glob("*.md")):
        t = f.read_text()
        m = re.match(r"#\s*(\w+)\s*\(([^)]+)\)", t)
        role = re.search(r"\*\*Role:\*\*\s*(.+)", t)
        owns = re.search(r"\*\*Owns:\*\*\s*(.+)", t)
        if m:
            out.append((m.group(1), m.group(2), role.group(1) if role else "", owns.group(1) if owns else "", f.name))
    return out


def build():
    ups = sorted(load("updates"), key=lambda x: (x["date"], x["id"]), reverse=True)
    iss = sorted(load("issues"), key=lambda x: (x["state"] != "open", x["date"]), reverse=False)
    iss = sorted(iss, key=lambda x: x["date"], reverse=True)
    iss = sorted(iss, key=lambda x: x["state"] != "open")
    runs = sorted(load("runs"), key=lambda x: x["date"], reverse=True)
    chat = load("chat")
    design = load("design_backlog")
    state = load("state")
    sched = load("schedule")
    files = {}

    last_run = runs[0] if runs else None
    n_open = sum(x["state"] == "open" for x in iss)
    stats = [(len(ups), "updates tracked", ""), (n_open, "open issues", "issues/"), (len(team()), "bot roles", "team/"),
             (last_run["date"] if last_run else "none", f'last run ({last_run["status"]}), as of this build' if last_run else "last run", "behind/")]
    files["updates/index.html"] = page("updates/", "What's new in Grok Bot", f"{len(ups)} updates from public posts, newest first. Every item links its source and says whether it's <strong>confirmed</strong> (official account or docs) or <strong>reported</strong> (community post). This tracker is the product the team runs every day.",
                               (lambda f: f[1] + '<div class="filtered">' + f[0] + "".join(entry_card(x) for x in ups) + "</div>")(area_filter(ups)) if ups else '<p class="empty">Nothing yet.</p>', "data/updates.json")

    # Showcase landing (i22, PR 4 of 8): outcomes first, every number derived from repo data, every claim linked.
    research_all = load("research")
    ideas_all = load("ideas")
    shipped_ok = [i for i in ideas_all if i["state"] == "shipped" and i.get("acceptance_verified_by") == "Trial"]
    dropped = sum(r["counts"].get("dropped_verify", 0) for r in runs)
    screened = sum(r["counts"].get("candidates", 0) for r in runs)
    pdrop = sum(r["counts"].get("dropped_privacy", 0) for r in runs)
    proof = [(len(research_all), "research reports filed, each with its sources", "arena/"),
             (len(shipped_ok), "shipped changes with acceptance checked by Trial", "cases/"),
             (f"{dropped} of {screened}", "candidate entries Verify dropped before publishing", "behind/"),
             (len(ups), "Grok Bot updates tracked from public sources", "updates/")]
    asof = last_run["date"] if last_run else ""
    q = [("What can this team do?", "Run a real product end to end. Every day it finds and verifies public Grok Bot updates, and it designs, builds, reviews, and ships its own site through pull requests.",
          [("updates/", "See the tracker"), ("cases/", "Read the case files")]),
         ("Why is the approach different?", "Every claim links a source, every change is reviewed by a different role, and the guardrails live in CI, where nobody, bots included, can quietly switch them off. Mistakes are shown, not hidden.",
          [("cases/#case-filters", "When a design hit our own guardrail"), ("behind/", "Behind the scenes")]),
         ("What is working with it like?", "A question goes in. Roles research it independently, a critic challenges the strongest ideas, and a scored decision comes back with the evidence attached.",
          [("arena/", "Watch a real round in the Research Arena")])]
    catches = [(f"Verify dropped {dropped} of {screened} candidate entries that weren't product changes or couldn't be sourced.", "behind/"),
               (f"Shield dropped {pdrop} entry that centered on a person's email address, and rewrote others so no regular user is named." if pdrop == 1 else f"Shield dropped {pdrop} entries for personal data.", "behind/"),
               ("A new contrast test caught a hard-to-read dark-mode badge on its first run.", "cases/#case-contrast"),
               ("The first filter design used form inputs, which CI bans. It was rebuilt instead of loosening the check.", "cases/#case-filters")]
    can = ["Research public sources and cite every one", "Design, build, and ship static sites through reviewed pull requests", "Run a daily routine on a fixed, published budget", "Score decisions and keep the record public"]
    cant = ["Take input from visitors (this site has no forms or scripts)", "Read private accounts or data", "Claim a result it can't link", "Ship without CI and a second role's sign-off"]
    team_strip = "".join(f'<li><a href="team/" title="{e(n)}">{avatar(n, "", 44)}<span>{e(n)}</span></a></li>' for _, members in GROUPS for n in members)
    landing = (f'<section class="proof" aria-labelledby="proof-t"><h2 id="proof-t">Proof, not promises</h2><p class="meta">{label("verified")} counted from the repo when this page was built{(" · " + as_of(asof, "last daily run")) if asof else ""}</p><ul class="stats">'
               + "".join(f'<li><a href="{u}"><strong>{e(v)}</strong> <span>{e(l)}</span></a></li>' for v, l, u in proof) + "</ul></section>"
               + '<section class="questions" aria-label="Three questions"><div class="qgrid">' + "".join(f'<article class="card q"><h2>{e(t)}</h2><p>{e(d)}</p><p class="links">' + " · ".join(f'<a href="{u}">{e(x)}</a>' for u, x in ls) + "</p></article>" for t, d, ls in q) + "</div></section>"
               + '<section aria-labelledby="catch-t"><h2 id="catch-t">How the team catches its own mistakes</h2><ul class="catches">' + "".join(f'<li>{label("verified")} {e(t)} <a href="{u}">record</a></li>' for t, u in catches)
               + f'<li class="meta">The history is young: runs began on {e(runs[-1]["date"]) if runs else "n/a"}, and no merged change has needed a revert yet.</li></ul></section>'
               + '<section class="cancant" aria-label="What the team can and can\'t do"><div class="card"><h2>Can</h2><ul>' + "".join(f"<li>{e(x)}</li>" for x in can) + '</ul></div><div class="card"><h2>Won\'t</h2><ul>' + "".join(f"<li>{e(x)}</li>" for x in cant) + "</ul></div></section>"
               + f'<section aria-labelledby="team-t"><h2 id="team-t">The team</h2><p>{len(team())} roles in five groups, played by one daily routine and labeled honestly as roles. <a href="team/">Meet them</a>.</p><ul class="strip">{team_strip}</ul></section>'
               + '<section aria-labelledby="latest-t"><h2 id="latest-t">Latest from the tracker</h2>' + "".join(entry_card(x) for x in ups[:3]) + '<p><a href="updates/">All updates</a> · <a href="issues/">Known issues</a></p></section>'
               + legend())
    files["index.html"] = page("", "A team of Grok Bots that researches, builds, reviews, and ships, in public",
                               "Slopworks is a showcase of their work. The team runs a real product, an unofficial Grok Bot tracker, and publishes every decision behind it. Everything here links to the record.", landing, "data")
    areas = sorted({x["area"] for x in iss})
    body = ""
    for a in areas:
        body += f'<section data-area="{e(a)}"><h2>{e(a.capitalize())}</h2>' + "".join(entry_card(x, True) for x in iss if x["area"] == a) + "</section>"
    if body:
        fl, st = area_filter(iss)
        body = st + '<div class="filtered">' + fl + body + "</div>"
    files["issues/index.html"] = page("issues/", "Known issues", f"{sum(x['state']=='open' for x in iss)} open, {sum(x['state']=='fixed' for x in iss)} fixed. Grouped by area. Marked fixed only when a public source says so.", body or '<p class="empty">No known issues right now. Issues land here when a public source reports one; the daily run checks around 9:15 AM ET.</p>', "data/issues.json")

    body = ""
    for r in runs:
        counts = "".join(f"<tr><th scope=\"row\">{e(k.replace('_', ' '))}</th><td>{v}</td></tr>" for k, v in r["counts"].items())
        notes = "".join(f"<li>{e(n)}</li>" for n in r.get("notes", []))
        body += (f'<article class="card"><h3>{e(r["date"])} · {e(r["kind"])} run · {e(r["status"])}</h3>'
                 f'<table><tbody>{counts}<tr><th scope="row">X reads</th><td>{r.get("x_reads", 0)}</td></tr></tbody></table><ul>{notes}</ul></article>')
    files["behind/index.html"] = page("behind/", "Behind the scenes", f"What each role found, dropped, or stripped in every run. Auto-merge is <strong>{e(state['auto_merge'])}</strong>. These are roles played in one daily routine, not separate live bots.", body, "data/runs.json")

    wins = load("wins")
    alumni = load("alumni")
    alumni_html = ("<h2 class=\"group\">Alumni</h2><ul>" + "".join(f'<li><a href="{REPO}/blob/main/bots/alumni/{e(a["role"].lower())}.md">{e(a["role"])}</a>: retired {a["date"]}. {e(a["reason"])} Work handed to {e(a["successor"])}.</li>' for a in alumni) + "</ul>") if alumni else ""
    research = sorted(load("research"), key=lambda r: r["date"], reverse=True)
    rot = {r["role"]: (d["day"], r["focus"]) for d in sched.get("research", []) for r in d["roles"]}
    TEAM_ROLE = {"Sketch": "Scout", "Lens": "Verify"}
    def researched(n):
        r = TEAM_ROLE.get(n, n)
        day, focus = rot.get(r, ("", ""))
        last = next((x for x in research if x["role"] == r), None)
        lt = f' Last: <a href="../chat/#{e(last["id"])}">{e(last["question"])}</a> ({last["date"]}).' if last else " No notes yet. The weekly rotation adds one."
        return f'<p><strong>Researches</strong> ({e(day)}s): {e(focus)}.{lt}</p>' if day else ""
    def tcard(n, t, r, o, f):
        w = [x for x in wins if x["role"] == n][:3]
        wl = "".join(f'<li><a href="{e(x["pr"])}">{e(x["title"])}</a> <time datetime="{x["date"]}">{x["date"]}</time></li>' for x in w) or '<li class="empty">No merged PRs yet. Shipped work shows up here after CI passes and the PR is squash-merged.</li>'
        return (f'<article class="card lead" style="border-top:4px solid {color(n)}">{avatar(n, "../", 72)}<h2><a href="{REPO}/blob/main/bots/{f}">{e(n)}</a></h2>'
                f'<p class="title">{e(t)}</p><p>{e(bio(n))}</p><p><strong>Owns:</strong> {e(o)}</p>{researched(n)}<h3>Recent wins</h3><ul>{wl}</ul></article>')
    files["team/index.html"] = page("team/", "The team", e(CREDIT) + " Each card comes from the bot's own instruction file, and the bios are written by the bots in their own words. One daily routine plays every role in turn, so these are roles, not separate accounts. Recent wins are the merged PRs each role made. Pixel and Core work under Forge.",
                                    "".join(f'<h2 class="group">{e(g)}</h2><div class="grid">' + "".join(tcard(*x) for x in team() if x[0] in members) + "</div>" for g, members in GROUPS) + alumni_html, "bots")

    idea_state = {i["id"]: i["state"] for i in load("ideas")}
    def msg(c, cls="msg"):
        ref = f' <a href="{e(c["ref"])}">ref</a>' if c.get("ref") else ""
        when = f'{c["date"]} {c["time"]} ET' if c.get("time") else c["date"]
        badge = ""
        if c.get("idea") in idea_state:
            st = idea_state[c["idea"]]
            badge = f' <a class="badge b-{BADGE.get(st, st)}" href="#{e(c["idea"])}">pitch: {e(BADGE.get(st, st))}</a>'
        return (f'<li class="{cls}" id="{e(c["id"])}">{avatar(c["from"], "../")}<div><p class="hd"><strong class="who" style="--c:{color(c["from"])}">{e(c["from"])}</strong>'
                f' <span class="meta">to {e(c["to"])} · <time datetime="{c["date"]}">{e(when)}</time>{ref}</span>{badge}</p><p>{e(c["text"])}</p>')
    replies = {}
    for c in chat:
        if c.get("reply_to"):
            replies.setdefault(c["reply_to"], []).append(c)
    def root(c):
        rs = replies.get(c["id"], [])
        th = (f'<details><summary>{len(rs)} {"reply" if len(rs) == 1 else "replies"}</summary><ul class="thread">' + "".join(msg(r, "msg reply") + "</div></li>" for r in rs) + "</ul></details>") if rs else ""
        return msg(c) + th + "</div></li>"
    items = "".join(root(c) for c in reversed(chat) if not c.get("reply_to"))
    standup = load("standup")
    last_day = max((x["date"] for x in standup), default=None)
    today = [x for x in standup if x["date"] == last_day]
    sbody = (f'<h2 id="standup">Standup · <time datetime="{last_day}">{last_day}</time></h2><ul class="chat">' + "".join(
        f'<li class="msg">{avatar(x["role"], "../")}<div><strong class="who" style="--c:{color(x["role"])}">{e(x["role"])}</strong><br>Did: {e(x["did"])}<br>Doing: {e(x["doing"])}<br>Blockers: {e(x["blockers"])}</div></li>' for x in today) + "</ul>"
        if today else "<h2 id=standup>Standup</h2><p class=empty>No standup yet today. The daily run (around 9:15 AM ET) opens with one line per role that has something new.</p>")
    ideas = sorted(load("ideas"), key=lambda i: i["date"], reverse=True)
    def idea(i):
        cm = "".join(f'<li>{e(c["role"])} ({e(c["stance"])}{", strong" if c.get("strong") else ""}): {e(c["text"])}</li>' for c in i["comments"])
        dec = f'<p><strong>{e(i["state"])}</strong> by {e(i["decided_by"])} on {e(i["decided"])}: {e(i["reason"])}</p>' if i.get("decided") else ""
        return (f'<article class="card" id="{e(i["id"])}"><h3>{e(i["problem"])}</h3><p>Helps: {e(i["helps"])} · effort {e(i["effort"])} · builds: {e(i["builder"])}</p>{dec}'
                f'{"<ul>" + cm + "</ul>" if cm else ""}<p class="meta"><span class="tag">{e(i["state"])}</span><span>pitched {e(i["date"])} by {e(i["by"])}</span></p></article>')
    ibody = "<h2 id=\"ideas\">Ideas</h2><p>Pitches from the standup. Coordinator decides at Monday planning, Shield can veto on risk, and strong disagreement goes to the CEO. Rejected and later ideas stay here and can be re-pitched with new evidence.</p>" + ("".join(map(idea, ideas)) or '<p class="empty">No pitches yet. Ideas come from the standup and get decided at Monday planning.</p>')
    research = sorted(load("research"), key=lambda r: r["date"], reverse=True)
    latest = {}
    for r in research:
        latest.setdefault(r["role"], r)
    def rnote(r):
        tk = f'<p>{e(r["finding"])}</p>' + (f"<p>{label('verified')} <strong>Facts</strong></p><ul>" + "".join(f"<li>{e(t)}</li>" for t in r.get("facts", [])) + "</ul>" if r.get("facts") else "") \
            + (f"<p>{label('hypothesis')} <strong>Inferences</strong></p><ul>" + "".join(f"<li>{e(t)}</li>" for t in r.get("inferences", [])) + "</ul>" if r.get("inferences") else "")
        tk = f'<p class="meta"><span class="tag">{e(r["outcome"])}</span><span class="tag">{e(r["status"])}</span><span>confidence {e(r["confidence"])}</span>' + (f'<span>recommend {e(r["recommendation"])}</span>' if r.get("recommendation") else "") + "</p>" + tk
        src = " · ".join(f'<a href="{e(u)}">source {k + 1}</a>' for k, u in enumerate(r["evidence"]))
        idea = (f'<p>{label("recommendation")} <strong>Opportunity:</strong> {e(r["opportunity"])}' if r.get("opportunity") else "<p>") + (f' (<a href="#{e(r["pitch"])}">pitched</a>)' if r.get("pitch") else "") + "</p>"
        return (f'<article class="card" id="{e(r["id"])}"><p class="hd">{avatar(r["role"], "../", 32)} <strong class="who" style="--c:{color(r["role"])}">{e(r["role"])}</strong>'
                f' <span class="meta"><time datetime="{r["date"]}">{r["date"]}</time></span></p><h3>{e(r["question"])}</h3>{tk}{idea}<p class="meta">{src}</p></article>')
    rbody = ("<h2 id=\"research\">Research</h2><p>Each role researches its own area once a week (see the <a href=\"../schedule/\">rotation</a>), reading public web pages only, and writes the takeaways in its own words. Ideas go through the pitch flow.</p>" + legend()
             + ("".join(rnote(r) for r in sorted(latest.values(), key=lambda r: r["date"], reverse=True)) or '<p class="empty">No research notes yet. Each role adds one through the weekly rotation; urgent questions can add more.</p>'))
    fl = '<p>Follow Team chat: <a href="../chat.xml">RSS</a>, <a href="../chat.json">JSON</a>. </p><details class="routine"><summary>Follow it with your own Grok Bot</summary><p>Paste this into a routine:</p><blockquote class="card"><p>Every morning, read https://slopryno.github.io/slopworks/chat.json and tell me about new pitches, decisions, and any debate between the Slopworks bots since yesterday: who pitched what, who pushed back, and what Coordinator decided and why. Stay quiet if nothing\'s new.</p></blockquote></details>'
    fl = '<nav class="jump" aria-label="On this page"><a href="#standup">Standup</a><a href="#ideas">Ideas</a><a href="#research">Research</a><a href="#handoffs">Handoffs</a></nav>' + fl
    files["chat/index.html"] = page("chat/", "Team chat", "The real handoffs between roles during each run, newest first. Nothing is staged; quiet days stay quiet. It never quotes readers or names anyone outside the team.", fl + sbody + ibody + rbody + f'<h2 id="handoffs">Handoffs</h2><ul class="chat">{items}</ul>', "data/chat.json")
    citems = ([("standup", x["id"], x["date"], f'Standup: {x["role"]}', f'Did: {x["did"]} Doing: {x["doing"]} Blockers: {x["blockers"]}', "chat/") for x in standup]
              + [("idea", i["id"], i.get("decided") or i["date"], f'Idea ({i["state"]}): {i["problem"]}', f'Pitched by {i["by"]}. ' + (i.get("reason") or ""), f'chat/#{i["id"]}') for i in ideas]
              + [("research", r["id"], r["date"], f'Research ({r["role"]}): {r["question"]}', r["finding"] + (" Recommend: " + r["recommendation"] if r.get("recommendation") else ""), f'chat/#{r["id"]}') for r in research]
              + [("chat", c["id"], c["date"], f'{c["from"]} to {c["to"]}', c["text"], "chat/") for c in chat])
    citems = sorted(citems, key=lambda t: (t[2], t[1]), reverse=True)[:50]
    cdt = lambda d: datetime.fromisoformat(d).replace(hour=12, tzinfo=timezone.utc)
    files["chat.json"] = json.dumps({"version": "https://jsonfeed.org/version/1.1", "title": "Slopworks Team chat: standups, pitches, and handoffs",
        "home_page_url": BASE + "chat/", "feed_url": BASE + "chat.json", "description": DISCLAIMER,
        "items": [{"id": f"{k}-{i}", "url": BASE + u, "title": t, "content_text": b, "date_published": cdt(d).isoformat(), "tags": [k]} for k, i, d, t, b, u in citems]}, indent=2, ensure_ascii=False) + "\n"
    crss = "".join(f'<item><title>{e(t)}</title><link>{e(BASE + u)}</link><guid isPermaLink="false">{k}-{e(i)}</guid><pubDate>{format_datetime(cdt(d))}</pubDate><description>{e(b)}</description><category>{k}</category></item>\n' for k, i, d, t, b, u in citems)
    files["chat.xml"] = f'<?xml version="1.0" encoding="utf-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>Slopworks Team chat</title><link>{BASE}chat/</link><atom:link href="{BASE}chat.xml" rel="self" type="application/rss+xml"/><description>{e(DISCLAIMER)}</description>\n{crss}</channel></rss>\n'

    # Research Arena (i22, PR 2 of 8): one question, independent reports, challenge, scores, decision. Real records only.
    rmap = {r["id"]: r for r in load("research")}
    imap = {i["id"]: i for i in load("ideas")}
    def prio(s):
        return round(s["impact"] * s["evidence"] * s["fit"] / (s["effort"] * s["risk"]), 1)
    def report(r):
        facts = "".join(f"<li>{e(t)}</li>" for t in r.get("facts", []))
        infs = "".join(f"<li>{e(t)}</li>" for t in r.get("inferences", []))
        src = " · ".join(f'<a href="{e(u)}">source {k + 1}</a>' for k, u in enumerate(r["evidence"]))
        rec = (f'<p>{label("recommendation")} {e(r["opportunity"])}' + (f' <span class="meta">(recommend {e(r["recommendation"])})</span>' if r.get("recommendation") else "") + "</p>") if r.get("opportunity") else ""
        unc = f'<p><strong>Uncertainty:</strong> {e(r["risks"])}</p>' if r.get("risks") else ""
        exp = f'<p><strong>Cheap experiment:</strong> {e(r["experiment"])}</p>' if r.get("experiment") else ""
        return (f'<details class="report" name="arena" id="{e(r["id"])}"><summary>{avatar(r["role"], "../", 28)} <strong class="who" style="--c:{color(r["role"])}">{e(r["role"])}</strong> <span>{e(r["question"])}</span></summary>'
                f'<div class="report-body"><p class="finding">{e(r["finding"])}</p>'
                + (f"<p>{label('verified')} <strong>Facts</strong></p><ul>{facts}</ul>" if facts else "")
                + (f"<p>{label('hypothesis')} <strong>Inferences</strong></p><ul>{infs}</ul>" if infs else "")
                + rec + unc + exp + f'<p class="meta"><span>confidence {e(r["confidence"])}</span><span>status {e(r["status"])}</span>{src}</p></div></details>')
    abody = ""
    for a in load("arena"):
        reps = [rmap[x] for x in a["reports"] if x in rmap]
        reads = len({u for r in reps for u in r["evidence"]})
        dec = imap.get(a["decision"], {})
        rows = "".join(f'<tr><th scope="row">{e(c["name"])}</th>' + ("".join(f"<td>{c['scores'][k]}</td>" for k in ("impact", "evidence", "fit", "effort", "risk")) + f'<td><strong>{prio(c["scores"])}</strong></td>' if c["scores"] else '<td colspan="6">not scored</td>')
                       + f'<td>{e(c["outcome"])}<br><span class="meta">{e(c["note"])}</span></td></tr>' for c in a["concepts"])
        steps = [("Question", f'Ryno (CEO) asked: {e(a["question"])} <a href="../chat/#{e(a["thread"])}">CEO thread</a>'),
                 ("Independent research", f"{len(reps)} reports from {len({r['role'] for r in reps})} roles, written before reading each other's. {reads} distinct public web pages read, no X reads."),
                 ("Consolidate", 'Librarian merged duplicates into five concepts and checked them against prior work. <a href="#r-librarian-2026-10-17-showcase">Librarian\'s note</a>'),
                 ("Challenge", 'Critic challenged the strongest proposals and named what to cut. <a href="#r-critic-2026-10-17-showcase">Critic\'s report</a>'),
                 ("Score", "Coordinator scored each concept: Priority = (Impact × Evidence × Fit) / (Effort × Risk), each 1-5."),
                 ("Decide", f'Decision <a href="../chat/#{e(a["decision"])}">{e(a["decision"])}</a>: {e(dec.get("state", ""))} by {e(dec.get("decided_by", ""))}. Merged in <a href="{REPO}/pull/{a["pr"]}">PR #{a["pr"]}</a>.')]
        abody += (f'<section class="round" aria-labelledby="{e(a["id"])}-t"><h2 id="{e(a["id"])}-t">{e(a["title"])}</h2><p class="meta">{as_of(a["date"], "round held")}<span>{len(reps)} reports</span><span>all records real, nothing staged</span></p>'
                  + '<ol class="steps">' + "".join(f"<li><strong>{e(t)}.</strong> {d}</li>" for t, d in steps) + "</ol>"
                  + '<h3>The scoreboard</h3><div class="scroll"><table class="score"><thead><tr><th scope="col">Concept</th><th scope="col">Impact</th><th scope="col">Evidence</th><th scope="col">Fit</th><th scope="col">Effort</th><th scope="col">Risk</th><th scope="col">Priority</th><th scope="col">Outcome</th></tr></thead><tbody>' + rows + "</tbody></table></div>"
                  + f"<h3>What Critic cut</h3><ul>" + "".join(f"<li>{e(c)}</li>" for c in a["cuts"]) + "</ul>"
                  + "<h3>Every report</h3><p>Open one at a time. Each separates checked facts from reasoned judgment and ends with one recommendation, one uncertainty, and one cheap experiment.</p>" + legend()
                  + "".join(report(r) for r in reps) + "</section>")
    files["arena/index.html"] = page("arena/", "Research Arena", "Watch the team research a real question: independent reports, a challenge, a score, and a decision. Every claim links its source or the record behind it.",
                                     abody or '<p class="empty">No research rounds yet. A round appears here when the team researches a question together.</p>', "data/arena.json")

    # Case files (i22, PR 3 of 8): real decisions replayed step by step. Links go to merged PRs, chat, and research only.
    def case_card(c):
        st = "".join(f'<li>{avatar(x["role"], "../", 28)}<div><p>{label(x["label"])} <strong class="who" style="--c:{color(x["role"])}">{e(x["role"])}</strong></p><p>{e(x["text"])} <a href="{e(x["link"])}">{"PR #" + x["link"].rsplit("/", 1)[1] if "/pull/" in x["link"] else "record"}</a></p></div></li>' for x in c["steps"])
        return (f'<article class="card case" id="{e(c["id"])}"><h2>{e(c["title"])}</h2><p class="meta">{as_of(c["date"], "shipped")}<span>real work, not a demo</span></p>'
                f'<p>{e(c["summary"])}</p><p><strong>What it shows:</strong> {e(c["shows"])}</p><ol class="trace">{st}</ol><p><strong>Outcome:</strong> {e(c["outcome"])} <a href="{REPO}/pull/{c["pr"]}">PR #{c["pr"]}</a></p></article>')
    cases = load("cases")
    files["cases/index.html"] = page("cases/", "Case files", "Real decisions from this team, replayed step by step: the problem, the call, the build, the review, and what shipped. Every step links the merged PR or the Team chat message behind it.",
                                     legend() + ("".join(map(case_card, cases)) or '<p class="empty">No case files yet. A case file is added after a decision ships.</p>') + '<p>Want to see how a decision gets made before anything ships? Visit the <a href="../arena/">Research Arena</a>.</p>', "data/cases.json")

    shipped = [d for d in design if d["state"] == "shipped"]
    backlog = sorted([d for d in design if d["state"] in ("backlog", "in-progress")], key=lambda d: d["rank"])
    card = lambda d: f'<article class="card"><h3>{e(d["idea"])}</h3><p>{e(d["why"])}</p><p class="meta"><span class="tag">effort {d["effort"]}</span><span>{e(d["state"])}{" " + d["shipped"] if d.get("shipped") else ""}</span></p></article>'
    files["design/index.html"] = page("design/", "Design log", "What Polish, the design bot, changed and what's next. One small design change a week at most, each reviewed by Lens and Trial.",
                                      "<h2>Shipped</h2>" + "".join(map(card, shipped)) + "<h2>Up next (ranked)</h2>" + "".join(map(card, backlog)), "data/design_backlog.json")

    srows = "".join(f'<tr><th scope="row">{e(i["when"])}</th><td>{e(i["what"])}</td></tr>' for i in sched["items"])
    rot_html = "<h2>Research rotation</h2><p>Each role researches its own area once a week, using public web pages only (about 5 pages max, no X reads).</p><table><tbody>" + "".join(
        f'<tr><th scope="row">{e(d["day"])}</th><td>' + "<br>".join(f'<strong>{e(r["role"])}</strong>: {e(r["focus"])}' for r in d["roles"]) + "</td></tr>" for d in sched.get("research", [])) + "</tbody></table>"
    lim = "".join(f"<li>{e(l)}</li>" for l in sched["limits"])
    last = runs[0] if runs else None
    status = f'Last run: <strong>{e(last["date"])}</strong> ({e(last["kind"])}), status <strong>{e(last["status"])}</strong>. Next: the daily run, around 9:15 AM ET.' if last else '<span class="empty">No runs yet. The first daily run is around 9:15 AM ET.</span>'
    files["schedule/index.html"] = page("schedule/", "Schedule and limits", "What to expect and when. Generated from the same schedule file the routines use.",
                                        f'<p class="card">{status}</p><table><tbody>{srows}</tbody></table>' + rot_html + f'<h2>Limits, in plain words</h2><ul>{lim}</ul>', "data/schedule.json")

    feed = sorted([("update", x) for x in ups] + [("issue", x) for x in iss], key=lambda p: (p[1]["date"], p[1]["id"]), reverse=True)[:50]
    link = lambda k, x: f'{BASE}{"issues/" if k == "issue" else "updates/"}#e{x["id"]}'
    title = lambda k, x: (f"Issue ({x['state']}): " if k == "issue" else "") + x["title"]
    dt = lambda d: datetime.fromisoformat(d).replace(hour=12, tzinfo=timezone.utc)
    files["feed.json"] = json.dumps({"version": "https://jsonfeed.org/version/1.1", "title": "Slopworks: Grok Bot updates and known issues",
        "home_page_url": BASE, "feed_url": BASE + "feed.json", "description": DISCLAIMER,
        "items": [{"id": f"{k}-{x['id']}", "url": link(k, x), "external_url": x["source"], "title": title(k, x), "content_text": x["summary"],
                   "date_published": dt(x["date"]).isoformat(), "tags": [k, x["area"], x["status"]] + ([x["state"]] if k == "issue" else [])} for k, x in feed]}, indent=2, ensure_ascii=False) + "\n"
    rss = "".join(f"<item><title>{e(title(k, x))}</title><link>{e(link(k, x))}</link><guid isPermaLink=\"false\">{k}-{x['id']}</guid><pubDate>{format_datetime(dt(x['date']))}</pubDate><description>{e(x['summary'] + ' Source: ' + x['source'])}</description><category>{e(x['status'])}</category></item>\n" for k, x in feed)
    files["feed.xml"] = f'<?xml version="1.0" encoding="utf-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>Slopworks: Grok Bot updates and known issues</title><link>{BASE}</link><atom:link href="{BASE}feed.xml" rel="self" type="application/rss+xml"/><description>{e(DISCLAIMER)}</description>\n{rss}</channel></rss>\n'
    files["badges/updates.svg"] = badge("updates", len(ups), "#0550ae")
    files["badges/issues.svg"] = badge("open issues", n_open, "#7d4e00" if n_open else "#116329")
    files["badges/last-run.svg"] = badge("last run", f'{last_run["date"]} {last_run["status"]}' if last_run else "none", "#116329" if last_run and last_run["status"] == "ok" else "#7d4e00")
    files["badges/roles.svg"] = badge("bot roles", len(team()), "#8250df")
    return files


def main():
    files = build()
    stale = []
    for rel, content in files.items():
        p = SITE / rel
        if "--check" in sys.argv:
            if not p.exists() or p.read_text() != content:
                stale.append(rel)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
    if stale:
        print("Site is out of date; run python3 scripts/build.py:", *stale)
        sys.exit(1)
    print(f"{'checked' if '--check' in sys.argv else 'built'} {len(files)} files")


if __name__ == "__main__":
    main()
