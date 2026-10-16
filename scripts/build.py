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
NAV = [("", "What's new"), ("issues/", "Known issues"), ("behind/", "Behind the scenes"), ("team/", "Team"),
       ("chat/", "Team chat"), ("design/", "Design log"), ("schedule/", "Schedule and limits")]
e = lambda s: html.escape(str(s), quote=True)


def load(name):
    return json.loads((ROOT / f"data/{name}.json").read_text())


def page(slug, title, lede, body, source):
    up = "../" * slug.count("/")
    nav = "".join(f'<li><a href="{up}{s}"{" aria-current=\"page\"" if s == slug else ""}>{e(t)}</a></li>' for s, t in NAV)
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
<nav aria-label="Sections"><ul>{nav}</ul></nav>
</div></header>
<main id="main" class="wrap">
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
    return (f'<article class="card" id="e{e(x["id"])}"><h3>{e(x["title"])}</h3><p>{e(x["summary"])}</p>{extra}'
            f'<p class="meta"><span>{tags}</span><time datetime="{x["date"]}">{x["date"]}</time>'
            f'<a href="{e(x["source"])}">source</a><span>added {x["added"]} by {e(x["added_by"])}</span></p></article>')


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

    files["index.html"] = page("", "What's new in Grok Bot", f"{len(ups)} updates from public posts, newest first. Every item links its source and says whether it's <strong>confirmed</strong> (official account or docs) or <strong>reported</strong> (community post).",
                               "".join(entry_card(x) for x in ups) or "<p>Nothing yet.</p>", "data/updates.json")
    areas = sorted({x["area"] for x in iss})
    body = ""
    for a in areas:
        body += f"<h2>{e(a.capitalize())}</h2>" + "".join(entry_card(x, True) for x in iss if x["area"] == a)
    files["issues/index.html"] = page("issues/", "Known issues", f"{sum(x['state']=='open' for x in iss)} open, {sum(x['state']=='fixed' for x in iss)} fixed. Grouped by area. Marked fixed only when a public source says so.", body or "<p>No known issues.</p>", "data/issues.json")

    body = ""
    for r in runs:
        counts = "".join(f"<tr><th scope=\"row\">{e(k.replace('_', ' '))}</th><td>{v}</td></tr>" for k, v in r["counts"].items())
        notes = "".join(f"<li>{e(n)}</li>" for n in r.get("notes", []))
        body += (f'<article class="card"><h3>{e(r["date"])} · {e(r["kind"])} run · {e(r["status"])}</h3>'
                 f'<table><tbody>{counts}<tr><th scope="row">X reads</th><td>{r.get("x_reads", 0)}</td></tr></tbody></table><ul>{notes}</ul></article>')
    files["behind/index.html"] = page("behind/", "Behind the scenes", f"What each role found, dropped, or stripped in every run. Auto-merge is <strong>{e(state['auto_merge'])}</strong>. These are roles played in one daily routine, not separate live bots.", body, "data/runs.json")

    rows = "".join(f'<tr><td><a href="{REPO}/blob/main/bots/{f}">{e(n)}</a></td><td>{e(t)}</td><td>{e(r)}</td><td>{e(o)}</td></tr>' for n, t, r, o, f in team())
    files["team/index.html"] = page("team/", "The team", e(CREDIT) + " Each card is generated from the bot's instruction file. In v1 one daily routine plays every role in turn, so these are roles, not separate accounts.",
                                    f"<table><thead><tr><th scope=\"col\">Bot</th><th scope=\"col\">Title</th><th scope=\"col\">Role</th><th scope=\"col\">Owns</th></tr></thead><tbody>{rows}</tbody></table>", "bots")

    def msg(c):
        ref = f' <a href="{e(c["ref"])}">ref</a>' if c.get("ref") else ""
        return (f'<li><span class="who">{e(c["from"])} → {e(c["to"])}</span> <span class="meta"><time datetime="{c["date"]}">{c["date"]}</time>{ref}</span>'
                f'<br>{e(c["text"])}</li>')
    items = "".join(msg(c) for c in reversed(chat))
    standup = load("standup")
    last_day = max((x["date"] for x in standup), default=None)
    today = [x for x in standup if x["date"] == last_day]
    sbody = (f'<h2>Standup · <time datetime="{last_day}">{last_day}</time></h2><ul class="chat">' + "".join(
        f'<li><span class="who">{e(x["role"])}</span><br>Did: {e(x["did"])}<br>Doing: {e(x["doing"])}<br>Blockers: {e(x["blockers"])}</li>' for x in today) + "</ul>"
        if today else "<h2>Standup</h2><p>No standup yet. Each run starts with one line per role that has something new.</p>")
    ideas = sorted(load("ideas"), key=lambda i: i["date"], reverse=True)
    def idea(i):
        cm = "".join(f'<li>{e(c["role"])} ({e(c["stance"])}{", strong" if c.get("strong") else ""}): {e(c["text"])}</li>' for c in i["comments"])
        dec = f'<p><strong>{e(i["state"])}</strong> by {e(i["decided_by"])} on {e(i["decided"])}: {e(i["reason"])}</p>' if i.get("decided") else ""
        return (f'<article class="card" id="{e(i["id"])}"><h3>{e(i["problem"])}</h3><p>Helps: {e(i["helps"])} · effort {e(i["effort"])} · builds: {e(i["builder"])}</p>{dec}'
                f'{"<ul>" + cm + "</ul>" if cm else ""}<p class="meta"><span class="tag">{e(i["state"])}</span><span>pitched {e(i["date"])} by {e(i["by"])}</span></p></article>')
    ibody = "<h2>Ideas</h2><p>Pitches from the standup. Coordinator decides at Monday planning, Shield can veto on risk, and strong disagreement goes to the CEO. Rejected and later ideas stay here and can be re-pitched with new evidence.</p>" + ("".join(map(idea, ideas)) or "<p>No pitches yet.</p>")
    fl = '<p>Follow Team chat: <a href="../chat.xml">RSS</a>, <a href="../chat.json">JSON</a>. To follow it with your own Grok Bot, paste this into a routine:</p><blockquote class="card"><p>Every morning, read https://slopryno.github.io/slopworks/chat.json and tell me about new pitches, decisions, and any debate between the Slopworks bots since yesterday: who pitched what, who pushed back, and what Coordinator decided and why. Stay quiet if nothing\'s new.</p></blockquote>'
    files["chat/index.html"] = page("chat/", "Team chat", "The real handoffs between roles during each run, newest first. Nothing is staged; quiet days stay quiet. It never quotes readers or names anyone outside the team.", fl + sbody + ibody + f'<h2>Handoffs</h2><ul class="chat">{items}</ul>', "data/chat.json")
    citems = ([("standup", x["id"], x["date"], f'Standup: {x["role"]}', f'Did: {x["did"]} Doing: {x["doing"]} Blockers: {x["blockers"]}', "chat/") for x in standup]
              + [("idea", i["id"], i.get("decided") or i["date"], f'Idea ({i["state"]}): {i["problem"]}', f'Pitched by {i["by"]}. ' + (i.get("reason") or ""), f'chat/#{i["id"]}') for i in ideas]
              + [("chat", c["id"], c["date"], f'{c["from"]} to {c["to"]}', c["text"], "chat/") for c in chat])
    citems = sorted(citems, key=lambda t: (t[2], t[1]), reverse=True)[:50]
    cdt = lambda d: datetime.fromisoformat(d).replace(hour=12, tzinfo=timezone.utc)
    files["chat.json"] = json.dumps({"version": "https://jsonfeed.org/version/1.1", "title": "Slopworks Team chat: standups, pitches, and handoffs",
        "home_page_url": BASE + "chat/", "feed_url": BASE + "chat.json", "description": DISCLAIMER,
        "items": [{"id": f"{k}-{i}", "url": BASE + u, "title": t, "content_text": b, "date_published": cdt(d).isoformat(), "tags": [k]} for k, i, d, t, b, u in citems]}, indent=2, ensure_ascii=False) + "\n"
    crss = "".join(f'<item><title>{e(t)}</title><link>{e(BASE + u)}</link><guid isPermaLink="false">{k}-{e(i)}</guid><pubDate>{format_datetime(cdt(d))}</pubDate><description>{e(b)}</description><category>{k}</category></item>\n' for k, i, d, t, b, u in citems)
    files["chat.xml"] = f'<?xml version="1.0" encoding="utf-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>Slopworks Team chat</title><link>{BASE}chat/</link><atom:link href="{BASE}chat.xml" rel="self" type="application/rss+xml"/><description>{e(DISCLAIMER)}</description>\n{crss}</channel></rss>\n'

    shipped = [d for d in design if d["state"] == "shipped"]
    backlog = sorted([d for d in design if d["state"] in ("backlog", "in-progress")], key=lambda d: d["rank"])
    card = lambda d: f'<article class="card"><h3>{e(d["idea"])}</h3><p>{e(d["why"])}</p><p class="meta"><span class="tag">effort {d["effort"]}</span><span>{e(d["state"])}{" " + d["shipped"] if d.get("shipped") else ""}</span></p></article>'
    files["design/index.html"] = page("design/", "Design log", "What Polish, the design bot, changed and what's next. One small design change a week at most, each reviewed by Lens and Trial.",
                                      "<h2>Shipped</h2>" + "".join(map(card, shipped)) + "<h2>Up next (ranked)</h2>" + "".join(map(card, backlog)), "data/design_backlog.json")

    srows = "".join(f'<tr><th scope="row">{e(i["when"])}</th><td>{e(i["what"])}</td></tr>' for i in sched["items"])
    lim = "".join(f"<li>{e(l)}</li>" for l in sched["limits"])
    last = runs[0] if runs else None
    status = f'Last run: <strong>{e(last["date"])}</strong> ({e(last["kind"])}), status <strong>{e(last["status"])}</strong>. Next: the daily run, around 9:15 AM ET.' if last else "No runs yet."
    files["schedule/index.html"] = page("schedule/", "Schedule and limits", "What to expect and when. Generated from the same schedule file the routines use.",
                                        f'<p class="card">{status}</p><table><tbody>{srows}</tbody></table><h2>Limits, in plain words</h2><ul>{lim}</ul>', "data/schedule.json")

    feed = sorted([("update", x) for x in ups] + [("issue", x) for x in iss], key=lambda p: (p[1]["date"], p[1]["id"]), reverse=True)[:50]
    link = lambda k, x: f'{BASE}{"issues/" if k == "issue" else ""}#e{x["id"]}'
    title = lambda k, x: (f"Issue ({x['state']}): " if k == "issue" else "") + x["title"]
    dt = lambda d: datetime.fromisoformat(d).replace(hour=12, tzinfo=timezone.utc)
    files["feed.json"] = json.dumps({"version": "https://jsonfeed.org/version/1.1", "title": "Slopworks: Grok Bot updates and known issues",
        "home_page_url": BASE, "feed_url": BASE + "feed.json", "description": DISCLAIMER,
        "items": [{"id": f"{k}-{x['id']}", "url": link(k, x), "external_url": x["source"], "title": title(k, x), "content_text": x["summary"],
                   "date_published": dt(x["date"]).isoformat(), "tags": [k, x["area"], x["status"]] + ([x["state"]] if k == "issue" else [])} for k, x in feed]}, indent=2, ensure_ascii=False) + "\n"
    rss = "".join(f"<item><title>{e(title(k, x))}</title><link>{e(link(k, x))}</link><guid isPermaLink=\"false\">{k}-{x['id']}</guid><pubDate>{format_datetime(dt(x['date']))}</pubDate><description>{e(x['summary'] + ' Source: ' + x['source'])}</description><category>{e(x['status'])}</category></item>\n" for k, x in feed)
    files["feed.xml"] = f'<?xml version="1.0" encoding="utf-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>Slopworks: Grok Bot updates and known issues</title><link>{BASE}</link><atom:link href="{BASE}feed.xml" rel="self" type="application/rss+xml"/><description>{e(DISCLAIMER)}</description>\n{rss}</channel></rss>\n'
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
