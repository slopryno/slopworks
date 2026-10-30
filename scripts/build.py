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
BASE = "https://slopryno.com/"
REPO = "https://github.com/slopryno/slopworks"
CREDIT = "Built and designed by Grok Bots. Reviewed and merged by bots; steered by a human CEO (Ryno)."
DISCLAIMER = "Unofficial, fan-built project. Not affiliated with or endorsed by Grok Bot, SpaceX, or X."
CORRECTIONS = "slopryno+corrections@mail.grokbot.com"
# Information architecture (i36, Team chat c210 to c214): 4 top items plus the brand as Home. Deeper pages sit one tap
# from their hub, every deep page has one "Back to" link, and the footer lists every page. No URL moved.
WORK = [("timeline/", "Timeline"), ("weekly/", "Weekly recap"), ("metrics/", "Metrics"), ("roadmap/", "Quest board"), ("cases/", "Case files"), ("arena/", "Research Arena"), ("challenges/", "Demo challenge")]
HOOD = [("how/", "How this works"), ("updates/", "What's new"), ("issues/", "Known issues"), ("chat/", "Team chat"), ("schedule/", "Schedule and limits"), ("calendar/", "Calendar"), ("behind/", "Behind the scenes"), ("design/", "Design log")]
TOP = [("work/", "Work"), ("team/", "Team"), ("lessons/", "Lessons"), ("hood/", "Under the hood")]
NAV = [("", "Home")] + WORK + [("team/", "Team"), ("lessons/", "Lessons"), ("how/", "How this works")]  # every visitor page, for llms.txt and the footer
OPS = HOOD


def section(slug):
    """(hub slug, hub title) a page belongs to, for the nav highlight and its Back link."""
    for hub, pages in (("work/", WORK), ("hood/", HOOD)):
        if any(slug.startswith(s) for s, _ in pages):
            return hub, dict(TOP)[hub]
    for s, title in TOP:
        if slug.startswith(s):
            return s, title
    return None, None


def back_link(slug, up):
    """One 'Back to' link on deep pages (Comms, c211): archives go back to their page, sheets to Team, the rest to their hub."""
    if slug in ("", "work/", "hood/", "team/", "lessons/"):
        return ""
    for base, title in (("chat/", "Team chat"), ("timeline/", "Timeline"), ("lessons/", "Lessons"), ("team/", "Team"), ("updates/", "What's new"), ("issues/", "Known issues")):
        if slug.startswith(base) and slug != base:
            return f'<p class="back"><a href="{up}{base}">Back to {title}</a></p>'
    hub, title = section(slug)
    return f'<p class="back"><a href="{up}{hub}">Back to {title}</a></p>' if hub else ""
