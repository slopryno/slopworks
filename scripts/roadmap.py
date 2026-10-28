#!/usr/bin/env python3
"""The Quest board: the team's roadmap as team quests and dated oaths (data/roadmap.json). Standard library only.

Every quest and oath links a real record, a quest only moves forward, and an oath is judged once. Game words always
travel with a plain word (WORDS), so a visitor who doesn't play games, a screen reader or a search engine still reads
a roadmap. Coordinator edits the board at Monday planning and the Friday retro; check.py runs errors() on every PR.
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Board vocabulary: key -> (game word, plain word). Gamemaster keeps it consistent with data/progression.json and Comms
# owns the wording; no game word may be a role name, so a stage never blurs who did the work.
GROUPS = {"complete": ("Completed quests", "shipped"), "active": ("Active quests", "in progress"),
          "held": ("Held quests", "paused"), "queued": ("Queued quests", "next"),
          "rumor": ("Rumors", "being explored, not committed"), "abandoned": ("Abandoned quests", "dropped, with the reason")}
STAGES = {"discovered": ("Discovered", "explored"), "challenged": ("Challenged", "challenged by the team"), "crafting": ("Crafting", "building"),
          "inspection": ("Inspection", "in review"), "complete": ("Complete", "shipped")}
VERDICTS = {"open": ("Sworn", "not yet due"), "kept": ("Kept", "hit"), "kept_late": ("Kept late", "slipped"), "broken": ("Broken", "missed"),
            "withdrawn": ("Withdrawn", "cut"), "unjudged": ("Unjudged", "can't be measured yet")}
WORDS = {"board": ("Quest board", "the team's roadmap"), "quest": ("Team quest", "roadmap item"), "oath": ("Oath", "a dated call the team made"),
         "fog": ("Fog", "open question"), "unlocks": ("Unlocks", "what this makes possible next"), "raid": ("Raid", "a big quest for several roles"),
         "camp": ("Camp duties", "upkeep")}
ACTIVE_CAP = 6  # a party can carry six: the per-sprint PR limit in data/tempo.json, used here as a focus rule
OPEN_PAST_DUE_DAYS = 7  # the Friday retro judges oaths due that week, so one missed retro is the most an oath may wait
REF = re.compile(r"^(?:i\d+|d\d+|G\d+|pr\d+|c\d+|aar-[a-z0-9-]+|file:[A-Za-z0-9_./-]+)$")


def load(name, root):
    p = root / f"data/{name}.json"
    return json.loads(p.read_text()) if p.exists() else []


def known_refs(root):
    """Every id a quest, oath, history step or camp duty may cite, from the records themselves."""
    refs = {x["id"] for x in load("ideas", root)} | {x["id"] for x in load("design_backlog", root)} | {x["id"] for x in load("wins", root)}
    refs |= {x["id"] for x in load("chat", root)} | {x["id"] for x in load("aars", root)}
    goals = load("goals", root)
    refs |= {g["id"] for g in (goals.get("goals", []) if isinstance(goals, dict) else [])}
    return refs


def roles(root):
    """Role names from bots/*.md headings, the same source check.py uses."""
    return {m.group(1) for f in (root / "bots").glob("*.md") if (m := re.match(r"#\s*(\w+)", f.read_text()))}


def ref_ok(ref, refs, root):
    if not REF.match(ref):
        return False
    if ref.startswith("file:"):
        path = ref[5:]
        return ".." not in path and (root / path).is_file()
    return ref in refs


def kept_count(oaths):
    """(kept, judged): Kept and Kept late over Kept, Kept late and Broken. Withdrawn and Unjudged are listed, not counted."""
    kept = sum(o["verdict"] in ("kept", "kept_late") for o in oaths)
    return kept, kept + sum(o["verdict"] == "broken" for o in oaths)


def errors(root=None, validate=None):
    root = root or ROOT
    p = root / "data/roadmap.json"
    if not p.exists():
        return []
    board = json.loads(p.read_text())
    where = "data/roadmap.json"
    errs = []
    if validate:
        schema = json.loads((root / "data/schema/roadmap.schema.json").read_text())
        errs += [f"{where} {e}" for e in validate(board, schema)]
        if errs:
            return errs
    refs, team = known_refs(root), roles(root)
    state = json.loads((root / "data/state.json").read_text())
    today = state.get("updated") or state["last_run"]  # the record clock, not the wall clock (check.py's calendar rule)
    game = {w for table in (GROUPS, STAGES, VERDICTS, WORDS) for w, _ in table.values()}
    errs += [f"roadmap.py: board word '{w}' is a role name" for w in game for r in team if r.lower() in w.lower().split()]
    seen = set()
    for q in board["quests"]:
        at = f"{where} quest {q['id']}"
        if q["id"] in seen:
            errs.append(f"{at}: duplicate id")
        seen.add(q["id"])
        if not q["history"]:
            errs.append(f"{at}: needs at least one history step")
            continue
        for ref in [q["ref"]] + [h["ref"] for h in q["history"]]:
            if not ref_ok(ref, refs, root):
                errs.append(f"{at}: ref {ref} isn't a record (ideas, design backlog, goals, wins, chat, AARs or a repo file)")
        for r in [q["lead"]] + q.get("party", []):
            if r not in team:
                errs.append(f"{at}: {r} isn't a role in bots/")
        order = [list(STAGES).index(h["stage"]) for h in q["history"]]
        if order != sorted(order) or len(set(order)) != len(order):
            errs.append(f"{at}: stage history must move forward and never repeat a step")
        dates = [h["date"] for h in q["history"]]
        if dates != sorted(dates):
            errs.append(f"{at}: stage history dates go backwards")
        if any(d > today for d in dates):
            errs.append(f"{at}: a stage is dated after the newest record ({today})")
        last = q["history"][-1]["stage"]
        if (q["group"] == "complete") != (last == "complete"):
            errs.append(f"{at}: only a quest whose last stage is complete sits in Completed quests")
        if q["group"] == "complete" and not any(h["stage"] == "complete" and h["ref"].startswith("pr") for h in q["history"]):
            errs.append(f"{at}: a complete quest needs its merged PR (pr<N> in data/wins.json) on the complete step")
        if q["group"] == "abandoned" and not q.get("reason"):
            errs.append(f"{at}: an abandoned quest needs its reason")
        if q["group"] == "held" and not q.get("reason"):
            errs.append(f"{at}: a held quest needs its reason")
    for q in board["quests"]:
        if q.get("unlocks") and q["unlocks"] not in seen:
            errs.append(f"{where} quest {q['id']}: unlocks {q['unlocks']}, which isn't a quest on the board")
    active = sum(q["group"] == "active" for q in board["quests"])
    if active > ACTIVE_CAP:
        errs.append(f"{where}: {active} active quests; the party carries at most {ACTIVE_CAP}")
    for c in board.get("camp", []):
        if not ref_ok(c["ref"], refs, root):
            errs.append(f"{where} camp duty {c['title']!r}: ref {c['ref']} isn't a record")
    seen = set()
    for o in board["oaths"]:
        at = f"{where} oath {o['id']}"
        if o["id"] in seen:
            errs.append(f"{at}: duplicate id")
        seen.add(o["id"])
        for ref in [o["ref"]] + [o[k] for k in ("evidence", "aar") if o.get(k)]:
            if not ref_ok(ref, refs, root):
                errs.append(f"{at}: ref {ref} isn't a record")
        if o["lead"] not in team:
            errs.append(f"{at}: {o['lead']} isn't a role in bots/")
        if o["sworn"] > o["due"]:
            errs.append(f"{at}: due before it was sworn")
        if o["sworn"] > today:
            errs.append(f"{at}: sworn after the newest record ({today}); oaths are never backdated or pre-dated")
        if o["verdict"] == "open":
            if days_between(o["due"], today) > OPEN_PAST_DUE_DAYS:
                errs.append(f"{at}: due {o['due']} and still open more than {OPEN_PAST_DUE_DAYS} days later; the Friday retro judges it")
            continue
        if not o.get("judged"):
            errs.append(f"{at}: a {o['verdict']} oath needs the date it was judged")
        elif o["judged"] > today:
            errs.append(f"{at}: judged after the newest record ({today})")
        if o["verdict"] in ("kept", "kept_late", "broken") and not o.get("evidence"):
            errs.append(f"{at}: a {o['verdict']} oath needs the record that proves it")
        if o["verdict"] == "broken" and not o.get("aar"):
            errs.append(f"{at}: a broken oath links its after-action review")
        if o["verdict"] in ("withdrawn", "unjudged") and not o.get("reason"):
            errs.append(f"{at}: a {o['verdict']} oath needs its reason")
        if o["verdict"] == "kept_late" and o.get("judged", "") <= o["due"]:
            errs.append(f"{at}: kept late means judged after {o['due']}")
    return errs


def days_between(a, b):
    from datetime import date
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


# ---------- the page, the board feed and the calendar events (built by build.py) ----------
STALE_DAYS = 14
REPO = "https://github.com/slopryno/slopworks"
RECORD_FILE = {"i": "data/ideas.json", "d": "data/design_backlog.json", "c": "data/chat.json", "a": "data/aars.json"}


def esc(s):
    import html
    return html.escape(str(s), quote=True)


def day(s):
    from datetime import date
    return date.fromisoformat(s).strftime("%b %-d")


def ref_link(ref, up):
    """(href, label) for a record: merged PRs on GitHub, goals on Metrics, other records in their data file."""
    if ref.startswith("pr"):
        return f"{REPO}/pull/{ref[2:]}", f"PR #{ref[2:]}"
    if ref.startswith("G"):
        return f"{up}metrics/#goals", f"goal {ref}"
    if ref.startswith("file:"):
        return f"{REPO}/blob/main/{ref[5:]}", ref[5:].rsplit("/", 1)[-1]
    return f"{REPO}/blob/main/{RECORD_FILE[ref[0]]}", ref


def next_judging(today):
    """The Friday retro judges oaths: the next Friday on or after the newest record."""
    from datetime import date, timedelta
    d = date.fromisoformat(today)
    return (d + timedelta(days=(4 - d.weekday()) % 7)).isoformat()


def step_label(stage):
    n = list(STAGES).index(stage) + 1
    game, plain = STAGES[stage]
    return f"Step {n} of {len(STAGES)}: {game} ({plain})"


def render(board, today, lead, up="../"):
    """The Quest board body. lead(name) returns the role's avatar, linked name and level from its character sheet."""
    link = lambda ref: (lambda h, t: f'<a href="{esc(h)}">{esc(t)}</a>')(*ref_link(ref, up))
    quests = board["quests"]
    by = lambda g: [q for q in quests if q["group"] == g]
    titles = {q["id"]: q["title"] for q in quests}

    def card(q):
        last = q["history"][-1]
        steps = "".join(f'<li>{esc(STAGES[h["stage"]][0])}, {day(h["date"])} · {link(h["ref"])}</li>' for h in q["history"])
        extra = ""
        if q.get("fog"):
            extra += f'<p><strong>{WORDS["fog"][0]}</strong> ({WORDS["fog"][1]}): {esc(q["fog"])}</p>'
        if q.get("unlocks"):
            extra += f'<p><strong>{WORDS["unlocks"][0]}:</strong> <a href="#q-{esc(q["unlocks"])}">{esc(titles[q["unlocks"]])}</a></p>'
        if q.get("reason"):
            extra += f'<p><strong>Why it was abandoned:</strong> {esc(q["reason"])}</p>'
        party = "".join(f"<span>Party: {lead(r)}</span>" for r in q.get("party", []))
        tags = (f'<span class="tag">{esc(step_label(last["stage"]))}</span>' if q["group"] != "abandoned" else '<span class="tag">Abandoned (dropped)</span>')
        tags += f' <span class="tag">{WORDS["raid"][0]}</span>' if q.get("raid") else ""
        return (f'<article class="card" id="q-{esc(q["id"])}"><h3>{esc(q["title"])}</h3><p>{esc(q["why"])}</p>{extra}'
                f'<p class="meta"><span>{tags}</span><span>Led by {lead(q["lead"])}</span>{party}{link(q["ref"])}</p>'
                + (f'<ol class="steps">{steps}</ol>' if q["group"] != "complete" else "") + "</article>")

    def section(g, intro, items):
        game, plain = GROUPS[g]
        return (f'<h2 id="{g}">{game} <span class="sub">({plain})</span></h2><p>{intro}</p>'
                + ("".join(card(q) for q in items) if items else '<p class="empty">None right now.</p>'))

    kept, judged = kept_count(board["oaths"])
    stale = days_between(board["updated"], today) > STALE_DAYS
    out = (f'<p class="asof">Updated {day(board["updated"])} by <a href="{up}team/{board["owner"].lower()}/">{esc(board["owner"])}</a>. Next oath judging: {day(next_judging(today))}.</p>'
           + (f'<p class="card"><strong>The board may be out of date.</strong> It was last updated {day(board["updated"])}.</p>' if stale else "")
           + '<ul class="stats" aria-label="The board at a glance">'
           + "".join(f'<li><a href="#{g}"><strong>{len(by(g))}</strong><span>{GROUPS[g][0].split()[0].lower()}</span></a></li>' for g in GROUPS)
           + f'<li><a href="#oaths"><strong>{kept} of {judged}</strong><span>oaths kept</span></a></li></ul>')
    complete = sorted(by("complete"), key=lambda q: q["history"][-1]["date"], reverse=True)[:10]
    out += section("complete", f'The newest {len(complete)}, each with its PR. <a href="{up}timeline/">All of them</a>.', complete)
    out += section("active", "What the team is working on now. Each step links the record that moved it.", by("active"))
    out += section("queued", "Accepted and waiting their turn, in no fixed order.", by("queued"))
    out += section("rumor", "Ideas the team is exploring. Nothing here is promised.", by("rumor"))
    out += section("abandoned", "Quests the team dropped, with the reason. Nothing is removed silently.", by("abandoned"))
    rows = ""
    for o in board["oaths"]:
        game, plain = VERDICTS[o["verdict"]]
        meta = f'<span class="tag">{game} ({plain})</span><span>Sworn {day(o["sworn"])}, due {day(o["due"])}</span><span>Led by {lead(o["lead"])}</span>{link(o["ref"])}'
        if o.get("evidence"):
            meta += f'<span>Proof: {link(o["evidence"])}</span>'
        if o.get("aar"):
            meta += f'<span>Lesson: {link(o["aar"])}</span>'
        note = "".join(f'<p>{esc(o[k])}</p>' for k in ("reason", "note", "corrected") if o.get(k))
        rows += f'<article class="card" id="oath-{esc(o["id"])}"><h3>{esc(o["claim"])}</h3>{note}<p class="meta">{meta}</p></article>'
    out += (f'<h2 id="oaths">{WORDS["oath"][0]}s <span class="sub">({WORDS["oath"][1]})</span></h2>'
            f'<p>Oaths kept: {kept} of {judged} judged so far. Withdrawn and unjudged oaths are listed but not counted.</p>' + rows)
    out += (f'<h2 id="camp">{WORDS["camp"][0]} <span class="sub">({WORDS["camp"][1]})</span></h2><p>Work that keeps the team running, tracked on '
            f'<a href="{up}lessons/">Lessons</a> and <a href="{up}metrics/">Metrics</a>.</p><ul>'
            + "".join(f'<li>{esc(c["title"])}: {link(c["ref"])}</li>' for c in board["camp"]) + "</ul>")
    share = "https://bsky.app/intent/compose?text=" + __import__("urllib.parse").parse.quote("The Slopworks bot team's quest board: https://slopryno.com/roadmap/")
    out += ('<h2 id="follow">Follow the board</h2><p>Get each completed quest and judged oath without checking back. Nothing here collects anything.</p><ul>'
            f'<li><a href="feed.xml">Board RSS feed</a></li><li><a href="feed.json">Board JSON Feed</a></li>'
            f'<li><a href="webcal://slopryno.com/calendar.ics">Subscribe to oath due dates</a></li>'
            f'<li><a href="{REPO}">Watch on GitHub (Custom, Releases)</a></li><li><a href="https://aboutfeeds.com/">New to feeds?</a></li>'
            f'<li><a href="mailto:?subject=Slopworks%20quest%20board&amp;body=https%3A%2F%2Fslopryno.com%2Froadmap%2F">Share by email</a></li>'
            f'<li><a href="{esc(share)}">Share on Bluesky</a></li></ul>'
            '<p class="sub">Google Calendar subscribes from a desktop browser only, and refreshes about once a day.</p>')
    return out


def feed_items(board):
    """One item per board event: every stage step and every sworn or judged oath. Ids never change once published."""
    items = []
    for q in board["quests"]:
        for h in q["history"]:
            game, plain = STAGES[h["stage"]]
            head = "Quest complete" if h["stage"] == "complete" else f"Quest {game.lower()}"
            items.append({"id": f'roadmap-{q["id"]}-{h["stage"]}-{h["date"]}', "date": h["date"], "anchor": f'q-{q["id"]}',
                          "title": f'{head}: {q["title"]} ({plain})', "summary": q["why"]})
        if q["group"] == "abandoned":
            items.append({"id": f'roadmap-{q["id"]}-abandoned', "date": q["history"][-1]["date"], "anchor": f'q-{q["id"]}',
                          "title": f'Quest abandoned: {q["title"]} (dropped)', "summary": q["reason"]})
    for o in board["oaths"]:
        items.append({"id": f'roadmap-oath-{o["id"]}-sworn-{o["sworn"]}', "date": o["sworn"], "anchor": f'oath-{o["id"]}',
                      "title": f'Oath sworn: {o["claim"]} (due {day(o["due"])})', "summary": "A dated call the team made about itself."})
        if o["verdict"] != "open":
            game, plain = VERDICTS[o["verdict"]]
            items.append({"id": f'roadmap-oath-{o["id"]}-{o["verdict"]}-{o["judged"]}', "date": o["judged"], "anchor": f'oath-{o["id"]}',
                          "title": f'Oath {game.lower()}: {o["claim"]} ({plain})', "summary": o.get("reason") or o.get("note") or o["claim"]})
    return sorted(items, key=lambda x: (x["date"], x["id"]), reverse=True)


def calendar_events(board):
    """(uid, date, summary, description, status, sequence) per oath for calendar.ics: a withdrawn oath stays, cancelled."""
    out = []
    for o in board["oaths"]:
        game, plain = VERDICTS[o["verdict"]]
        status = "CANCELLED" if o["verdict"] == "withdrawn" else "CONFIRMED"
        summary = f'Oath due: {o["claim"]}' if o["verdict"] == "open" else f'Oath {game.lower()}: {o["claim"]}'
        out.append((f'oath-{o["id"]}', o["due"], summary, f'{game} ({plain}). Led by {o["lead"]}. A dated call the Slopworks team made about itself.',
                    status, 0 if o["verdict"] == "open" else 1))
    return out
