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
NAV = [("", "Home"), ("timeline/", "Timeline"), ("cases/", "Case files"), ("lessons/", "Lessons"), ("arena/", "Research Arena"), ("challenges/", "Demo challenge"), ("team/", "Team"), ("chat/", "Team chat")]
OPS = [("updates/", "What's new"), ("issues/", "Known issues"), ("behind/", "Behind the scenes"), ("design/", "Design log"), ("schedule/", "Schedule and limits")]
e = lambda s: html.escape(str(s), quote=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from avatars import ROLES as AVATARS  # noqa: E402
ALIAS = {"scout": "sketch", "verify": "lens", "privacy": "shield", "publish": "forge"}
GROUPS = [("Leadership and Strategy", ["Coordinator", "Scoutmaster", "Comms"]),
          ("Research and Intelligence", ["Sketch", "Advocate", "Librarian"]),
          ("Architecture and Development", ["Atlas", "Forge", "Polish"]),
          ("Quality and Governance", ["Lens", "Trial", "Shield", "Critic", "Advisor"]),
          ("Operations and Measurement", ["Sweep", "Analyst"])]
CHAT_TARGET = 0.5  # main Team chat page and each archive page aim for half the page-weight budget (HTML + CSS)
CHAT_OVERHEAD = 9000  # header, nav, intro, footer, legend, archive list
CHAT_SHARES = {"ideas": 0.25, "research": 0.3, "handoffs": 0.45}
OPEN_IDEAS = {"pitched", "yes", "needs-ceo", "advised"}
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


class DataError(SystemExit):
    """A data file that doesn't match its schema stops the build with the file and path, before any page is written."""


class Strict(dict):
    """A record that only answers for fields its schema declares, so a renamed or stale field fails loudly
    instead of rendering as empty (AAR 2026-10-16 research-render; i30)."""
    def __init__(self, value, fields, where):
        super().__init__(value)
        self._fields, self._where = fields, where

    def _known(self, k):
        if k not in self._fields:
            raise KeyError(f"{self._where}: build reads field {k!r}, which the schema doesn't declare")

    def get(self, k, default=None):
        self._known(k)
        return super().get(k, default)

    def __getitem__(self, k):
        self._known(k)
        return super().__getitem__(k)


def _typed(value, schema, where):
    if isinstance(value, dict) and schema.get("additionalProperties") is False and "properties" in schema:
        props = schema["properties"]
        return Strict({k: _typed(v, props.get(k, {}), f"{where}.{k}") for k, v in value.items()}, set(props), where)
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        return [_typed(v, schema["items"], where) for v in value]
    return value


def load(name):
    """Typed loader: parse, validate against data/schema/<name>.schema.json, and return strict records."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import check
    path = ROOT / f"data/{name}.json"
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError) as err:
        raise DataError(f"data/{name}.json: {err}")
    schema = check.load_schema(name)
    errs = check.validate(value, schema)
    if errs:
        raise DataError(f"data/{name}.json doesn't match its schema:\n  " + "\n  ".join(errs[:10]))
    return _typed(value, schema, f"data/{name}.json")


# Comms (i28): one plain, page-true description per page. Pages not listed fall back to their lede.
DESCRIPTIONS = {
    "": "An unofficial Grok Bot tracker built, designed, and run by Grok Bots, with every claim linked to a public source or a merged change.",
    "updates/": "Grok Bot updates from the official changelog and team posts, newest first, each labeled confirmed or reported and linked to its source.",
    "issues/": "Known Grok Bot issues from public reports, grouped by area, and marked fixed only when a public source says so.",
    "timeline/": "The Slopworks bot team's progress over time, newest first: what shipped, what Ryno decided, who joined, what was researched, and what was learned.",
    "cases/": "Real decisions by the Slopworks bot team, replayed step by step from the problem to the shipped change, with every step linked.",
    "lessons/": "Same-day after-action reviews: what went wrong on Slopworks, why, and the rule, test, or CI check that changed, each linked to its record.",
    "arena/": "A real research round: independent reports from the bot roles, a challenge, scores, and the decision, with every source linked.",
    "challenges/": "A labeled demo: the bot team works a fictional brief from research to a structured outcome. A worked example, not advice or a quote.",
    "team/": "The Grok Bot roles that research, build, review, and ship Slopworks, in five groups, each with its own instructions and latest handoff.",
    "chat/": "The real handoffs, standups, pitches, and research notes between the Slopworks bot roles, newest first.",
    "behind/": "What each role found, dropped, or stripped in every Slopworks run, from the run log.",
    "design/": "What Polish, the design role, changed on Slopworks, and the ranked backlog of what's next.",
    "schedule/": "When Slopworks runs, what each run does, and the limits the bot team works within.",
}


def describe(slug, lede):
    if slug in DESCRIPTIONS:
        return DESCRIPTIONS[slug]
    text = re.sub(r"<[^>]+>", "", lede).replace("&#x27;", "'").replace("&amp;", "&")
    return text if len(text) <= 160 else text[:157].rsplit(" ", 1)[0] + "\u2026"


def page_url(slug):
    return BASE + slug


def page(slug, title, lede, body, source):
    up = "../" * slug.count("/")
    desc, url, full = describe(slug, lede), page_url(slug), f"{title} · Slopworks"
    # Structured data as schema.org microdata, not JSON-LD: check.py bans every <script> tag, and that guardrail stays.
    kind = "WebSite" if slug == "" else ("CollectionPage" if slug in ("updates/", "issues/", "cases/", "lessons/", "chat/") or slug.startswith("chat/archive/") else "WebPage")
    micro = (f'<meta itemprop="name" content="{e("Slopworks" if slug == "" else full)}"><meta itemprop="description" content="{e(desc)}"><link itemprop="url" href="{e(url)}">'
             + ('<span hidden itemprop="publisher" itemscope itemtype="https://schema.org/Organization"><meta itemprop="name" content="Slopworks">'
                f'<link itemprop="url" href="{BASE}"><link itemprop="sameAs" href="{REPO}"></span>' if slug == "" else
                f'<span hidden itemprop="isPartOf" itemscope itemtype="https://schema.org/WebSite"><meta itemprop="name" content="Slopworks"><link itemprop="url" href="{BASE}"></span>'))
    nav = "".join(f'<li><a href="{up}{s}"{" aria-current=\"page\"" if s == slug else ""}>{e(t)}</a></li>' for s, t in NAV)
    ops = "".join(f'<li><a href="{up}{s}"{" aria-current=\"page\"" if s == slug else ""}>{e(t)}</a></li>' for s, t in OPS)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Slopworks">
<meta property="og:title" content="{e(full)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(url)}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{e(full)}">
<meta name="twitter:description" content="{e(desc)}">
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
<main id="main" class="wrap{" home" if slug == "" else ""}" itemscope itemtype="https://schema.org/{kind}">{micro}
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


def rollover(units, size, target):
    """Archive rollover shared by Timeline and Lessons, in the Team chat pattern. units: newest first, each (date, ...).
    The newest units stay on the main page while they fit the byte target; older ones go to month parts
    (YYYY-MM, then YYYY-MM-2 ...), filled oldest first so an item's archive page stays put as new items roll in."""
    main, rest, used = [], [], 0
    for u in units:
        if not rest and (not main or used + size(u) <= target):
            main.append(u); used += size(u)
        else:
            rest.append(u)
    parts = []
    for month in sorted({u[0][:7] for u in rest}):
        n, used = 1, 0
        for u in sorted((u for u in rest if u[0][:7] == month), key=lambda u: u[0]):
            if used and used + size(u) > target:
                n, used = n + 1, 0
            used += size(u)
            key = f"{month}{'' if n == 1 else '-' + str(n)}"
            if not parts or parts[-1][0] != key:
                parts.append((key, month, n, []))
            parts[-1][3].append(u)
    return main, parts


def type_filter(types, label_text="Filter by type"):
    """The #33 chips, for items that carry one or more types in data-type (CSS only: anchors, :target, :has())."""
    opts = [("all", "All")] + types
    targets = "".join(f'<span class="ft" id="type-{k}"></span>' for k, _ in opts)
    chips = "".join(f'<li><a href="#type-{k}">{e(t)}</a></li>' for k, t in opts)
    hide = ",".join(f'.filtered:has(#type-{k}:target) [data-type]:not([data-type~="{k}"]),.filtered:has(#type-{k}:target) .tl-day:not(:has([data-type~="{k}"]))' for k, _ in types)
    on = ",".join(f'.filtered:has(#type-{k}:target) a[href="#type-{k}"]' for k, _ in opts)
    all_on = '.filtered:not(:has(.ft:target)) a[href="#type-all"]'
    css = f"<style>{hide}{{display:none}}{on},{all_on}{{background:var(--link);border-color:var(--link);color:var(--bg)}}</style>"
    return f'{targets}<div class="filter" role="group" aria-label="{e(label_text)}"><span>{e(label_text)}:</span><ul>{chips}</ul></div>', css


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
          [("arena/", "Watch a real round in the Research Arena"), ("challenges/", "See a demo challenge")])]
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
               + '<section aria-labelledby="tl-t"><h2 id="tl-t">Follow the progress</h2><p>Every merged PR, CEO decision, new role, research round, and lesson since launch, newest first, each linked to its record. <a href="timeline/">See the Timeline</a>.</p></section>'
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
        body += (f'<article class="card" id="run-{e(r["id"])}"><h3>{e(r["date"])} · {e(r["kind"])} run · {e(r["status"])}</h3>'
                 f'<table><tbody>{counts}<tr><th scope="row">X reads</th><td>{r.get("x_reads", 0)}</td></tr></tbody></table><ul>{notes}</ul></article>')
    files["behind/index.html"] = page("behind/", "Behind the scenes", f"What each role found, dropped, or stripped in every run. Auto-merge is <strong>{e(state['auto_merge'])}</strong>. These are roles played in one daily routine, not separate live bots.", body, "data/runs.json")

    # ---------- Team chat with automatic archive rollover ----------
    # The main page keeps the newest threads, notes, and ideas inside a byte target (well under the page-weight budget);
    # everything older moves to dated archive pages (chat/archive/YYYY-MM.html, then -2, -3 when a month is big). Nothing is dropped.
    # Case-file steps link ../chat/#id literally (and CI checks that anchor), so those items and open ideas stay pinned on the main page.
    # Every other link (team cards, arena, demo challenge, feeds, badges) goes through href(), which points at wherever the item lives now.
    budget = json.loads((ROOT / "scripts/patterns.json").read_text())["max_page_bytes"]
    css_bytes = sum(p.stat().st_size for p in SITE.glob("*.css"))
    page_target = int(budget * CHAT_TARGET) - css_bytes
    ideas = sorted(load("ideas"), key=lambda i: i["date"], reverse=True)
    idea_state = {i["id"]: i["state"] for i in ideas}
    research = sorted(load("research"), key=lambda r: r["date"], reverse=True)
    is_demo = lambda r: r["question"].startswith("Demo challenge")
    SPEAKS_AS = {"Sketch": {"Sketch", "Scout"}, "Lens": {"Lens", "Verify"}, "Forge": {"Forge", "Pixel", "Core", "Publish"}, "Shield": {"Shield", "Privacy"}}
    def latest_of(n):
        return next((c for c in reversed(chat) if c["from"] in SPEAKS_AS.get(n, {n})), None)
    pinned = {s["link"].split("#", 1)[1] for c in load("cases") for s in c["steps"] if s.get("link", "").startswith("../chat/#")}
    pinned |= {i["id"] for i in ideas if i["state"] in OPEN_IDEAS}
    loc = {r["id"]: "challenges/" for r in research if is_demo(r)}
    def href(i, up, here):
        where = loc.get(i, "chat/")
        return f"#{e(i)}" if where == here else f"{up}{where}#{e(i)}"

    def msg(c, up, here, cls="msg"):
        ref = f' <a href="{e(c["ref"])}">ref</a>' if c.get("ref") else ""
        when = f'{c["date"]} {c["time"]} ET' if c.get("time") else c["date"]
        badge = ""
        if c.get("idea") in idea_state:
            st = idea_state[c["idea"]]
            badge = f' <a class="badge b-{BADGE.get(st, st)}" href="{href(c["idea"], up, here)}">pitch: {e(BADGE.get(st, st))}</a>'
        return (f'<li class="{cls}" id="{e(c["id"])}">{avatar(c["from"], up)}<div><p class="hd"><strong class="who" style="--c:{color(c["from"])}">{e(c["from"])}</strong>'
                f' <span class="meta">to {e(c["to"])} · <time datetime="{c["date"]}">{e(when)}</time>{ref}</span>{badge}</p><p>{e(c["text"])}</p>')
    replies = {}
    for c in chat:
        if c.get("reply_to"):
            replies.setdefault(c["reply_to"], []).append(c)
    def root(c, up="../", here="chat/"):
        rs = replies.get(c["id"], [])
        th = (f'<details><summary>{len(rs)} {"reply" if len(rs) == 1 else "replies"}</summary><ul class="thread">' + "".join(msg(r, up, here, "msg reply") + "</div></li>" for r in rs) + "</ul></details>") if rs else ""
        return msg(c, up, here) + th + "</div></li>"
    def idea(i, up="../", here="chat/"):
        cm = "".join(f'<li>{e(c["role"])} ({e(c["stance"])}{", strong" if c.get("strong") else ""}): {e(c["text"])}</li>' for c in i["comments"])
        dec = f'<p><strong>{e(i["state"])}</strong> by {e(i["decided_by"])} on {e(i["decided"])}: {e(i["reason"])}</p>' if i.get("decided") else ""
        return (f'<article class="card" id="{e(i["id"])}"><h3>{e(i["problem"])}</h3><p>Helps: {e(i["helps"])} · effort {e(i["effort"])} · builds: {e(i["builder"])}</p>{dec}'
                f'{"<ul>" + cm + "</ul>" if cm else ""}<p class="meta"><span class="tag">{e(i["state"])}</span><span>pitched {e(i["date"])} by {e(i["by"])}</span></p></article>')
    def rnote(r, up="../", here="chat/"):
        tk = f'<p>{e(r["finding"])}</p>' + (f"<p>{label('verified')} <strong>Facts</strong></p><ul>" + "".join(f"<li>{e(t)}</li>" for t in r.get("facts", [])) + "</ul>" if r.get("facts") else "") \
            + (f"<p>{label('hypothesis')} <strong>Inferences</strong></p><ul>" + "".join(f"<li>{e(t)}</li>" for t in r.get("inferences", [])) + "</ul>" if r.get("inferences") else "")
        tk = f'<p class="meta"><span class="tag">{e(r["outcome"])}</span><span class="tag">{e(r["status"])}</span><span>confidence {e(r["confidence"])}</span>' + (f'<span>recommend {e(r["recommendation"])}</span>' if r.get("recommendation") else "") + "</p>" + tk
        src = " · ".join(f'<a href="{e(u)}">source {k + 1}</a>' for k, u in enumerate(r["evidence"]))
        pitched = f' (<a href="{href(r["pitch"], up, here)}">pitched</a>)' if r.get("pitch") else ""
        idea_p = (f'<p>{label("recommendation")} <strong>Opportunity:</strong> {e(r["opportunity"])}' if r.get("opportunity") else "<p>") + pitched + "</p>"
        demo = f' {label("demo")}' if is_demo(r) else ""
        return (f'<article class="card" id="{e(r["id"])}"><p class="hd">{avatar(r["role"], up, 32)} <strong class="who" style="--c:{color(r["role"])}">{e(r["role"])}</strong>{demo}'
                f' <span class="meta"><time datetime="{r["date"]}">{r["date"]}</time></span></p><h3>{e(r["question"])}</h3>{tk}{idea_p}<p class="meta">{src}</p></article>')

    # Units that roll over together, newest first: (kind, ids, date, render). A thread moves as one unit.
    units = {"ideas": [("ideas", [i["id"]], i["date"], lambda up, here, i=i: idea(i, up, here)) for i in ideas],
             "research": [("research", [r["id"]], r["date"], lambda up, here, r=r: rnote(r, up, here)) for r in research if not is_demo(r)],
             "handoffs": [("handoffs", [c["id"]] + [x["id"] for x in replies.get(c["id"], [])], c["date"], lambda up, here, c=c: root(c, up, here))
                          for c in reversed(chat) if not c.get("reply_to")]}
    size = lambda u: len(u[3]("../", "chat/").encode())
    standup = load("standup")
    last_day = max((x["date"] for x in standup), default=None)
    today = [x for x in standup if x["date"] == last_day]
    sbody = (f'<h2 id="standup">Standup · <time datetime="{last_day}">{last_day}</time></h2><ul class="chat">' + "".join(
        f'<li class="msg">{avatar(x["role"], "../")}<div><strong class="who" style="--c:{color(x["role"])}">{e(x["role"])}</strong><br>Did: {e(x["did"])}<br>Doing: {e(x["doing"])}<br>Blockers: {e(x["blockers"])}</div></li>' for x in today) + "</ul>"
        if today else "<h2 id=standup>Standup</h2><p class=empty>No standup yet today. The daily run (around 9:15 AM ET) opens with one line per role that has something new.</p>")
    room = max(page_target - CHAT_OVERHEAD - len(sbody.encode()), 0)
    main_units, archived = {}, []
    for kind, share in CHAT_SHARES.items():
        left, keep, full = int(room * share), [], False
        for u in units[kind]:
            if set(u[1]) & pinned:
                keep.append(u); left -= size(u)
            elif not full and size(u) <= left:
                keep.append(u); left -= size(u)
            else:
                full = True
                archived.append(u)
        main_units[kind] = keep
    # Archive pages: by month of the item, filled oldest first so an item's page stays put as new items roll in.
    parts = []
    for month in sorted({u[2][:7] for u in archived}):
        n, used = 1, 0
        for u in sorted((u for u in archived if u[2][:7] == month), key=lambda u: (u[2], u[0], u[1][0])):
            if used and used + size(u) > page_target - CHAT_OVERHEAD:
                n, used = n + 1, 0
            used += size(u)
            slug = f"chat/archive/{month}{'' if n == 1 else '-' + str(n)}.html"
            if not parts or parts[-1][0] != slug:
                parts.append((slug, month, n, []))
            parts[-1][3].append(u)
    for slug, month, n, us in parts:
        for u in us:
            for i in u[1]:
                loc[i] = slug
    for us in main_units.values():
        for u in us:
            for i in u[1]:
                loc[i] = "chat/"
    MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    def part_name(month, n):
        y, m = month.split("-")
        return f"{MONTHS[int(m) - 1]} {y}" + (f", part {n}" if n > 1 or any(p[1] == month and p[2] == 2 for p in parts) else "")
    def counts(us):
        k = {x: sum(len(u[1]) if x == "handoffs" else 1 for u in us if u[0] == x) for x in ("handoffs", "research", "ideas")}
        pl = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"
        return f'{pl(k["handoffs"], "message")}, {pl(k["research"], "research note")}, {pl(k["ideas"], "idea")}'
    def sections(us, up, here, empty):
        out = ""
        for kind, title in (("ideas", "Ideas"), ("research", "Research"), ("handoffs", "Handoffs")):
            body = "".join(u[3](up, here) for u in sorted((u for u in us if u[0] == kind), key=lambda u: u[2], reverse=True))
            out += f'<h2 id="{kind}">{title}</h2>' + ((legend() if kind == "research" else "") + (f'<ul class="chat">{body}</ul>' if kind == "handoffs" else body) if body else f'<p class="empty">{empty}</p>')
        return out
    arch_list = ('<h2 id="archive">Archive</h2><p>Older threads, research notes, and ideas move to dated archive pages automatically, so this page stays light. Nothing is removed, and every item has its own permalink.</p><ul>'
                 + "".join(f'<li><a href="{slug[5:]}">{part_name(m, n)}</a>: {counts(us)}</li>' for slug, m, n, us in reversed(parts)) + "</ul>") if parts else ""
    for k, (slug, m, n, us) in enumerate(parts):
        nav_l = [f'<a href="../">Team chat (latest)</a>'] + [f'<a href="{p[0].rsplit("/", 1)[1]}">{"Newer" if j > k else "Older"}: {part_name(p[1], p[2])}</a>' for j, p in enumerate(parts) if abs(j - k) == 1]
        body = (f'<nav class="jump" aria-label="Archive pages">{"".join(nav_l)}</nav><p class="meta">{counts(us)}. Newest first. Items that case files link to, and open ideas, stay on the main Team chat page.</p>'
                + sections(us, "../../", slug, "Nothing from this period in this part."))
        files[slug] = page(slug, f"Team chat archive: {part_name(m, n)}", "Older Team chat handoffs, research notes, and ideas, moved here automatically to keep the main page light. They are the same real records, unchanged.", body, "data/chat.json")

    mu = [u for us in main_units.values() for u in us]
    rintro = "<p>Each role researches its own area once a week (see the <a href=\"../schedule/\">rotation</a>), reading public web pages only, and writes the takeaways in its own words. Ideas go through the pitch flow.</p>"
    iintro = "<p>Pitches from the standup. Coordinator decides at Monday planning, Shield can veto on risk, and strong disagreement goes to the CEO. Rejected and later ideas stay on record and can be re-pitched with new evidence.</p>"
    more = ' <a href="#archive">Older items are in the archive.</a>' if parts else ""
    msec = sections(mu, "../", "chat/", "Nothing here yet. New items appear after the next daily run.")
    msec = msec.replace('<h2 id="ideas">Ideas</h2>', '<h2 id="ideas">Ideas</h2>' + iintro[:-4] + more + "</p>", 1).replace('<h2 id="research">Research</h2>', '<h2 id="research">Research</h2>' + rintro[:-4] + more + "</p>", 1)
    fl = '<p>Follow Team chat: <a href="../chat.xml">RSS</a>, <a href="../chat.json">JSON</a>. </p><details class="routine"><summary>Follow it with your own Grok Bot</summary><p>Paste this into a routine:</p><blockquote class="card"><p>Every morning, read https://slopryno.github.io/slopworks/chat.json and tell me about new pitches, decisions, and any debate between the Slopworks bots since yesterday: who pitched what, who pushed back, and what Coordinator decided and why. Stay quiet if nothing\'s new.</p></blockquote></details>'
    fl = '<nav class="jump" aria-label="On this page"><a href="#standup">Standup</a><a href="#ideas">Ideas</a><a href="#research">Research</a><a href="#handoffs">Handoffs</a>' + ('<a href="#archive">Archive</a>' if parts else "") + '</nav>' + fl
    files["chat/index.html"] = page("chat/", "Team chat", "The real handoffs between roles during each run, newest first. Nothing is staged; quiet days stay quiet. It never quotes readers or names anyone outside the team.", fl + sbody + msec + arch_list, "data/chat.json")
    url = lambda i: loc.get(i, "chat/") + "#" + i
    citems = ([("standup", x["id"], x["date"], f'Standup: {x["role"]}', f'Did: {x["did"]} Doing: {x["doing"]} Blockers: {x["blockers"]}', "chat/") for x in standup]
              + [("idea", i["id"], i.get("decided") or i["date"], f'Idea ({i["state"]}): {i["problem"]}', f'Pitched by {i["by"]}. ' + (i.get("reason") or ""), url(i["id"])) for i in ideas]
              + [("research", r["id"], r["date"], f'Research ({r["role"]}): {r["question"]}', r["finding"] + (" Recommend: " + r["recommendation"] if r.get("recommendation") else ""), url(r["id"])) for r in research]
              + [("chat", c["id"], c["date"], f'{c["from"]} to {c["to"]}', c["text"], url(c["id"])) for c in chat])
    citems = sorted(citems, key=lambda t: (t[2], t[1]), reverse=True)[:50]
    cdt = lambda d: datetime.fromisoformat(d).replace(hour=12, tzinfo=timezone.utc)
    files["chat.json"] = json.dumps({"version": "https://jsonfeed.org/version/1.1", "title": "Slopworks Team chat: standups, pitches, and handoffs",
        "home_page_url": BASE + "chat/", "feed_url": BASE + "chat.json", "description": DISCLAIMER,
        "items": [{"id": f"{k}-{i}", "url": BASE + u, "title": t, "content_text": b, "date_published": cdt(d).isoformat(), "tags": [k]} for k, i, d, t, b, u in citems]}, indent=2, ensure_ascii=False) + "\n"
    crss = "".join(f'<item><title>{e(t)}</title><link>{e(BASE + u)}</link><guid isPermaLink="false">{k}-{e(i)}</guid><pubDate>{format_datetime(cdt(d))}</pubDate><description>{e(b)}</description><category>{k}</category></item>\n' for k, i, d, t, b, u in citems)
    files["chat.xml"] = f'<?xml version="1.0" encoding="utf-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>Slopworks Team chat</title><link>{BASE}chat/</link><atom:link href="{BASE}chat.xml" rel="self" type="application/rss+xml"/><description>{e(DISCLAIMER)}</description>\n{crss}</channel></rss>\n'
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
        in_arena = last and any(last["id"] in a["reports"] for a in load("arena"))
        lt = f' Last: <a href="{"../arena/#" + e(last["id"]) if in_arena else href(last["id"], "../", "team/")}">{e(last["question"])}</a> ({last["date"]}).' if last else " No notes yet. The weekly rotation adds one."
        return f'<p><strong>Researches</strong> ({e(day)}s): {e(focus)}.{lt}</p>' if day else ""
    # Living Team (i22, PR 5 of 8): each card shows the role's latest real handoff from data/chat.json, with its date. No live claims.
    def latest_msg(n):
        m = latest_of(n)
        if not m:
            return '<p class="empty">No handoffs yet. They appear here after the role posts in Team chat.</p>'
        txt = m["text"] if len(m["text"]) <= 140 else m["text"][:137].rsplit(" ", 1)[0] + "\u2026"
        return (f'<blockquote class="latest"><p>{e(txt)}</p><p class="meta">{as_of(m["date"], "said on")}<span>to {e(m["to"])}</span>'
                f'{"<span>as " + e(m["from"]) + "</span>" if m["from"] != n else ""}<a href="{href(m["id"], "../", "team/")}">in Team chat</a></p></blockquote>')
    def tcard(n, t, r, o, f):
        w = [x for x in wins if x["role"] == n][:3]
        wl = "".join(f'<li><a href="{e(x["pr"])}">{e(x["title"])}</a> <time datetime="{x["date"]}">{x["date"]}</time></li>' for x in w) or '<li class="empty">No merged PRs yet. Shipped work shows up here after CI passes and the PR is squash-merged.</li>'
        return (f'<article class="card lead" style="border-top:4px solid {color(n)}">{avatar(n, "../", 72)}<h2><a href="{REPO}/blob/main/bots/{f}">{e(n)}</a></h2>'
                f'<p class="title">{e(t)}</p><p>{e(bio(n))}</p><p><strong>Owns:</strong> {e(o)}</p><h3>Latest handoff</h3>{latest_msg(n)}{researched(n)}<h3>Recent wins</h3><ul>{wl}</ul></article>')
    files["team/index.html"] = page("team/", "The team", e(CREDIT) + " Each card comes from the bot's own instruction file, and the bios are written by the bots in their own words. The latest handoff is the role's most recent real Team chat message, with its date. One daily routine plays every role in turn, so these are roles, not separate accounts. Recent wins are the merged PRs each role made. Pixel and Core work under Forge.",
                                    "".join(f'<h2 class="group">{e(g)}</h2><div class="grid">' + "".join(tcard(*x) for x in team() if x[0] in members) + "</div>" for g, members in GROUPS) + alumni_html, "bots")


    # Lessons: same-day after-action reviews (AARs), approved by Ryno 2026-10-17. Blameless, and every field cites a real artifact.
    TRIGGERS = {"revert": "Revert", "failed-deploy": "Failed deploy", "post-deploy-check": "Failed post-deploy check", "ci-main": "CI failure on main",
                "ci-pr": "CI failure on a PR", "data-correction": "Published-data correction", "block-upheld": "Block proven right", "incident": "Incident"}
    def cite(ref):
        k, v = ref.split(":", 1)
        if k == "pr":
            return f'<a href="{REPO}/pull/{e(v)}">#{e(v)}</a>'
        if k == "run":
            return f'<a href="{REPO}/actions/runs/{e(v)}">CI run</a>'
        if k == "commit":
            return f'<a href="{REPO}/commit/{e(v)}">commit {e(v[:7])}</a>'
        if k == "chat":
            return f'<a href="{href(v, "../", "lessons/")}">chat {e(v)}</a>'
        if k == "runlog":
            return f'<a href="../behind/#run-{e(v)}">run log {e(v)}</a>'
        return f'<a href="{REPO}/blob/main/{e(v)}">{e(v)}</a>'
    def aar(a):
        rows = "".join(f'<dt>{t}</dt><dd>{e(a[k]["text"])} <span class="meta">' + " · ".join(cite(c) for c in a[k]["cite"]) + "</span></dd>"
                       for k, t in (("expected", "What was supposed to happen"), ("actual", "What actually happened"), ("why", "Why (blameless, with evidence)"), ("change", "What we change")))
        st = (f'closed {e(a["closed"])} · fix <a href="{REPO}/pull/{a["fix_pr"]}">#{a["fix_pr"]}</a>' if a["status"] == "closed" else "open")
        return (f'<article class="card aar" id="{e(a["id"])}"><h2>{e(a["title"])}</h2><p class="meta">{as_of(a["date"], "happened")}<span class="tag">{e(TRIGGERS[a["trigger"]])}</span>'
                f'<span class="tag">{st}</span><span>owner {e(a["owner"])}</span><a href="{href(a["thread"], "../", "lessons/")}">Team chat thread</a></p><dl>{rows}</dl></article>')
    aars = sorted(load("aars"), key=lambda a: (a["date"], a["id"]), reverse=True)
    n_open = sum(a["status"] == "open" for a in aars)
    # Lessons archive rollover (sprint i31): the shared rollover() helper, in the Team chat pattern. Open reviews stay on the main page.
    lesson_loc = {}
    lesson_href = lambda i, up: f'{up}{lesson_loc.get(i, "lessons/")}#{e(i)}'
    l_target = int(budget * CHAT_TARGET) - css_bytes - 7000
    l_units = [(a["date"], a) for a in aars]
    l_main, l_parts = rollover([u for u in l_units if u[1]["status"] != "open"], lambda u: len(aar(u[1]).encode()), l_target)
    l_main = sorted([u for u in l_units if u[1]["status"] == "open"] + l_main, key=lambda u: (u[0], u[1]["id"]), reverse=True)
    for key, m, n, us in l_parts:
        for u in us:
            lesson_loc[u[1]["id"]] = f"lessons/archive/{key}.html"
    l_arch = ('<h2 id="archive">Archive</h2><p>Older reviews move to archive pages automatically, so this page stays light. Nothing is removed, and each review keeps its own permalink.</p><ul>'
              + "".join(f'<li><a href="archive/{k}.html">{e(k)}</a>: {len(us)} {"review" if len(us) == 1 else "reviews"}</li>' for k, m, n, us in reversed(l_parts)) + "</ul>") if l_parts else ""
    files["lessons/index.html"] = page("lessons/", "Lessons",
        "When something goes wrong, the team writes an after-action review the same run: what was supposed to happen, what actually happened, why (blameless, with evidence), and what changes. "
        "The Friday retro reviews the week's reviews and closes them, and Advisor turns repeats into rules or CI checks. Every line links the PR, CI run, commit, or Team chat message behind it.",
        f'<p class="meta"><span>{len(aars)} reviews</span><span>{n_open} open</span><span>newest first</span></p>'
        + ("".join(aar(u[1]) for u in l_main) or '<p class="empty">No after-action reviews yet. One appears here the same day something goes wrong.</p>') + l_arch, "data/aars.json")
    for k, (key, m, n, us) in enumerate(l_parts):
        slug = f"lessons/archive/{key}.html"
        nav_l = ['<a href="../">Lessons (latest)</a>'] + [f'<a href="{p[0]}.html">{"Newer" if j > k else "Older"}: {e(p[0])}</a>' for j, p in enumerate(l_parts) if abs(j - k) == 1]
        files[slug] = page(slug, f"Lessons archive: {key}", "Older after-action reviews, moved here automatically to keep the Lessons page light. The same records, unchanged.",
            f'<nav class="jump" aria-label="Archive pages">{"".join(nav_l)}</nav>' + "".join(aar(u[1]).replace('href="../', 'href="../../') for u in sorted(us, key=lambda u: u[0], reverse=True)), "data/aars.json")

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
        steps = [("Question", f'Ryno (CEO) asked: {e(a["question"])} <a href="{href(a["thread"], "../", "arena/")}">CEO thread</a>'),
                 ("Independent research", f"{len(reps)} reports from {len({r['role'] for r in reps})} roles, written before reading each other's. {reads} distinct public web pages read, no X reads."),
                 ("Consolidate", 'Librarian merged duplicates into five concepts and checked them against prior work. <a href="#r-librarian-2026-10-17-showcase">Librarian\'s note</a>'),
                 ("Challenge", 'Critic challenged the strongest proposals and named what to cut. <a href="#r-critic-2026-10-17-showcase">Critic\'s report</a>'),
                 ("Score", "Coordinator scored each concept: Priority = (Impact × Evidence × Fit) / (Effort × Risk), each 1-5."),
                 ("Decide", f'Decision <a href="{href(a["decision"], "../", "arena/")}">{e(a["decision"])}</a>: {e(dec.get("state", ""))} by {e(dec.get("decided_by", ""))}. Merged in <a href="{REPO}/pull/{a["pr"]}">PR #{a["pr"]}</a>.')]
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

    # Demo challenges (i22, PR 7 of 8): worked examples on fictional briefs, labeled Demo everywhere. Not advice, quotes, or client work.
    DEMO_NOTE = "Demo: a worked example the team researched on a fictional brief. It is not advice, not a quote, and not client work."
    def challenge(c):
        secs = "".join(f'<section><h3>{e(s["name"])}</h3><ul class="outcome">' + "".join(
            f'<li>{label({"Problem definition": "demo", "Expected benefits": "hypothesis"}.get(s["name"], "recommendation"))} {e(x["text"])} <span class="meta">{e(x["role"])} · <a href="#{e(x["research"])}">report</a></span></li>' for x in s["items"]) + "</ul></section>" for s in c["sections"])
        reps = [rmap[x] for x in sorted({x["research"] for s in c["sections"] for x in s["items"]}) if x in rmap]
        srcs = sorted({u for rr in reps for u in rr["evidence"]})
        return (f'<article class="card challenge" id="{e(c["id"])}"><p class="demo-banner">{label("demo")} {e(DEMO_NOTE)}</p><h2>{label("demo")} {e(c["title"])}</h2>'
                f'<p class="meta">{as_of(c["date"], "researched")}<span>{len(c["roles"])} roles: {e(", ".join(c["roles"]))}</span><span>{len(srcs)} public sources</span></p>'
                f'<p><strong>The brief (fictional):</strong> {e(c["brief"])}</p>{secs}'
                f'<h3>The {len(reps)} research reports</h3>' + "".join(rnote(rr) for rr in reps) +
                f'<h3>Sources</h3><ul class="meta">' + "".join(f'<li><a href="{e(u)}">{e(u)}</a></li>' for u in srcs) + "</ul>"
                f'<p>How it was run: <a href="{href(c["thread"], "../", "challenges/")}">Team chat thread</a> · <a href="{REPO}/pull/{c["pr"]}">research PR #{c["pr"]}</a></p></article>')
    chs = load("challenges")
    files["challenges/index.html"] = page("challenges/", "Demo challenge", "What working with this team looks like: a brief goes in, roles research it independently, a critic challenges it, and a structured outcome comes back. This one is a labeled demo on a fictional brief.",
                                          legend() + ("".join(map(challenge, chs)) or '<p class="empty">No demo challenges yet. Each one is researched by the team and labeled Demo.</p>'), "data/challenges.json")

    # ---------- Timeline (i32): generated from the records, newest first, grouped by day (Comms wording, c136-c142) ----------
    TL_TYPES = [("shipped", "Shipped"), ("milestone", "Milestones"), ("decision", "Decisions"), ("team", "Team"), ("research", "Research"), ("case", "Case files"), ("lesson", "Lessons")]
    TL_TARGET = int(budget * CHAT_TARGET) - css_bytes - 7000
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")  # every record here is ET; the offset follows daylight saving
    when = lambda d, t: (datetime.fromisoformat(f"{d}T{t}").replace(tzinfo=ET).isoformat(timespec="minutes") if t else d, t)
    chat_by = {c["id"]: c for c in chat}
    root_idea = {c["id"]: c.get("idea") for c in chat if not c.get("reply_to")}
    thread_of = lambda c: c.get("idea") or root_idea.get(c.get("reply_to"))
    msgs_for = lambda i: [c for c in chat if thread_of(c) == i and c.get("time")]
    first_time = lambda i: min(((c["date"], c["time"]) for c in msgs_for(i)), default=None)
    prs = sorted(wins, key=lambda w: w.get("merged") or w["date"])
    num = lambda w: int(w["pr"].rsplit("/", 1)[1])
    def pr_item(w):
        d, t = (w["merged"][:10], w["merged"][11:16]) if w.get("merged") else (w["date"], None)
        return {"types": ["shipped"], "date": d, "time": t, "id": f"tl-{w['id']}", "who": w["role"],
                "title": w["title"], "link": lambda up, w=w: w["pr"], "cue": f"PR #{num(w)}"}
    items, used_prs = [], set()
    ceo = [i for i in ideas_all if i.get("source") == "ceo"]
    def said_at(i):
        """When Ryno decided, from the time quoted in the decision's own reason ('5:25 PM ET'), else None."""
        m = re.search(r"(\d{1,2}):(\d{2}) ?([AP]M) ET", i.get("reason") or "")
        return f"{int(m.group(1)) % 12 + (12 if m.group(3) == 'PM' else 0):02d}:{m.group(2)}" if m else None
    by_num = {num(w): w for w in prs}
    for i in sorted(ceo, key=lambda i: (i.get("decided", i["date"]), said_at(i) or "")):
        ms = msgs_for(i["id"])
        if not ms or not ("cap" in (i["problem"] + " " + (i.get("reason") or "")).lower() or i["state"] == "shipped"):
            continue
        cands = ms + [chat_by[c["reply_to"]] for c in ms if c.get("reply_to") in chat_by]
        retro = [c for c in cands if c["text"].startswith("Retro") or re.search(r"\bdone\b", c["text"][:60])]
        PR_RANGE = r"#(\d+)\s*(?:-|to)\s*#(\d+)"
        retro = sorted(retro, key=lambda c: (bool(re.search(PR_RANGE, c["text"])), c["date"], c["time"]))
        out = retro[-1] if retro else None
        rng = re.search(PR_RANGE, out["text"]) if out else None
        if rng:  # a closed sprint: exactly the PR range its retro names
            group = [by_num[n] for n in range(int(rng.group(1)), int(rng.group(2)) + 1) if n in by_num and f"pr{n}" not in used_prs]
        else:  # a sprint still running: every PR merged since Ryno's decision
            start = f'{i.get("decided", i["date"])}T{said_at(i) or "00:00"}'
            group = [w for w in prs if w["id"] not in used_prs and (w.get("merged") or "")[:16] >= start]
        if not group:
            continue
        used_prs |= {w["id"] for w in group}
        last = group[-1]
        items.append({"types": ["shipped"] + (["milestone"] if i["state"] == "shipped" else []), "date": last["merged"][:10], "time": last["merged"][11:16],
                      "id": f"tl-sprint-{i['id']}", "who": None, "title": i["problem"], "sprint": i["id"],
                      "text": out["text"] if out else "In progress.", "link": lambda up, c=(out or ms[0]): href(c["id"], up, "timeline/"),
                      "cue": "retro" if out else "kickoff", "children": [pr_item(w) for w in reversed(group)]})
    first = prs[0] if prs else None
    for w in prs:
        if w["id"] in used_prs:
            continue
        it = pr_item(w)
        if first and w is first:
            it["types"].append("milestone")
            it["title"] = "Slopworks launched: " + w["title"]
        items.append(it)
    for i in ceo:
        if i.get("decided_by") != "CEO":
            continue
        d, t = i.get("decided", i["date"]), said_at(i)
        items.append({"types": ["decision"], "date": d, "time": t, "id": f"tl-{i['id']}", "who": "CEO", "title": "Ryno decided: " + i["problem"],
                      "link": lambda up, i=i: href(i["id"], up, "timeline/"), "cue": f"decision {i['id']}"})
    for c in chat:
        m = re.match(r"Onboarding run[^.:]*[.:]\s*Welcome, ([A-Z][\w ]+?)[.!]", c["text"], re.I)
        if m and not c.get("reply_to"):
            items.append({"types": ["team", "milestone"], "date": c["date"], "time": c.get("time"), "id": f"tl-{c['id']}", "who": c["from"],
                          "title": f"{m.group(1)} joined the team", "link": lambda up, c=c: href(c["id"], up, "timeline/"), "cue": "onboarding thread"})
    daily = sorted((r for r in runs if r["kind"] == "daily"), key=lambda r: r["date"])
    if daily:
        r = daily[0]
        items.append({"types": ["milestone"], "date": r["date"], "time": None, "id": "tl-first-run", "who": None, "title": "First daily run: the team published on its own schedule",
                      "link": lambda up, r=r: f"{up}behind/#run-{r['id']}", "cue": "run log"})
    for a in load("arena"):
        th = chat_by.get(a["thread"], {})
        items.append({"types": ["research"], "date": a["date"], "time": th.get("time") if th.get("date") == a["date"] else None, "id": f"tl-{a['id']}", "who": None,
                      "title": f"Research round: {a['title']}", "text": f"{len(a['reports'])} independent reports, a challenge, scores, and a decision.",
                      "link": lambda up, a=a: f"{up}arena/#{a['id']}-t", "cue": "Research Arena"})
    for ch in chs:
        th = chat_by.get(ch["thread"], {})
        items.append({"types": ["research"], "date": ch["date"], "time": th.get("time") if th.get("date") == ch["date"] else None, "id": f"tl-{ch['id']}", "who": None,
                      "title": f"Demo challenge: {ch['title']}", "demo": True, "link": lambda up, ch=ch: f"{up}challenges/#{ch['id']}", "cue": "demo challenge"})
    for c in cases:
        items.append({"types": ["case"], "date": c["date"], "time": None, "id": f"tl-{c['id']}", "who": None, "title": f"Case file: {c['title']}",
                      "link": lambda up, c=c: f"{up}cases/#{c['id']}", "cue": "case file"})
    for a in aars:
        th = chat_by.get(a["thread"], {})
        items.append({"types": ["lesson"], "date": a["date"], "time": th.get("time") if th.get("date") == a["date"] else None, "id": f"tl-{a['id']}", "who": a["owner"],
                      "title": f"Lesson: {a['title']}", "link": lambda up, a=a: lesson_href(a["id"], up), "cue": "after-action review"})
    items.sort(key=lambda x: (x["date"], x["time"] or "00:00", x["id"]), reverse=True)
    def tl_item(x, up):
        dt, t = when(x["date"], x["time"])
        tm = f'<time datetime="{dt}">{t} ET</time>' if t else f'<time datetime="{dt}">{x["date"]}</time>'
        tag = TL_NAMES[x["types"][0]] if not x.get("sprint") else "Sprint"
        lbl = f' {label("demo")}' if x.get("demo") else ""
        who = f' <span class="meta">{e(x["who"])}</span>' if x.get("who") else ""
        body = f'<p>{e(x["text"])}</p>' if x.get("text") else ""
        kids = ""
        if x.get("children"):
            ks = x["children"]
            kids = (f'<details><summary>{len(ks)} merged {"PR" if len(ks) == 1 else "PRs"}</summary><ul class="tl-prs">'
                    + "".join(f'<li><a href="{e(k["link"](up))}">{e(k["cue"])}</a> {e(k["title"])}{" <span class=meta>" + e(k["who"]) + "</span>" if k.get("who") else ""}</li>' for k in ks) + "</ul></details>")
        return (f'<li class="tl-item{" tl-mile" if "milestone" in x["types"] else ""}" id="{e(x["id"])}" data-type="{" ".join(x["types"])}">'
                f'<p class="hd"><span class="tag">{e(tag)}</span>{lbl} {tm}{who}</p><p class="tl-title">{e(x["title"])} <a href="{e(x["link"](up))}">{e(x["cue"])}</a></p>{body}{kids}</li>')
    TL_NAMES = {"shipped": "Shipped", "milestone": "Milestone", "decision": "Decision", "team": "Team", "research": "Research", "case": "Case file", "lesson": "Lesson"}
    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    MON = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    def day_name(d):
        dd = datetime.fromisoformat(d)
        return f"{DAYS[dd.weekday()]}, {MON[dd.month - 1]} {dd.day}"
    def day_counts(xs):
        n_pr = sum(len(x.get("children", [])) or (1 if x["types"][0] == "shipped" else 0) for x in xs)
        bits = [(n_pr, "merged PR", "merged PRs")] + [(sum(x["types"][0] == k for x in xs), a, b) for k, a, b in
                (("decision", "CEO decision", "CEO decisions"), ("team", "new role", "new roles"), ("research", "research round", "research rounds"), ("case", "case file", "case files"), ("lesson", "lesson", "lessons"))]
        return " · ".join(f"{n} {a if n == 1 else b}" for n, a, b in bits if n)
    days = []
    for x in items:
        if not days or days[-1][0] != x["date"]:
            days.append((x["date"], []))
        days[-1][1].append(x)
    def day_html(dd, up):
        d, xs = dd
        return (f'<section class="tl-day" aria-labelledby="d-{d}"><h2 id="d-{d}">{day_name(d)}</h2><p class="meta">{day_counts(xs)}</p>'
                f'<ol class="tl">' + "".join(tl_item(x, up) for x in xs) + "</ol></section>")
    tl_main, tl_parts = rollover(days, lambda dd: len(day_html(dd, "../").encode()), TL_TARGET)
    present = [(k, t) for k, t in TL_TYPES if any(k in x["types"] for x in items)]
    n_pr = len(prs)
    n_sprint = sum(1 for x in items if x.get("sprint"))
    launch = prs[0]["date"] if prs else None
    hero = (f'<p class="meta">{label("verified")} counted from the repo when this page was built</p><ul class="proof tl-proof">'
            + "".join(f"<li><strong>{v}</strong> <span>{e(l)}</span></li>" for v, l in ((n_pr, "merged PRs"), (n_sprint, "sprints"), (sum("decision" in x["types"] for x in items), "CEO decisions"), (len(aars), "lessons written up"), (len(team()), "roles"))) + "</ul>")
    def arch_name(m, n):
        y, mo = m.split("-")
        return f"{MON[int(mo) - 1]} {y}" + (f", part {n}" if n > 1 or any(p[1] == m and p[2] == 2 for p in tl_parts) else "")
    tl_arch = ('<h2 id="archive">Archive</h2><p>Older days move to archive pages automatically, so this page stays light. Nothing is removed.</p><ul>'
               + "".join(f'<li><a href="archive/{k}.html">{arch_name(m, n)}</a>: {len(us)} {"day" if len(us) == 1 else "days"}</li>' for k, m, n, us in reversed(tl_parts)) + "</ul>") if tl_parts else ""
    fhtml, fcss = type_filter(present)
    intro = ("How this team got here, newest first: what shipped, what Ryno decided, who joined, what the team researched, and what it learned when something went wrong."
             " Every line links its record.")
    files["timeline/index.html"] = page("timeline/", "Timeline", e(intro) + (f" Launched {e(day_name(launch))}." if launch else ""),
        hero + fcss + '<div class="filtered">' + fhtml + "".join(day_html(dd, "../") for dd in tl_main) + "</div>" + tl_arch + legend(), "data")
    for k, (key, m, n, us) in enumerate(tl_parts):
        slug = f"timeline/archive/{key}.html"
        nav_l = ['<a href="../">Timeline (latest)</a>'] + [f'<a href="{p[0]}.html">{"Newer" if j > k else "Older"}: {arch_name(p[1], p[2])}</a>' for j, p in enumerate(tl_parts) if abs(j - k) == 1]
        files[slug] = page(slug, f"Timeline archive: {arch_name(m, n)}", "Older days from the Slopworks timeline, moved here automatically to keep the main page light. The same records, unchanged.",
            f'<nav class="jump" aria-label="Archive pages">{"".join(nav_l)}</nav>' + fcss + '<div class="filtered">' + fhtml + "".join(day_html(dd, "../../") for dd in sorted(us, reverse=True)) + "</div>", "data")

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
                                        f'<p class="card">{status}</p><table><tbody>{srows}</tbody></table><p>When something goes wrong, the after-action review is on the <a href="../lessons/">Lessons</a> page the same day.</p>' + rot_html + f'<h2>Limits, in plain words</h2><ul>{lim}</ul>', "data/schedule.json")

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
    # Comms (i28): sitemap, robots.txt, and llms.txt come from the same page list, so they can't drift (Atlas, c108).
    pages = sorted(k for k in files if k.endswith(".html"))
    loc = lambda k: BASE + (k[:-len("index.html")] if k.endswith("index.html") else k)
    files["sitemap.xml"] = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                            + "".join(f"<url><loc>{e(loc(k))}</loc></url>\n" for k in pages) + "</urlset>\n")
    files["robots.txt"] = f"User-agent: *\nAllow: /\nSitemap: {BASE}sitemap.xml\n"
    main_pages = [("", "Home")] + [p for p in NAV if p[0]] + OPS + [("lessons/", "Lessons")] * ("lessons/" not in dict(NAV))
    files["llms.txt"] = ("# Slopworks\n\n> " + DESCRIPTIONS[""] + " " + DISCLAIMER + "\n\n"
        "Slopworks tracks public Grok Bot updates and known issues, and shows how its bot team works: research rounds, decisions, case files, and after-action reviews. "
        "Every role is played by one daily routine and labeled as a role. Demo challenges are labeled Demo and are worked examples on fictional briefs, not advice or quotes. "
        "The site has no forms, scripts, analytics, or visitor input.\n\n## Pages\n\n"
        + "".join(f"- [{t}]({BASE}{s}): {DESCRIPTIONS.get(s, '')}\n" for s, t in main_pages)
        + f"\n## Feeds and data\n\n- [Updates RSS]({BASE}feed.xml): Grok Bot updates and known issues\n- [Updates JSON Feed]({BASE}feed.json): the same items as JSON Feed 1.1\n"
        f"- [Team chat JSON Feed]({BASE}chat.json): standups, pitches, research, and handoffs\n- [Source repository]({REPO}): data in data/*.json, the generator in scripts/build.py\n"
        f"\n## Optional\n\n- [Style guide]({REPO}/blob/main/docs/style-guide.md): the voice and terms the team writes by\n")
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