e = lambda s: html.escape(str(s), quote=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from avatars import ROLES as AVATARS  # noqa: E402
from cal import run_time  # noqa: E402
# The daily run's time comes from data/schedule.json's daily cron, so no page hardcodes it (Ryno, 2026-10-20 10:15 AM ET).
RUN_TIME = run_time(json.loads((ROOT / "data/schedule.json").read_text()))
ALIAS = {"scout": "sketch", "verify": "lens", "privacy": "shield", "publish": "forge"}
GROUPS = [("Leadership and Strategy", ["Coordinator", "Strategy", "Scoutmaster", "Comms", "Assistant"]),
          ("Research and Intelligence", ["Sketch", "Advocate", "Librarian"]),
          ("Architecture and Development", ["Atlas", "Forge", "Polish"]),
          ("Quality and Governance", ["Lens", "Trial", "Shield", "Critic", "Advisor"]),
          ("Operations and Measurement", ["Sweep", "Analyst", "Gamemaster"])]
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


def trim_legend(body):
    """Explain only the labels a page actually shows, and drop the legend when it shows one kind or none (Critic, c212)."""
    if '<details class="legend">' not in body:
        return body
    full = re.search(r'<details class="legend">.*?</details>', body, re.S).group(0)
    rest = body.replace(full, "")
    kinds = [k for k in LABELS if f"lbl-{k}" in rest]
    keep = ('<details class="legend"><summary>How to read the labels</summary><ul>'
            + "".join(f"<li>{label(k)} {e(LABELS[k][2])}</li>" for k in kinds) + "</ul></details>") if len(kinds) > 1 else ""
    return body.replace(full, keep)


def avatar_of(name):
    n = name.lower()
    n = ALIAS.get(n, n)
    return n if n in AVATARS else "coordinator"


def avatar(name, up, size=40, move=False):
    """Long lists (Team chat, the Arena, cases) use the still copy; the Team page, role sheets and home cards animate."""
    a = avatar_of(name)
    return f'<img class="av" src="{up}assets/avatars/{"" if move else "still/"}{a}.svg" width="{size}" height="{size}" alt="">'


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


def pace_line(t, up):
    """Under the hood (i44): the pace the bots work at, straight from data/tempo.json (derived from wins and AARs)."""
    lim = t["limits"][t["mode"]]
    why = (f' since <a href="{up}lessons/#{e(t["tripped_by"])}">{e(t["tripped_by"])}</a> (#{t["trip_pr"]})' if t["mode"] == "slowed" else "")
    clean = f', {t["clean_prs"]} of {t["clean_needed"]} clean PRs{why}' if t["mode"] == "slowed" else ""
    return (f'<p class="pace"><strong>Pace: {e(t["mode"])}</strong>{clean}. Up to {lim["prs_per_day"]} merged PRs a day '
            f'({lim["sprints_per_day"]} {"sprint" if lim["sprints_per_day"] == 1 else "sprints"} of up to {lim["prs_per_sprint"]}). '
            f'A revert, CI failure on main, failed deploy, or incident or data-correction AAR slows it until {t["clean_needed"]} clean PRs merge. '
            f'A same-day after-action review can still ship when the day\'s limit is used up (Ryno, Oct 20). '
            f'<a href="https://github.com/slopryno/slopworks/blob/main/data/tempo.json">Source</a> · <a href="{up}metrics/">Metrics and trends</a></p>')


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
    import ceo_quotes  # Ryno, Oct 21 8:51 AM ET: no CEO quotes on the site; his words stay on the PR and in the records
    global _CEO_REG
    if _CEO_REG is None:
        _CEO_REG = ceo_quotes.registry(ROOT)
    return _typed(ceo_quotes.scrub_all(value, _CEO_REG), schema, f"data/{name}.json")


_CEO_REG = None


# How this works (i48, Comms; Ryno's external review, c-thread i48): plain words, and the numbers come from code so they can't drift.
def how_body(sched, up):
    import tempo
    gh = lambda path: f"{REPO}/blob/main/{path}"
    n, s = tempo.LIMITS["normal"], tempo.LIMITS["slowed"]
    loop = [("Scout", "Sketch", "reads public Grok Bot posts and docs and logs each update or known issue with its source.", "bots/sketch.md"),
            ("Verify", "Lens", "checks every fact and number against its source before it can publish.", "bots/lens.md"),
            ("Privacy", "Shield", "checks for personal data and secrets, and can veto.", "bots/shield.md"),
            ("Build", "a maker role", "makes the change on its own branch with scripts/bot.py, never on main.", "scripts/bot.py"),
            ("Review", "other roles", "sign off by the paths changed; CI runs every check, and design changes need screenshots of every page.", "scripts/check.py"),
            ("Publish", "Forge", "merges when checks pass; GitHub Pages rebuilds the site from the data files.", "bots/forge.md")]
    steps = "".join(f'<li><strong>{e(a)}</strong> ({e(who)}) {e(what)} <a href="{gh(src)}">Rule</a></li>' for a, who, what, src in loop)
    days = "; ".join(f'{e(d["day"])}: {e(", ".join(r["role"] for r in d["roles"]))}' for d in sched.get("research", []))
    terms = [("AAR", "After-action review: written the same day something goes wrong (what was expected, what happened, why, what changes).", f"{up}lessons/"),
             ("Block", "A reviewer stops a PR until it's fixed. A second Block on the same PR goes to Ryno.", gh("scripts/check.py")),
             ("Blast radius", "Atlas's note on a PR that touches shared files: what could break, for whom, how to roll back, and a size.", gh("bots/atlas.md")),
             ("ceo-approved", "The label only Ryno adds, to let a PR that loosens a safety check through. Bots never add it.", gh("scripts/check.py")),
             ("CI", "Checks that run on every PR: data schemas, sources, secrets, personal data, accessibility, page weight, tests.", gh(".github/workflows/ci.yml")),
             ("Maker", "The role that made a PR. It can't sign off its own work.", gh("scripts/bot.py")),
             ("needs-ceo", "The label for a real disagreement or a safety case. Nothing labelled needs-ceo merges until Ryno decides.", gh(".github/workflows/needs-ceo.yml")),
             ("Sign-off", "A reviewer's approval, posted on the PR. Which roles must sign off depends on the files changed.", gh("scripts/check.py")),
             ("Tempo", f"How fast the team may ship: up to {n['prs_per_day']} PRs a day normally, {s['prs_per_day']} a day after a revert, failed deploy, failure on main, incident or data correction, until {tempo.CLEAN_NEEDED} clean PRs merge. A same-day after-action review, and nothing else, may still ship once the day's limit is used up.", f"{up}metrics/"),
             ("XP", "Points a role earns only from verified work, each linked to its evidence and approved by another role.", f"{up}team/xp/")]
    gloss = "".join(f'<dt id="g-{e(t.lower().replace(" ", "-"))}">{e(t)}</dt><dd>{e(d)} <a href="{e(h)}">Source</a></dd>' for t, d, h in terms)
    return (f'<h2>The daily run</h2><p>Once a day, around {RUN_TIME}, one routine plays every role in turn:</p><ol class="steps">{steps}</ol>'
            f'<h2>The role cycle</h2><p>Each role also researches its own area once a week, from public web pages only. {days}. '
            f'The full rotation is on <a href="{up}schedule/">Schedule and limits</a>, and who does what is on <a href="{up}team/">Team</a>.</p>'
            f'<h2>Where the human decides</h2><p>Ryno, the CEO, doesn\'t sign off routine work. He decides his own pitches, any real disagreement '
            f'(needs-ceo), any change that loosens a safety check (ceo-approved), and the direction. His decisions are marked on the '
            f'<a href="{up}timeline/">Timeline</a>.</p><h2>Glossary</h2><dl class="gloss">{gloss}</dl>')


# Comms (i28): one plain, page-true description per page. Pages not listed fall back to their lede.
DESCRIPTIONS = {
    "": "An unofficial Grok Bot tracker built, designed, and run by Grok Bots, with every claim linked to a public source or a merged change.",
    "roadmap/": "The Slopworks team's roadmap as a quest board: what shipped, what's in progress and next, what was dropped, and the dated calls it kept or broke.",
    "metrics/": "Slopworks metrics from its records: merged PRs, open-to-merge time, sprint durations, CI catches, failures on main, reverts, AARs, and trends by day.",
    "weekly/": "A weekly recap of the Slopworks bot team from its records: merged PRs, sprints, research, lessons, and next objectives. A running week is labeled so far.",
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
    "team/xp/": "How the Slopworks bot roles earn XP and levels: only from verified work, each point linked to its evidence and reviewed by another role.",
    "work/": "What the Slopworks bot team has made and how it went: the timeline, case files, a research round, and a labeled demo.",
    "hood/": "How Slopworks runs: the Grok Bot tracker, the bots' own chat, the schedule and limits, and the run and design logs.",
    "how/": "How the Slopworks bot team works, in plain words: the daily run, the weekly role cycle, where Ryno (the human CEO) decides, and a glossary.",
    "schedule/": "When Slopworks runs, what each run does, and the limits the bot team works within.",
    "calendar/": "The Slopworks team calendar: this month and the next two, with runs, reviews, releases and holiday character themes, plus a subscribe feed.",
}


def describe(slug, lede):
    if slug in DESCRIPTIONS:
        return DESCRIPTIONS[slug]
    text = re.sub(r"<[^>]+>", "", lede).replace("&#x27;", "'").replace("&amp;", "&")
    return text if len(text) <= 160 else text[:157].rsplit(" ", 1)[0] + "\u2026"


def page_url(slug):
    return BASE + slug


# Breezy navigation (Ryno, 2026-10-19 3:45 PM ET; visual review V9): every main page ends with one next step in reading order.
ORDER = [("", "Home"), ("work/", "Work")] + WORK + [("team/", "Team"), ("team/xp/", "How XP works"), ("lessons/", "Lessons"), ("hood/", "Under the hood")] + HOOD


def next_link(slug, up, body):
    """'Next: <page>' at the end of a page in ORDER; the last page leads back home. Pages with their own next step keep it."""
    slugs = [s for s, _ in ORDER]
    if slug not in slugs or slug == "" or 'class="next"' in body:
        return ""
    s, t = ORDER[(slugs.index(slug) + 1) % len(ORDER)]
    return f'<p class="next"><a class="more" href="{up}{s}">Next: {e(t)}</a></p>'


def page(slug, title, lede, body, source, h1=None, kind=None):
    up = "../" * slug.count("/")
    desc, url, full = describe(slug, lede), page_url(slug), f"{title} · Slopworks"
    # Structured data as schema.org microdata, not JSON-LD: check.py bans every <script> tag, and that guardrail stays.
    kind = kind or ("WebSite" if slug == "" else ("CollectionPage" if slug in ("updates/", "issues/", "cases/", "lessons/", "chat/") or slug.startswith("chat/archive/") else "WebPage"))
    micro = (f'<meta itemprop="name" content="{e("Slopworks" if slug == "" else full)}"><meta itemprop="description" content="{e(desc)}"><link itemprop="url" href="{e(url)}">'
             + ('<span hidden itemprop="publisher" itemscope itemtype="https://schema.org/Organization"><meta itemprop="name" content="Slopworks">'
                f'<link itemprop="url" href="{BASE}"><link itemprop="sameAs" href="{REPO}"></span>' if slug == "" else
                f'<span hidden itemprop="isPartOf" itemscope itemtype="https://schema.org/WebSite"><meta itemprop="name" content="Slopworks"><link itemprop="url" href="{BASE}"></span>'))
    here = section(slug)[0]
    cur = lambda s: ' aria-current="page"' if s == slug else (' aria-current="true"' if s == here else "")
    nav = "".join(f'<li><a href="{up}{s}"{cur(s)}>{e(t)}</a></li>' for s, t in TOP)
    # Footer (hotfix after the 2026-10-17 /work/ incident, Comms and Polish): the 5 sections, not every page.
    sitemap = (f'<nav class="sitelist" aria-label="Sections"><ul><li><a href="{up}">Home</a></li>'
               + "".join(f'<li><a href="{up}{s}">{e(t)}</a></li>' for s, t in TOP) + "</ul></nav>")
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
<link rel="icon" href="{up}assets/favicon.svg" type="image/svg+xml">
<meta name="theme-color" content="#F6F5F1" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#141418" media="(prefers-color-scheme: dark)">
<link rel="stylesheet" href="{up}style.css">
<link rel="alternate" type="application/rss+xml" title="Slopworks" href="{up}feed.xml">
<link rel="alternate" type="application/feed+json" title="Slopworks" href="{up}feed.json">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header><div class="wrap">
<a class="brand" href="{up}"{' aria-current="page"' if slug == "" else ""}><img src="{up}assets/favicon.svg" alt="" width="28" height="28">Slopworks</a>
<label class="tf"><input type="checkbox" id="theme-flip"><span class="tf-d"><span class="vh">Switch to </span>Dark<span class="vh"> theme</span></span><span class="tf-l"><span class="vh">Switch to </span>Light<span class="vh"> theme</span></span></label>
<nav aria-label="Main"><ul>{nav}</ul></nav>
</div></header>
<main id="main" class="wrap{" home" if slug == "" else ""}" itemscope itemtype="https://schema.org/{kind}">{micro}
{back_link(slug, up)}<p class="disclaimer">{e(DISCLAIMER)}</p>
<h1>{h1 or e(title)}</h1>
<p class="lede">{lede}</p>
{trim_legend(body)}{next_link(slug, up, body)}
</main>
<footer><div class="wrap">
{sitemap}
<p>{e(CREDIT)}</p>
<p class="links"><a href="mailto:{CORRECTIONS}">Corrections</a> <a href="{up}feed.xml">RSS</a> <a href="{REPO}/blob/main/docs/follow.md">Follow</a> <a href="{REPO}">Source</a> <a href="{REPO}/commits/main/{source}">Page history</a></p>
</div></footer>
</body>
</html>
"""


def item_slug(x, issue=False):
    """Item pages (#149 §2.1) live at updates/<id>/ and issues/<id>/: the record id never changes, so a corrected title
    can't break a published URL."""
    return f'{"issues" if issue else "updates"}/{x["id"]}/'


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
            f'<a href="{e(x["source"])}">source</a><a href="{e(x["id"])}/" aria-label="Details on {e(x["title"])}">details</a><span>added {x["added"]} by {e(x["added_by"])}</span></p></article>')


def item_modified(x, issue=False):
    """Newest date the record itself carries: added, or the fix date for a fixed issue."""
    return max(d for d in (x["added"], x.get("fixed_date") if issue else None) if d)


def item_page(x, issue, related):
    """One page per update or issue (#149 §2.1): the record, where it came from, who added it, and 3 more in its area.
    Every line comes from the record; nothing is inferred. h1 uses short_title (8-word page_title limit) when set."""
    day = lambda d: datetime.fromisoformat(d).strftime("%b %-d, %Y")
    what = "issue" if issue else "update"
    lede = f'{x["status"].capitalize()} Grok Bot {what} · {e(x["area"])} · {day(x["date"])}'
    facts = ""
    if issue:
        facts += f'<p><strong>State:</strong> {e(x["state"])}' + (f' since {day(x["fixed_date"])}' if x.get("fixed_date") else "") + "</p>"
        if x.get("workaround"):
            facts += f'<p><strong>Workaround:</strong> {e(x["workaround"])}</p>'
        if x.get("fixed_source"):
            facts += f'<p class="meta"><a href="{e(x["fixed_source"])}">Source for the fix</a></p>'
    if x.get("corrected"):
        facts += f'<p><strong>Corrected:</strong> {e(x["corrected"])}</p>'
    meaning = ("Confirmed means it comes from an official account or the docs." if x["status"] == "confirmed"
               else "Reported means a community post, not yet confirmed by an official account or the docs.")
    more = "".join(f'<li><a href="../{e(r["id"])}/">{e(r["title"])}</a></li>' for r in related)
    body = (f'<meta itemprop="headline" content="{e(x["title"])}"><meta itemprop="datePublished" content="{x["date"]}">'
            f'<meta itemprop="dateModified" content="{item_modified(x, issue)}">'
            f'<p>{e(x["summary"])}</p>{facts}'
            f'<h2>Where this comes from</h2><p><a itemprop="isBasedOn" href="{e(x["source"])}">The public source</a>, dated {day(x["date"])}. {meaning}</p>'
            f'<p>Added {day(x["added"])} by {e(x["added_by"])}. <a href="../../how/">How the team checks entries</a></p>'
            + (f'<h2>More in {e(x["area"])}</h2><ul>{more}</ul>' if more else "")
            + f'<p class="next"><a class="more" href="../">All {"known issues" if issue else "updates"}</a></p>')
    return page(item_slug(x, issue), x["title"], lede, body, f'data/{"issues" if issue else "updates"}.json',
                h1=e(x.get("short_title") or x["title"]), kind="Article")


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


def xp_totals(entries):
    """XP per role (i34): the sum of approved entries only, base XP times the quality percent. Never stored, always computed."""
    tot = {}
    for x in entries:
        if x["status"] == "approved":
            tot[x["agent"]] = tot.get(x["agent"], 0) + x["base_xp"] * x["quality_pct"] // 100
    return tot


def level_for(xp, levels):
    """(number, level, next level or None) for an XP total, from the thresholds in data/progression.json."""
    i = max(k for k, lv in enumerate(levels) if lv["xp"] <= xp)
    return i + 1, levels[i], levels[i + 1] if i + 1 < len(levels) else None


def rollover(units, size, target, keep=1, hard=None):
    """Archive rollover shared by Timeline and Lessons, in the Team chat pattern. units: newest first, each (date, ...).
    The newest units stay on the main page while they fit the byte target; older ones go to month parts
    (YYYY-MM, then YYYY-MM-2 ...), filled oldest first so an item's archive page stays put as new items roll in.
    keep (i42): the newest `keep` units stay even past the target, as long as they fit `hard` bytes, so a new day
    doesn't leave the main page with one thin day."""
    main, rest, used = [], [], 0
    for u in units:
        if not rest and (not main or used + size(u) <= target or (len(main) < keep and hard and used + size(u) <= hard)):
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
    files["updates/index.html"] = page("updates/", "What's new in Grok Bot", f"{len(ups)} Grok Bot updates from public posts, newest first. Each links its source and is marked <strong>confirmed</strong> (official account or docs) or <strong>reported</strong> (community post).",
                               (lambda f: f[1] + '<div class="filtered">' + f[0] + '<h2 id="all">Updates, newest first</h2>' + "".join(entry_card(x) for x in ups) + "</div>")(area_filter(ups)) if ups else '<p class="empty">Nothing yet.</p>', "data/updates.json")

    # Tracker counts for home (i22's proof line, kept on home's tracker panel in i41).
    ideas_all = load("ideas")
    dropped = sum(r["counts"].get("dropped_verify", 0) for r in runs)
    screened = sum(r["counts"].get("candidates", 0) for r in runs)
    # Home moved below the Timeline (mission i41): it reuses the Timeline records, so it's built after them.
    areas = sorted({x["area"] for x in iss})
    body = ""
    for a in areas:
        body += f'<section data-area="{e(a)}"><h2>{e(a.capitalize())}</h2>' + "".join(entry_card(x, True) for x in iss if x["area"] == a) + "</section>"
    if body:
        fl, st = area_filter(iss)
        body = st + '<div class="filtered">' + fl + body + "</div>"
    # Item pages (#149 §2.1): one per update and issue, with 3 newer-first neighbours from the same area.
    for items, issue in ((ups, False), (iss, True)):
        for x in items:
            near = [r for r in sorted(items, key=lambda r: (r["date"], r["id"]), reverse=True) if r["area"] == x["area"] and r is not x][:3]
            DESCRIPTIONS[item_slug(x, issue)] = describe(None, x["summary"])  # raw: page() escapes it once
            files[item_slug(x, issue) + "index.html"] = item_page(x, issue, near)
    files["issues/index.html"] = page("issues/", "Known issues", f"{sum(x['state']=='open' for x in iss)} open, {sum(x['state']=='fixed' for x in iss)} fixed. Grouped by area. Marked fixed only when a public source says so.", body or f'<p class="empty">No known issues right now. Issues land here when a public source reports one; the daily run checks around {RUN_TIME}.</p>', "data/issues.json")

    body = ""
    for r in runs:
        counts = "".join(f"<tr><th scope=\"row\">{e(k.replace('_', ' '))}</th><td>{v}</td></tr>" for k, v in r["counts"].items())
        notes = "".join(f"<li>{e(n)}</li>" for n in r.get("notes", []))
        body += (f'<article class="card" id="run-{e(r["id"])}"><h3>{e(r["date"])} · {e(r["kind"])} run · {e(r["status"])}</h3>'
                 f'<div class="scroll"><table class="stack"><tbody>{counts}<tr><th scope="row">X reads</th><td>{r.get("x_reads", 0)}</td></tr></tbody></table></div><ul>{notes}</ul></article>')
    files["behind/index.html"] = page("behind/", "Behind the scenes", f"What each role found, dropped, or stripped in every run. Auto-merge is <strong>{e(state['auto_merge'])}</strong>. These are roles played in one daily routine, not separate live bots.", ('<h2 id="runs">Runs, newest first</h2>' + body) if body else body, "data/runs.json")

    # ---------- Team chat with automatic archive rollover ----------
    # The main page keeps the newest threads, notes, and ideas inside a byte target (well under the page-weight budget);
    # everything older moves to dated archive pages (chat/archive/YYYY-MM.html, then -2, -3 when a month is big). Nothing is dropped.
    # Case-file steps link ../chat/#id literally (and CI checks that anchor), so those items and open ideas stay pinned on the main page.
    # Every other link (team cards, arena, demo challenge, feeds, badges) goes through href(), which points at wherever the item lives now.
    budget = json.loads((ROOT / "scripts/patterns.json").read_text())["max_page_bytes"]
    css_bytes = (SITE / "style.css").stat().st_size  # the stylesheet these pages load; site/sheets.css loads on the sheets only
    page_target = int(budget * CHAT_TARGET) - css_bytes
    ideas = sorted(load("ideas"), key=lambda i: i["date"], reverse=True)
    idea_state = {i["id"]: i["state"] for i in ideas}
    research = sorted(load("research"), key=lambda r: r["date"], reverse=True)
    is_demo = lambda r: r["question"].startswith("Demo challenge")
    SPEAKS_AS = {"Sketch": {"Sketch", "Scout"}, "Lens": {"Lens", "Verify"}, "Forge": {"Forge", "Pixel", "Core", "Publish"}, "Shield": {"Shield", "Privacy"}}
    def latest_of(n):
        return next((c for c in reversed(chat) if c["from"] in SPEAKS_AS.get(n, {n})), None)
    pinned = {s["link"].split("#", 1)[1] for c in load("cases") for s in c["steps"] if s.get("link", "").startswith("../chat/#")}
    pinned |= {i["id"] for i in ideas if i["state"] in OPEN_IDEAS - {"yes"}}  # pitches still waiting on a decision; decided ones roll by date like everything else
    loc = {r["id"]: "challenges/" for r in research if is_demo(r)}
    def href(i, up, here):
        where = loc.get(i, "chat/")
        return f"#{e(i)}" if where == here else f"{up}{where}#{e(i)}"

    by_id = {c["id"]: c for c in chat}

    def msg(c, up, here, cls="msg"):
        ref = f' <a href="{e(c["ref"])}">ref</a>' if c.get("ref") else ""
        when = f'{c["date"]} {c["time"]} ET' if c.get("time") else c["date"]
        badge = ""
        parent = by_id.get(c.get("reply_to"), {})
        if c.get("idea") in idea_state and parent.get("idea") != c["idea"]:  # badge once per thread, not on every reply (Critic, c212)
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
        if today else f"<h2 id=standup>Standup</h2><p class=empty>No standup yet today. The daily run (around {RUN_TIME}) opens with one line per role that has something new.</p>")
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
    fl = '<p>Follow Team chat: <a href="../chat.xml">RSS</a>, <a href="../chat.json">JSON</a>. </p><details class="routine"><summary>Follow it with your own Grok Bot</summary><p>Paste this into a routine:</p><blockquote class="card"><p>Every morning, read https://slopryno.com/chat.json and tell me about new pitches, decisions, and any debate between the Slopworks bots since yesterday: who pitched what, who pushed back, and what Coordinator decided and why. Stay quiet if nothing\'s new.</p></blockquote></details>'
    fl = '<nav class="jump" aria-label="On this page"><a href="#standup">Standup</a><a href="#ideas">Ideas</a><a href="#research">Research</a><a href="#handoffs">Handoffs</a>' + ('<a href="#archive">Archive</a>' if parts else "") + '</nav>' + fl
    files["chat/index.html"] = page("chat/", "Team chat", "The real handoffs between roles, newest first. Nothing is staged, and it never quotes readers or names anyone outside the team.", fl + sbody + msec + arch_list, "data/chat.json")
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
    import home
    objectives = {o["role"]: o for o in load("objectives")}  # i42: one current objective per role, each from a real record
    alumni = load("alumni")
    alumni_html = ("<h2 class=\"group\">Alumni</h2><ul>" + "".join(f'<li><a href="{REPO}/blob/main/bots/alumni/{e(a["role"].lower())}.md">{e(a["role"])}</a>: retired {a["date"]}. {e(a["reason"])} Work handed to {e(a["successor"])}.</li>' for a in alumni) + "</ul>") if alumni else ""
    research = sorted(load("research"), key=lambda r: r["date"], reverse=True)
    rot = {r["role"]: (d["day"], r["focus"]) for d in sched.get("research", []) for r in d["roles"]}
    TEAM_ROLE = {"Sketch": "Scout", "Lens": "Verify"}
    # Living Team (i22, PR 5 of 8): each card shows the role's latest real handoff from data/chat.json, with its date. No live claims.
    def latest_msg(n, up="../", here="team/"):
        m = latest_of(n)
        if not m:
            return '<p class="empty">No handoffs yet. They appear here after the role posts in Team chat.</p>'
        txt = m["text"] if len(m["text"]) <= 140 else m["text"][:137].rsplit(" ", 1)[0] + "\u2026"
        return (f'<blockquote class="latest"><p>{e(txt)}</p><p class="meta">{as_of(m["date"], "said on")}<span>to {e(m["to"])}</span>'
                f'{"<span>as " + e(m["from"]) + "</span>" if m["from"] != n else ""}<a href="{href(m["id"], up, here)}">in Team chat</a></p></blockquote>')
    # Role skills (Ryno, 2026-10-19 10:06 PM ET): parsed from each role file's **Skills:** block; scripts/skills.py checks them.
    import skills as skillmod
    kit = skillmod.load()
    learned = lambda f: skillmod.role_skills((ROOT / "bots" / f).read_text()) or []
    def trained_when(got):  # per-source trained dates, e.g. "Oct 15 and 21, 2026"
        days = sorted({datetime.fromisoformat(kit["sources"][src].get("trained", kit["trained"])) for _, _, src, _ in got}) or [datetime.fromisoformat(kit["trained"])]
        return " and ".join(d.strftime("%b %-d") if i == 0 or d.month != days[0].month else d.strftime("%-d") for i, d in enumerate(days)) + f", {days[-1].year}"
    # Training tracks (Ryno, 2026-10-20 7:05 AM ET): a role's **Training track:** lines name tracks in data/skills.json.
    tracked = lambda f: [(tid, kit["tracks"][tid]) for tid in skillmod.role_tracks((ROOT / "bots" / f).read_text()) if tid in kit.get("tracks", {})]
    # Character sheets (i34, Week 1): every number is computed here from data/xp_ledger.json and data/progression.json.
    prog, ledger_all = load("progression"), load("xp_ledger")
    totals, levels = xp_totals(ledger_all), prog["levels"]
    stems = {n: f[:-3] for n, _, _, _, f in team()}
    def xp_line(n, up):
        x = totals.get(n, 0)
        num, lv, nxt = level_for(x, levels)
        return f'Level {num}, {e(lv["name"])}, {x} XP'
    order = [x[0] for x in team()]
    def sheet(n, t, r, o, f):
        x = totals.get(n, 0)
        num, lv, nxt = level_for(x, levels)
        mine = [y for y in ledger_all if y["agent"] == n]
        ok = [y for y in mine if y["status"] == "approved"]
        pct = 100 if not nxt else int(100 * (x - lv["xp"]) / (nxt["xp"] - lv["xp"]))
        skipped = {s: sum(y["status"] == s for y in mine) for s in ("rejected", "pending", "reversed")}
        notes = sorted({y.get("note", "") for y in mine if y["status"] != "approved"} - {""})
        kinds = {}
        for y in ok:
            k = kinds.setdefault(y["type"], [0, 0]); k[0] += 1; k[1] += y["base_xp"] * y["quality_pct"] // 100
        quest = prog["quests"].get(n, prog["quests"]["default"])
        newest = sorted(ok, key=lambda y: y["timestamp"], reverse=True)
        # The role's 3 latest merged PRs always show (they moved here from the Team page), even when sign-offs fill the newest 15.
        shipped = [y for y in newest if y["type"] == "pr_merged"][:3]
        shown = newest[:15] + [y for y in shipped if y not in newest[:15]]
        extra = len(shown) - 15
        plus = f", plus {extra} older merged {'PR' if extra == 1 else 'PRs'}" if extra > 0 else ""
        # The card back (Ryno, Oct 20 3:06 PM ET: "Go with B, the card back"): scripts/sheets.py renders, site/sheets.css styles.
        r = cspec["roles"][n]
        ty = next(z for z in cspec["types"] if z["name"] == r["type"])
        art = r.get("art", {}).get(season)
        rk, rname = cardmod.rarity(num, cspec)
        cant = re.search(r"\*\*Can't:\*\*\s*(.+)", (ROOT / "bots" / f).read_text())
        tracks = []
        for tid, tt in tracked(f):
            rn = next(z for z in tt["roles"] if z.lower() == f[:-3])
            xx, mods, src = tt["exercises"][rn], skillmod.track_modules(tt, rn), tt["sources"]
            g = xx["grade"]
            tracks.append(dict(id=tid, title=tt["title"], mods=mods, grade=g, findings=xx["findings"], width=xx["width"], pages=xx["pages"],
                grade_text={"pending": f'Grade pending from {g["by"]}', "pass": f'Passed, graded by {g["by"]}', "redo": f'Redo asked by {g["by"]}'}[g["state"]],
                day=datetime.fromisoformat(xx["date"]).strftime("%b %-d"),
                mods_html="".join(f'<li><strong>{e(m["title"])}.</strong> {e(m["practice"])} <a href="{e(src[m["sources"][0]]["url"])}">{e(src[m["sources"][0]]["title"])}</a></li>' for m in mods),
                findings_html="".join(f'<li><strong>{ {"defect": "Defect", "risk": "Risk", "pass": "Pass"}[x2["kind"]]}:</strong> {e(x2["what"])}</li>' for x2 in xx["findings"])))
        rr = TEAM_ROLE.get(n, n)
        rday, rfocus = rot.get(rr, ("", ""))
        rlast = next((z for z in research if z["role"] == rr), None)
        in_arena = rlast and any(rlast["id"] in a["reports"] for a in load("arena"))
        i = order.index(n) + 1
        set_order = [m for _, ms in GROUPS for m in ms]
        c = dict(n=n, stem=stems[n], title=t, role=r, ty=ty, ti=[z["name"] for z in cspec["types"]].index(r["type"]), art=art,
                 pk=art["particles"] if art else ty["particles"], av=f"../../assets/avatars/{avatar_of(n)}.svg", xp=x, level=num, lvname=lv["name"], pct=pct,
                 togo=(f'{nxt["xp"] - x} XP to {e(nxt["name"])} ({nxt["xp"]} XP)' if nxt else "Top level reached"), rk=rk, rname=rname,
                 set=set_order.index(n) + 1, total=len(order), flavour=r["flavour"].get(season) or r["flavour"]["normal"],
                 counts={k: v[0] for k, v in kinds.items()}, kinds=sorted(kinds.items(), key=lambda kv: -kv[1][1]),
                 labels={k: v["label"] for k, v in prog["events"].items()}, ok=len(ok), skipped=skipped, notes="; ".join(notes),
                 quest=quest, quest_note=shmod.quest_note(prog),
                 ach=[dict(name=a["name"], rule=a["rule"], got=next((z for z in ok if z["type"] == a["event"]), None)) for a in prog["achievements"]], badges=None,
                 bio=bio(n), objective=home.objective(objectives[n], "../../", href) if n in objectives else "", owns=o, cant=cant.group(1) if cant else "",
                 latest=latest_msg(n, "../../", "team/" + f[:-3] + "/"), rolefile=f"{REPO}/blob/main/bots/{f}",
                 skills=learned(f) or [], tracks=tracks, trained=trained_when(learned(f)), skills_src=f"{REPO}/blob/main/data/skills.json",
                 rday=rday, rfocus=rfocus[:1].upper() + rfocus[1:], rlast=rlast,
                 rlast_href=(("../../arena/#" + e(rlast["id"])) if in_arena else href(rlast["id"], "../../", "team/")) if rlast else "",
                 work=[dict(y, gain=y["base_xp"] * y["quality_pct"] // 100) for y in shown], verified=label("verified"),
                 shown_line=f"Showing the newest {min(15, len(ok))} of {len(ok)}{plus}." if ok else "", ledger=f"{REPO}/blob/main/data/xp_ledger.json",
                 claimed=[s for s in load("standup") if s["role"] == n],
                 next_href=f"../{stems[order[i]]}/" if i < len(order) else "../xp/", next_text=f"Next: {order[i]}'s sheet" if i < len(order) else "Next: How XP works")
        return page(f"team/{stems[n]}/", f"{n}: character sheet", f"{e(n)}'s level, XP, achievements, and verified work, computed from the XP ledger at build time.",
                    shmod.render(c), "data/xp_ledger.json").replace("</head>", '<link rel="stylesheet" href="../../sheets.css">\n</head>', 1)
    import cards as cardmod
    import avatars as avmod
    import sheets as shmod
    cspec, season = cardmod.load(), avmod.committed_season() or "normal"
    for x in team():
        files[f"team/{stems[x[0]]}/index.html"] = sheet(*x)
    files["sheets.css"] = shmod.css(cspec, season, stems)
    ev_rows = ""
    for k, v in prog["events"].items():
        d = prog["tables"]["default"].get(k)
        extra = ", ".join(f'{r} {tb[k]}' for r, tb in prog["tables"].items() if r != "default" and k in tb)
        ev_rows += f'<tr><td>{e(v["label"])}</td><td>{d if d is not None else "-"}</td><td>{e(extra) or "-"}</td><td>{e(v["who"])}</td><td>{e(v["reviewer"])}</td></tr>'
    roster = "".join(f'<li><a href="../{stems[n]}/">{e(n)}</a>: {xp_line(n, "")}</li>' for n in sorted(stems))
    xbody = ("".join(f"<p>{e(x)}</p>" for x in re.split(r"(?<=[.)])\s+(?=[A-Z])", prog["note"])) +
             f'<h2>Levels</h2><div class="scroll fit"><table><thead><tr><th scope="col">Level</th><th scope="col">Name</th><th scope="col">XP needed</th></tr></thead><tbody>'
             + "".join(f'<tr><td>{i + 1}</td><td>{e(l["name"])}</td><td>{l["xp"]}</td></tr>' for i, l in enumerate(levels)) + "</tbody></table></div>"
             f'<h2>What earns XP</h2><div class="scroll"><table><thead><tr><th scope="col">Work</th><th scope="col">XP</th><th scope="col">Role tables</th><th scope="col">Who earns it</th><th scope="col">Reviewer</th></tr></thead><tbody>{ev_rows}</tbody></table></div>'
             f'<p>Sign-offs count at most {prog["events"]["signoff"]["cap_per_day"]} a day per role; the rest stay in the ledger as rejected, so the cap is visible.</p><p>{e(prog["quality"]["note"])}</p>'
             f'<h2>Fair play</h2><ol>' + "".join(f"<li>{e(r)}</li>" for r in prog["anti_gaming"]) + "</ol>"
             f'<h2>Entry statuses</h2><ul>' + "".join(f"<li><strong>{e(k)}:</strong> {e(v)}</li>" for k, v in prog["statuses"].items()) + "</ul>"
             f'<h2>Achievements</h2><ul>' + "".join(f'<li><strong>{e(a["name"])}:</strong> {e(a["rule"])}</li>' for a in prog["achievements"]) + "</ul>"
             f'<h2>Coming in later weeks</h2><ul><li><strong>Week 2:</strong> {e(prog["later_weeks"]["week2"])}</li><li><strong>Week 3:</strong> {e(prog["later_weeks"]["week3"])}</li><li><strong>Week 4:</strong> {e(prog["later_weeks"]["week4"])}</li></ul>'
             f'<h2>Every character sheet</h2><p class="meta">In name order. Levels describe each role\'s own record.</p><ul>{roster}</ul>'
             f'<p>Rules: <a href="{REPO}/blob/main/data/progression.json">data/progression.json</a> (owned by Game Master). Ledger: <a href="{REPO}/blob/main/data/xp_ledger.json">data/xp_ledger.json</a>, written by <a href="{REPO}/blob/main/scripts/xp.py">scripts/xp.py</a>. Decided in <a href="{href(prog["thread"], "../../", "team/xp/")}">Team chat</a>.</p>')
    files["team/xp/index.html"] = page("team/xp/", "How XP works", f"XP from {len([y for y in ledger_all if y['status'] == 'approved'])} verified pieces of work. Every point links its evidence.", xbody, "data/progression.json")
    # Team trading cards (Ryno, Oct 20 12:18 PM ET: design locked; Comms wording). scripts/cards.py renders; no script.
    def tslot(x, i):
        n, f = x[0], x[4]
        xp = totals.get(n, 0)
        num, lv, nxt = level_for(xp, levels)
        kinds = {}
        for y in ledger_all:
            if y["agent"] == n and y["status"] == "approved":
                kinds[y["type"]] = kinds.get(y["type"], 0) + 1
        return cardmod.card(n, i, len(order), f[:-3], cspec, season, xp, num, lv, nxt, kinds, f"../assets/avatars/{avatar_of(n)}.svg", jb=avmod.card_badge(avatar_of(n), season))
    by_name = {x[0]: x for x in team()}
    seq = [by_name[n] for _, members in GROUPS for n in members if n in by_name]  # set order = the group order
    tiers = {}
    for x in seq:
        k = cardmod.rarity(level_for(totals.get(x[0], 0), levels)[0], cspec)[1]
        tiers[k] = tiers.get(k, 0) + 1
    summ = ", ".join(f"{tiers[r['name']]} {r['name'].lower()}" for r in reversed(cspec["rarity"]) if r["name"] in tiers)
    tbody = (f'<p class="set">Set 1, {len(seq)} cards: {summ}.' + (" October edition: Halloween art." if season == "halloween" else "") + " Tap a card to open it.</p>"
             
             + "".join(f'<h2 class="group">{e(g)}</h2><div class="deck">' + "".join(tslot(x, seq.index(x) + 1) for x in seq if x[0] in members) + "</div>" for g, members in GROUPS))
    # Ryno's CEO card and sheet (scripts/ceo.py; Ryno, Oct 20 3:54 PM ET): a CEO group above Leadership, his avatar the same all year.
    import ceo
    g0 = tbody.index('<h2 class="group">')
    tbody = (tbody[:g0].replace(" Tap a card to open it.</p>", " Plus one human: Ryno, the CEO. Tap a card to open it.</p>", 1)
             + f'<h2 class="group">CEO</h2><div class="deck">{ceo.card(cardmod, cspec, season, len(seq), "../assets/avatars/ceo.svg")}</div>' + tbody[g0:])
    first = seq[0][0]
    files[f"team/{ceo.STEM}/index.html"] = page(f"team/{ceo.STEM}/", "Ryno: character sheet", "The human CEO: his real powers and every time he used them, counted from the records at build time.",
                                                ceo.sheet(REPO, len(seq), f'<p class="next"><a class="more" href="../{stems[first]}/">Next: {e(first)}\'s sheet</a></p>'), "data/ceo_decisions.json").replace("</head>", f'<link rel="stylesheet" href="../../sheets.css">\n<style>{ceo.sheet_css(season)}</style>\n</head>', 1)
    files["team/index.html"] = page("team/", "The team", f"{len(team())} Grok Bot roles in five groups, played by one daily routine, not separate agents. Levels come from verified XP (<a href=\"xp/\">how XP works</a>).",
                                    tbody + alumni_html + '<p class="next"><a class="more" href="../timeline/">Next: how the team grew, on the Timeline</a></p>', "bots").replace("</head>", f"<style>{cardmod.css(cspec, season, stems)}{ceo.css(season)}</style>\n</head>", 1)


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
        lead, sents = [], re.split(r"(?<=[.)])\s+(?=[A-Z#])", a["change"]["text"])
        for x in sents:  # visual review V5: what changed, in about one sentence; the whole review is one tap away
            if lead and len(" ".join(lead + [x]).split()) > 20:
                break
            lead.append(x)
        return (f'<article class="card aar" id="{e(a["id"])}"><h2>{e(a["title"])}</h2><p class="meta">{as_of(a["date"], "happened")}<span class="tag">{e(TRIGGERS[a["trigger"]])}</span>'
                f'<span class="tag">{st}</span></p><p><strong>What we change:</strong> {e(" ".join(lead))}</p>'
                f'<details><summary>The full review, with receipts</summary><p class="meta"><span>owner {e(a["owner"])}</span><a href="{href(a["thread"], "../", "lessons/")}">Team chat thread</a></p><dl>{rows}</dl></details></article>')
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
        "Same-day, blameless after-action reviews: what was expected, what happened, why, and what changed. Every line links its record.",
        f'<p class="meta"><span>{len(aars)} reviews</span><span>{n_open} open</span><span>newest first</span></p>'
        + ("".join(aar(u[1]) for u in l_main) or '<p class="empty">No after-action reviews yet. One appears here the same day something goes wrong.</p>') + "<p>The Friday retro reviews the week's reviews and closes them, and Advisor turns repeats into rules or CI checks.</p>" + l_arch, "data/aars.json")
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
    files["arena/index.html"] = page("arena/", "Research Arena", "A real research round: independent reports, a challenge, a score, and a decision. Every claim links its source.",
                                     abody or '<p class="empty">No research rounds yet. A round appears here when the team researches a question together.</p>', "data/arena.json")

    # Case files (i22, PR 3 of 8): real decisions replayed step by step. Links go to merged PRs, chat, and research only.
    def case_card(c):
        st = "".join(f'<li>{avatar(x["role"], "../", 28)}<div><p>{label(x["label"])} <strong class="who" style="--c:{color(x["role"])}">{e(x["role"])}</strong></p><p>{e(x["text"])} <a href="{e(x["link"])}">{"PR #" + x["link"].rsplit("/", 1)[1] if "/pull/" in x["link"] else "record"}</a></p></div></li>' for x in c["steps"])
        return (f'<article class="card case" id="{e(c["id"])}"><h2>{e(c["title"])}</h2><p class="meta">{as_of(c["date"], "shipped")}<span>real work, not a demo</span></p>'
                f'<p>{e(c["summary"])}</p><p><strong>Outcome:</strong> {e(c["outcome"])} <a href="{REPO}/pull/{c["pr"]}">PR #{c["pr"]}</a></p>'
                f'<details><summary>How it happened, in {len(c["steps"])} steps</summary><p><strong>What it shows:</strong> {e(c["shows"])}</p><ol class="trace">{st}</ol></details></article>')
    cases = load("cases")
    files["cases/index.html"] = page("cases/", "Case files", "Real decisions, replayed from the problem to what shipped. Every step links its record.",
                                     legend() + ("".join(map(case_card, cases)) or '<p class="empty">No case files yet. A case file is added after a decision ships.</p>') + '<p>Want to see how a decision gets made before anything ships? Visit the <a href="../arena/">Research Arena</a>.</p>', "data/cases.json")

    # Demo challenges (i22, PR 7 of 8): worked examples on fictional briefs, labeled Demo everywhere. Not advice, quotes, or client work.
    DEMO_NOTE = "A worked example on a fictional brief: not advice, not a quote, and not client work."
    def challenge(c):
        secs = "".join(f'<details class="sec"><summary>{e(s["name"])}</summary><ul class="outcome">' + "".join(
            f'<li>{label({"Problem definition": "demo", "Expected benefits": "hypothesis"}.get(s["name"], "recommendation"))} {e(x["text"])} <span class="meta">{e(x["role"])} · <a href="#{e(x["research"])}">report</a></span></li>' for x in s["items"]) + "</ul></details>" for s in c["sections"])
        reps = [rmap[x] for x in sorted({x["research"] for s in c["sections"] for x in s["items"]}) if x in rmap]
        srcs = sorted({u for rr in reps for u in rr["evidence"]})
        return (f'<article class="card challenge" id="{e(c["id"])}"><p class="demo-banner">{label("demo")} {e(DEMO_NOTE)}</p><h2>{e(c["title"])}</h2>'
                f'<p class="meta">{as_of(c["date"], "researched")}<span>{len(c["roles"])} roles</span><span>{len(srcs)} public sources</span></p>'
                f'<details class="brief"><summary>The brief (fictional)</summary><p>{e(c["brief"])}</p></details>{secs}'
                f'<details><summary>The {len(reps)} research reports</summary><p class="meta">By {e(", ".join(c["roles"]))}.</p>' + "".join(f'<details class="report"><summary>{e(rr["role"])}: {e(rr["question"])}</summary><div class="report-body">{rnote(rr)}</div></details>' for rr in reps) + "</details>"
                f'<details><summary>The {len(srcs)} sources</summary><ul class="meta">' + "".join(f'<li><a href="{e(u)}">{e(u)}</a></li>' for u in srcs) + "</ul></details>"
                f'<details><summary>How it was run</summary><p><a href="{href(c["thread"], "../", "challenges/")}">Team chat thread</a> · <a href="{REPO}/pull/{c["pr"]}">research PR #{c["pr"]}</a></p></details></article>')
    chs = load("challenges")
    files["challenges/index.html"] = page("challenges/", "Demo challenge", "A labeled demo: a fictional brief goes in, roles research it, a critic challenges it, and a structured outcome comes back.",
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
        elif "cap" not in (i["problem"] + " " + (i.get("reason") or "")).lower():  # a shipped decision, not a sprint: only the PRs it names
            group = [by_num[int(n)] for n in re.findall(r"#(\d+)", i.get("shipped") or "") if int(n) in by_num and f"pr{n}" not in used_prs]
        else:  # a sprint still running: every PR merged since Ryno's decision
            start = f'{i.get("decided", i["date"])}T{said_at(i) or "00:00"}'
            group = [w for w in prs if w["id"] not in used_prs and (w.get("merged") or "")[:16] >= start]
        if not group:
            continue
        used_prs |= {w["id"] for w in group}
        last = group[-1]
        items.append({"types": ["shipped"] + (["milestone"] if i["state"] == "shipped" else []), "date": last["merged"][:10], "time": last["merged"][11:16],
                      "id": f"tl-sprint-{i['id']}", "who": None, "title": i["problem"], "short": i.get("short_title"), "sprint": i["id"],
                      "capped": "cap" in (i["problem"] + " " + (i.get("reason") or "")).lower(),
                      "text": out["text"] if out else (i.get("shipped") if i["state"] == "shipped" else "In progress."), "link": lambda up, c=(out or ms[0]): href(c["id"], up, "timeline/"),
                      "cue": "retro" if out else ("thread" if i["state"] == "shipped" else "kickoff"), "children": [pr_item(w) for w in reversed(group)]})
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
        tag = "Sprint" if x.get("capped") else TL_NAMES[x["types"][0]]
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
    tl_main, tl_parts = rollover(days, lambda dd: len(day_html(dd, "../").encode()), TL_TARGET, keep=2, hard=budget - css_bytes - 12000)
    # Where each Timeline record lives now (i42): home links a sprint on whichever page holds it.
    tl_where = {x["id"]: "timeline/" for _, xs in tl_main for x in xs}
    tl_where.update({x["id"]: f"timeline/archive/{key}.html" for key, _, _, us in tl_parts for _, xs in us for x in xs})
    present = [(k, t) for k, t in TL_TYPES if any(k in x["types"] for x in items)]
    n_pr = len(prs)
    n_sprint = sum(1 for x in items if x.get("capped"))  # a shipped decision grouped with its PRs isn't a sprint
    launch = prs[0]["date"] if prs else None
    hero = (f'<p class="meta">{label("verified")} counted from the repo when this page was built</p><ul class="proof tl-proof">'
            + "".join(f"<li><strong>{v}</strong> <span>{e(l)}</span></li>" for v, l in ((n_pr, "merged PRs"), (n_sprint, "sprints"), (sum("decision" in x["types"] for x in items), "CEO decisions"), (len(aars), "lessons written up"), (len(team()), "roles"))) + "</ul>")
    def arch_name(m, n):
        y, mo = m.split("-")
        return f"{MON[int(mo) - 1]} {y}" + (f", part {n}" if n > 1 or any(p[1] == m and p[2] == 2 for p in tl_parts) else "")
    tl_arch = ('<h2 id="archive">Archive</h2><p>Older days move to archive pages automatically, so this page stays light. Nothing is removed.</p><ul>'
               + "".join(f'<li><a href="archive/{k}.html">{arch_name(m, n)}</a>: {len(us)} {"day" if len(us) == 1 else "days"}</li>' for k, m, n, us in reversed(tl_parts)) + "</ul>") if tl_parts else ""
    fhtml, fcss = type_filter(present)
    intro = ("How the team got here, newest first: what shipped, what Ryno decided, who joined, and what it researched and learned."
             " Every line links its record.")
    files["timeline/index.html"] = page("timeline/", "Timeline", e(intro) + (f" Launched {e(day_name(launch))}." if launch else ""),
        hero + fcss + '<div class="filtered">' + fhtml + "".join(day_html(dd, "../") for dd in tl_main) + "</div>" + tl_arch + legend(), "data")
    for k, (key, m, n, us) in enumerate(tl_parts):
        slug = f"timeline/archive/{key}.html"
        nav_l = ['<a href="../">Timeline (latest)</a>'] + [f'<a href="{p[0]}.html">{"Newer" if j > k else "Older"}: {arch_name(p[1], p[2])}</a>' for j, p in enumerate(tl_parts) if abs(j - k) == 1]
        files[slug] = page(slug, f"Timeline archive: {arch_name(m, n)}", "Older days from the Slopworks timeline, moved here automatically to keep the main page light. The same records, unchanged.",
            f'<nav class="jump" aria-label="Archive pages">{"".join(nav_l)}</nav>' + fcss + '<div class="filtered">' + fhtml + "".join(day_html(dd, "../../") for dd in sorted(us, reverse=True)) + "</div>", "data")

    # Metrics and trends (i45, Analyst's definitions, c328 to c335): generated from records into data/metrics.json.
    import metrics
    files["metrics/index.html"] = page("metrics/", "Metrics", "How fast the team ships, and how often something slips past review. Every number links its record.",
                                       metrics.render(load("metrics")), "data/metrics.json")
    # Weekly recap (i42, Analyst and Comms, c297 and c298): real records only; a running week says "so far".
    import weekly
    files["weekly/index.html"] = page("weekly/", "Weekly recap", "What happened each week, from the records: what shipped, what the team found, what it learned, and what's next. A week still running is marked so far.",
                                      weekly.render(sys.modules[__name__], items, wins, ups, iss, aars, list(objectives.values())), "data")
    # Home (mission i41; Polish UX depth 2026-10-29): latest verified, one next step, counts secondary, tracker, team, featured sprint, activity.
    files["index.html"] = page("", home.TITLE, f"{len(team())} Grok Bot roles run a real product, an unofficial Grok Bot tracker, and publish every decision behind it.",
                               home.render(sys.modules[__name__], items, wins, ups, iss, totals, levels, team(), dropped, screened, tl_where, objectives, href), "data", h1=home.HEADLINE)

    # Team calendar (Ryno, 2026-10-19 9:34 PM ET): month grids and a subscribe feed from data/calendar.json and the schedule.
    import cal
    from datetime import date as _date
    calendar = load("calendar")
    today = _date.fromisoformat(state.get("updated") or state["last_run"])
    files["calendar/index.html"] = page("calendar/", "Team calendar", f"Runs, reviews, releases and holiday themes, month by month. As of {cal.nice(today)}.",
                                        cal.render(calendar, sched, today), "data/calendar.json")
    # Quest board (the public roadmap, data/roadmap.json): the page, a board feed with one item per event, and oath due dates
    # in calendar.ics. Each lead shows the avatar, name and level from that role's character sheet.
    import roadmap
    board = load("roadmap")
    lead = lambda n: (f'<a href="../team/{stems[n]}/">{avatar(n, "../", 24)}{e(n)}</a>, {xp_line(n, "../").split(",")[0]}' if n in stems else e(n))
    files["roadmap/index.html"] = page("roadmap/", "Quest board", "The team's roadmap as a quest board: what shipped, what's next, and the oaths it kept or broke.",
                                       roadmap.render(board, today.isoformat(), lead), "data/roadmap.json").replace(
        "</head>", '<link rel="alternate" type="application/rss+xml" title="Slopworks Quest board (roadmap)" href="feed.xml">\n</head>', 1)
    events = roadmap.feed_items(board)[:50]
    rdt = lambda x: datetime.fromisoformat(x).replace(hour=12, tzinfo=timezone.utc)
    files["roadmap/feed.json"] = json.dumps({"version": "https://jsonfeed.org/version/1.1", "title": "Slopworks Quest board (roadmap)", "home_page_url": BASE + "roadmap/",
        "feed_url": BASE + "roadmap/feed.json", "description": "Each completed quest, stage change and judged oath on the Slopworks team's roadmap. " + DISCLAIMER,
        "items": [{"id": x["id"], "url": f'{BASE}roadmap/#{x["anchor"]}', "title": x["title"], "content_text": x["summary"], "date_published": rdt(x["date"]).isoformat()} for x in events]},
        indent=2, ensure_ascii=False) + "\n"
    files["roadmap/feed.xml"] = ('<?xml version="1.0" encoding="utf-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>Slopworks Quest board (roadmap)</title>'
        f'<link>{BASE}roadmap/</link><atom:link href="{BASE}roadmap/feed.xml" rel="self" type="application/rss+xml"/><description>{e(DISCLAIMER)}</description>\n'
        + "".join(f'<item><title>{e(x["title"])}</title><link>{BASE}roadmap/#{x["anchor"]}</link><guid isPermaLink="false">{x["id"]}</guid><pubDate>{format_datetime(rdt(x["date"]))}</pubDate><description>{e(x["summary"])}</description></item>\n' for x in events)
        + "</channel></rss>\n")
    files["calendar.ics"] = cal.ics(calendar, sched, today, BASE, roadmap.calendar_events(board))
    shipped = [d for d in design if d["state"] == "shipped"]
    backlog = sorted([d for d in design if d["state"] in ("backlog", "in-progress")], key=lambda d: d["rank"])
    card = lambda d: f'<article class="card"><h3>{e(d["idea"])}</h3><p>{e(d["why"])}</p><p class="meta"><span class="tag">effort {d["effort"]}</span><span>{e(d["state"])}{" " + d["shipped"] if d.get("shipped") else ""}</span></p></article>'
    # Hubs (i36): one tap from home to every section, one more to every page. Each row is a full-width link, easy to tap.
    # Phase A V8 (Ryno 2026-10-19 6:33 PM ET): one card anatomy: a kicker naming the kind of page, the title, a one-line
    # blurb, and a metric footer counted from the records (none where there is no honest count). A thin rule marks the kind.
    kinds = {"timeline/": ("Record", f"{len(wins)} merged PRs"), "weekly/": ("Record", ""), "metrics/": ("Measure", ""),
             "roadmap/": ("Plan", (lambda n: f"{n} active {'quest' if n == 1 else 'quests'}")(sum(q["group"] == "active" for q in board["quests"]))),
             "cases/": ("Proof", f"{len(cases)} case files"), "arena/": ("Research", (lambda n: f"{n} research {'round' if n == 1 else 'rounds'}")(len(load("arena")))),
             "challenges/": ("Demo", "Labeled demo"), "how/": ("Guide", ""), "updates/": ("Tracker", f"{len(ups)} updates"),
             "issues/": ("Tracker", f"{sum(x['state'] == 'open' for x in iss)} open"), "chat/": ("Record", f"{len(chat)} messages"),
             "schedule/": ("Guide", ""), "calendar/": ("Guide", (lambda n: f"{n} dates ahead")(cal.upcoming(calendar, today))), "behind/": ("Record", ""), "design/": ("Log", f"{len(shipped)} shipped")}

    blurb = {"timeline/": "What shipped, what Ryno decided and what was learned, newest first.",
             "weekly/": "Each week from the records: PRs, sprints, research and lessons.",
             "metrics/": "Merge time, CI catches, failures, reverts and AARs, from records.",
             "roadmap/": "Team quests completed, active and rumored, and the oaths we kept or broke.",
             "cases/": "Real decisions replayed step by step, from problem to shipped change.",
             "arena/": "Independent reports, a challenge, scores and the decision.",
             "challenges/": "A fictional brief, worked the way the team works.",
             "how/": "One daily run, a team of roles, and where Ryno steps in.",
             "updates/": "Grok Bot updates from public sources, confirmed or reported.",
             "issues/": "Public bug reports by area, fixed only when a source says so.",
             "chat/": "Standups, pitches and the real handoffs between roles.",
             "schedule/": "When each run happens and the limits the team works within.",
             "calendar/": "This month and the next two: runs, reviews and holiday themes.",
             "behind/": "What each role found, dropped or stripped in every run.",
             "design/": "What Polish changed and what's next, one change a week at most."}

    def hub(pages):
        def item(s, t):
            k, m = kinds.get(s, ("", ""))
            return (f'<li><a class="hc hc-{e(k.lower())}" href="../{s}">' + (f'<span class="kick">{e(k)}</span>' if k else "")
                    + f'<strong>{e(t)}</strong><span>{e(blurb.get(s, DESCRIPTIONS[s]))}</span>' + (f'<small class="mono">{e(m)}</small>' if m else "") + "</a></li>")
        return '<ul class="hub">' + "".join(item(s, t) for s, t in pages) + "</ul>"
    files["work/index.html"] = page("work/", "Work", "What the team has made, and how it went.", hub(WORK), "data/cases.json")
    files["hood/index.html"] = page("hood/", "Under the hood", "How the site runs: the tracker, the team's chat, and the logs. No forms or scripts, and the theme button sends nothing.", hub(HOOD) + pace_line(load("tempo"), "../"), "data/runs.json")
    files["how/index.html"] = page("how/", "How this works", "One daily run, a team of roles, and a human CEO who steps in only where the rules say so. Every term below links the rule or record behind it.",
                                   how_body(sched, "../"), "scripts/build.py")
    files["design/index.html"] = page("design/", "Design log", "What Polish, the design bot, changed and what's next. One small design change a week at most, each reviewed from screenshots of every page attached to its PR as a CI artifact.",
                                      "<h2>Shipped</h2>" + "".join(map(card, shipped)) + "<h2>Up next (ranked)</h2>" + "".join(map(card, backlog)), "data/design_backlog.json")

    srows = "".join(f'<tr><th scope="row">{e(i["when"])}</th><td>{e(i["what"])}</td></tr>' for i in sched["items"])
    rot_html = "<h2>Research rotation</h2><p>Each role researches its own area once a week, using public web pages only (about 5 pages max, no X reads).</p><div class=\"scroll\"><table class=\"stack\"><tbody>" + "".join(
        f'<tr><th scope="row">{e(d["day"])}</th><td>' + "<br>".join(f'<strong>{e(r["role"])}</strong>: {e(r["focus"])}' for r in d["roles"]) + "</td></tr>" for d in sched.get("research", [])) + "</tbody></table></div>"
    lim = "".join(f"<li>{e(l)}</li>" for l in sched["limits"])
    last = runs[0] if runs else None
    status = f'Last run: <strong>{e(last["date"])}</strong> ({e(last["kind"])}), status <strong>{e(last["status"])}</strong>. Next: the daily run, around {RUN_TIME}.' if last else f'<span class="empty">No runs yet. The first daily run is around {RUN_TIME}.</span>'
    files["schedule/index.html"] = page("schedule/", "Schedule and limits", "What to expect and when. Generated from the same schedule file the routines use.",
                                        f'<p class="card">{status}</p><div class="scroll"><table class="stack"><tbody>{srows}</tbody></table></div><p>When something goes wrong, the after-action review is on the <a href="../lessons/">Lessons</a> page the same day.</p><p>Dated plans, reviews and holiday themes are on the <a href="../calendar/">Calendar</a>.</p>' + rot_html + f'<h2>Limits, in plain words</h2><ul>{lim}</ul>', "data/schedule.json")

    feed = sorted([("update", x) for x in ups] + [("issue", x) for x in iss], key=lambda p: (p[1]["date"], p[1]["id"]), reverse=True)[:50]
    link = lambda k, x: BASE + item_slug(x, k == "issue")  # item pages; the GUIDs below don't change
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
    # Not-found page (#149 Level 1): GitHub Pages serves site/404.html at any depth, so <base> points its relative links at
    # the site root. Missing URLs get it with HTTP 404, which search engines don't index. check.py lists every page in the
    # sitemap, so it's there too; it isn't a section page, so it stays out of llms.txt.
    files["404.html"] = page("404.html", "Page not found", "That page isn't here. The link may be mistyped, or the page may never have existed.",
                             '<p>Every page the site has published keeps its address. Try one of these:</p><ul>'
                             + "".join(f'<li><a href="{s}">{e(t)}</a></li>' for s, t in [("", "Home"), ("updates/", "What's new in Grok Bot"), ("issues/", "Known issues"), ("work/", "The team's work"), ("team/", "The team")])
                             + f'</ul><p>Followed a broken link from this site? <a href="mailto:{CORRECTIONS}">Tell us</a> and we\'ll fix it.</p>', "scripts/build.py"
                             ).replace("<head>\n", f'<head>\n<base href="{BASE}">\n', 1).replace('<a class="skip" href="#main">', '<a class="skip" href="404.html#main">', 1)  # <base> would send #main to the home page
    # Comms (i28): sitemap, robots.txt, and llms.txt come from the same page list, so they can't drift (Atlas, c108).
    pages = sorted(k for k in files if k.endswith(".html"))
    loc = lambda k: BASE + (k[:-len("index.html")] if k.endswith("index.html") else k)
    # lastmod only where a record gives a real date (#149): item pages, and the two lists they belong to.
    lastmod = {item_slug(x, k == "issue") + "index.html": item_modified(x, k == "issue") for k, x in [("update", x) for x in ups] + [("issue", x) for x in iss]}
    lastmod.update({"updates/index.html": max((x["added"] for x in ups), default=None), "issues/index.html": max((item_modified(x, True) for x in iss), default=None)})
    files["sitemap.xml"] = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                            + "".join(f"<url><loc>{e(loc(k))}</loc>" + (f"<lastmod>{lastmod[k]}</lastmod>" if lastmod.get(k) else "") + "</url>\n" for k in pages) + "</urlset>\n")
    files["robots.txt"] = f"User-agent: *\nAllow: /\nSitemap: {BASE}sitemap.xml\n"
    main_pages = [("", "Home"), ("work/", "Work"), ("hood/", "Under the hood")] + [p for p in NAV if p[0]] + OPS + [("lessons/", "Lessons")] * ("lessons/" not in dict(NAV)) + [("team/xp/", "How XP works")]
    main_pages = list(dict.fromkeys(main_pages))  # How this works is in both NAV and OPS; list each page once (#149 Level 1)
    files["llms.txt"] = ("# Slopworks\n\n> " + DESCRIPTIONS[""] + " " + DISCLAIMER + "\n\n"
        "Slopworks tracks public Grok Bot updates and known issues, and shows how its bot team works: research rounds, decisions, case files, and after-action reviews. "
        "Every role is played by one daily routine and labeled as a role. Demo challenges are labeled Demo and are worked examples on fictional briefs, not advice or quotes. "
        "The site has no forms, scripts or analytics. Its one control, the theme button, only changes how the page looks and sends nothing.\n\n## Pages\n\n"
        + "".join(f"- [{t}]({BASE}{s}): {DESCRIPTIONS.get(s, '')}\n" for s, t in main_pages)
        + f"\n## Feeds and data\n\n- [Updates RSS]({BASE}feed.xml): Grok Bot updates and known issues\n- [Updates JSON Feed]({BASE}feed.json): the same items as JSON Feed 1.1\n"
        f"- [Team chat JSON Feed]({BASE}chat.json): standups, pitches, research, and handoffs\n"
        f"- [Quest board RSS]({BASE}roadmap/feed.xml): each completed quest, stage change and judged oath on the team's roadmap\n"
        f"- [Team calendar]({BASE}calendar.ics): the team's dated plans, reviews and holiday themes (iCalendar)\n- [Source repository]({REPO}): data in data/*.json, the generator in scripts/build.py\n"
        f"\n## Optional\n\n- [Style guide]({REPO}/blob/main/docs/style-guide.md): the voice and terms the team writes by\n")
    return files


def main():
    files = build()
    stale = []
    for rel, content in files.items():
        p = SITE / rel
        if "--check" in sys.argv:
            if not p.exists() or p.read_bytes() != content.encode():  # bytes: calendar.ics keeps its CRLF line ends
                stale.append(rel)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(content.encode())
    if stale:
        print("Site is out of date; run python3 scripts/build.py:", *stale)
        sys.exit(1)
    print(f"{'checked' if '--check' in sys.argv else 'built'} {len(files)} files")


if __name__ == "__main__":
    main()
