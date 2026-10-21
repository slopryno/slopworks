"""Character sheets as the back of the trading card (Ryno, 2026-10-20 3:06 PM ET: "Go with B, the card back").

A sheet opens with a wide banner in the role's job-type colour: the card's art window (the costume scene in an approved
holiday month), rarity, set number, type, level bar and flavour, with a link back to the card on Team. Below it: jump
chips, the card's moves, then icon-led tiles (stats, next quest, achievements, recent work, about the role, research,
training). Long parts sit in <details>. No script. Every number comes from the records build.py passes in.

The CSS is one shared, cacheable file, site/sheets.css (the card rules from scripts/cards.css plus scripts/sheets.css),
so 19 sheets don't each repeat it (Critic, sheets concept). The badge case is a hook only: badges=None renders nothing
until the held badge rollout ships.
"""
import html, re
from pathlib import Path
import cards as cardmod

e = lambda s: html.escape(str(s), quote=False)
P = cardmod.P
EXTRA = {
 "star": "M0-6l1.8 3.9 4.2.5-3.1 2.9.8 4.2L0 3.4-3.7 5.5l.8-4.2-3.1-2.9 4.2-.5z",
 "flag": "M-5 6.5v-13M-5-6h9l-2 3 2 3h-9",
 "key": "M-3.5-2.5a2.5 2.5 0 1 0 .1 0M-1 0h7M4 0v2.5M6 0v2",
 "cal": "M-6-4.5h12v10.5h-12zM-6-1h12M-3-6.5v3M3-6.5v3",
 "user": "M0-5.5a2.5 2.5 0 1 0 .1 0M-5 6c.5-3.5 2.5-5 5-5s4.5 1.5 5 5",
 "spark": "M0-6.5v4M0 2.5v4M-6.5 0h4M2.5 0h4M-4.5-4.5l2 2M2.5 2.5l2 2M-4.5 4.5l2-2M2.5-2.5l2-2",
 "back": "M5.5 0h-11M-1-4.5L-5.5 0-1 4.5",
 "next": "M-5.5 0h11M1-4.5L5.5 0 1 4.5",
 "cards": "M-5-4h7v10h-7zM-2.5-6.5h7v10",
}
EV_ICON = {"pr_merged": "merge", "signoff": "check", "block_upheld": "block", "deploy_check": "eye", "ci_test_added": "flask",
           "aar_written": "doc", "aar_fix": "wrench", "research_accepted": "book", "pitch_shipped": "rocket",
           "error_prevented": "seal", "regression_prevented": "seal"}
SHEET_CSS = (Path(__file__).with_name("sheets.css")).read_text().replace("GEM", cardmod.GEM).replace("\n", "")
TILES_SHOWN = 6  # newest verified entries shown as tiles; the rest sit behind "N more"
DETAILS_WORDS = 235  # under data/word_limits.json details_limit (250), with room for the summary
TITLE_WORDS = 10


def short(t):
    w = t.split()
    return t if len(w) <= TITLE_WORDS else " ".join(w[:TITLE_WORDS]) + "\u2026"


def wbr(t):
    """Escaped text with a break chance after each slash and underscore, so paths, snake_case file names and "Role/Role:"
    wrap there, not mid-word (430-1440 tiles split "test_training_tracks.py" mid-word otherwise)."""
    return e(t).replace("/", "/<wbr>").replace("_", "_<wbr>")


def words(markup):
    return len(re.sub(r"<[^>]+>", " ", markup).split())


def ic(k, cls=""):
    return f'<svg aria-hidden="true"{" class=" + cls if cls else ""}><use href="#{P}{k}"/></svg>'


def sprite(used):
    paths = {**cardmod.ICONS, **EXTRA}
    return ('<svg width="0" height="0" style="position:absolute" aria-hidden="true">'
            + "".join(f'<symbol id="{P}{k}" viewBox="-7 -7 14 14"><path d="{paths[k]}"/></symbol>' for k in paths if k in used) + "</svg>")


def css(spec, season, stems):
    """site/sheets.css: the card stylesheet (every type and this season's art) plus the sheet layout."""
    return cardmod.css(spec, season, stems) + SHEET_CSS + "\n"


def code(s):
    """Role-file text with `backticks` shown as code, not literal backticks (Comms)."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", e(s))


def quest_note(prog):
    """No calendar date, so it can't go stale: the line shows while Week 2 is still listed as coming, then goes away."""
    return "Tracking starts in Week 2. <a href=\"../xp/\">How XP works</a>" if "week2" in prog.get("later_weeks", {}) else ""


def h2(id_, icon, text):
    return f'<div class="th">{ic(icon, "hi")}<h2 id="{id_}">{e(text)}</h2></div>'


def banner(c):
    r, ty = c["role"], c["ty"]
    return (f'<section class="cb" aria-label="{e(c["n"])}\'s card back"><div class="bn"><span class="art {c["pk"]}"><img src="{c["av"]}" width="112" height="112" alt=""></span>'
            f'<p class="gm">{e(c["rname"])}</p><p class="sn gs">{c["set"]:02d}/{c["total"]}</p></div>'
            f'<div class="id"><p class="jr"><svg role="img" aria-label="{e(r["type"])}" class=ti><use href="#{P}{ty["icon"]}"/></svg><span class="jt">{e(c["title"])}</span></p>'
            f'<p class="lv">Level {c["level"]} · {e(c["lvname"])}<span><strong>{c["xp"]} XP</strong> · {c["togo"]}</span></p>'
            f'<div class="xpbar" aria-hidden="true"><span style="width:{c["pct"]}%"></span></div>'
            f'<p class="fl">{e(c["flavour"])} <a class="tc" href="../#{c["stem"]}">{ic("cards")}See the card</a></p></div></section>')


def moves(c):
    r = c["role"]
    li = ""
    for m in r["moves"]:
        n = c["counts"].get(m["stat"]) if m["stat"] else None
        st = f'<em>{n}<small> {cardmod.SH[m["stat"]][0 if n == 1 else 1]}</small></em>' if n else ""
        li += f'<li>{ic(m["icon"])}<b>{e(m["name"])}</b>{st}<span>{e(m["line"])}</span></li>'
    return (f'<section class="tile mvs" aria-labelledby="moves">{h2("moves", "spark", "Moves")}<ul class="mv">{li}</ul>'
            f'<p class="wr"><span>{e(r["weak_to"])}</span><span>{e(r["resists"])}</span><span>{e(r["hands_off"])}</span></p></section>')


def stats(c):
    tiles = "".join(f'<li>{ic(EV_ICON.get(k, "spark"))}<b>{n}</b><span>{e(c["labels"][k])}</span><small>+{v} XP</small></li>' for k, (n, v) in c["kinds"])
    skipped = ", ".join(f"{v} {k}" for k, v in c["skipped"].items() if v)
    note = (f'{c["ok"]} entries count' + (f'; {skipped} don\'t' + (f' ({e(c["notes"])})' if c["notes"] else "") if skipped else "") + '. <a href="../xp/">How XP works</a>')
    body = f'<ul class="sts">{tiles}</ul>' if tiles else '<p class="empty">No XP yet. Every role starts here.</p>'
    return f'<section class="tile" aria-labelledby="stats">{h2("stats", "chart", "Stats")}{body}<p class="meta">{note}</p></section>'


def quest(c):
    note = f'<p class="meta">{c["quest_note"]}</p>' if c["quest_note"] else ""
    return f'<section class="tile qt" aria-labelledby="quest">{h2("quest", "flag", "Next quest")}<p class="big">{e(c["quest"])}</p>{note}</section>'


def trophies(c):
    li = ""
    for a in c["ach"]:
        if a["got"]:
            d = a["got"]["timestamp"][:10]
            li += (f'<li class="got"><a href="{e(a["got"]["evidence"])}">{ic("star", "md")}<b>{e(a["name"])}</b>'
                   f'<time datetime="{d}">{int(d[5:7])}/{int(d[8:])}</time></a></li>')
        else:  # locked says "Not yet" in words, not by colour alone (training track m6)
            li += f'<li>{ic("star", "md")}<b>{e(a["name"])}</b><span>Not yet: {e(a["rule"][0].lower() + a["rule"][1:])}</span></li>'
    got = sum(1 for a in c["ach"] if a["got"])
    bd = ""  # badge case hook: renders once the badge rollout passes {family: count}
    if c.get("badges"):
        bd = '<ul class="bc">' + "".join(f'<li><img src="../../assets/badges/{f}.svg" width="40" height="40" alt="{e(f.capitalize())} badges:">{n}</li>' for f, n in c["badges"].items()) + "</ul>"
    return f'<section class="tile" aria-labelledby="trophies">{h2("trophies", "star", f"Achievements {got}/{len(c["ach"])}")}<ul class="tr">{li}</ul>{bd}</section>'


def work(c):
    if not c["work"]:
        return f'<section class="tile wide" aria-labelledby="work">{h2("work", "merge", "Recent work")}<p class="empty">No verified work yet. It appears here once a reviewer approves it.</p></section>'
    def tile(y):
        d = y["timestamp"][:10]
        return (f'<li><a href="{e(y["evidence"])}"><span class="wt">{ic(EV_ICON.get(y["type"], "spark"))}<b>+{y["gain"]} XP</b>'
                f'<time datetime="{y["timestamp"]}">{int(d[5:7])}/{int(d[8:])}</time></span><span class="wn">{wbr(y["task"])}</span>'
                f'<small>{e(c["labels"][y["type"]])} · reviewed by {e(y["reviewer"])}</small></a></li>')
    head, rest = c["work"][:TILES_SHOWN], c["work"][TILES_SHOWN:]
    more = ""
    if rest:  # Comms's 250-word cap per <details>: short titles (the link has the rest), then drop the per-row detail if needed
        def rows(meta):
            return "".join(f'<li><time datetime="{y["timestamp"]}">{y["timestamp"][:10]}</time> <a href="{e(y["evidence"])}">{e(short(y["task"]))}</a>'
                           + (f' <span class="meta">+{y["gain"]} XP · {e(c["labels"][y["type"]])} · reviewed by {e(y["reviewer"])}</span>' if meta else f' <span class="meta">+{y["gain"]} XP</span>')
                           + "</li>" for y in rest)
        li = rows(True)
        if words(li) > DETAILS_WORDS:
            li = rows(False)
        more = f'<details><summary>{len(rest)} more</summary><ul class="worklist">{li}</ul></details>'
    return (f'<section class="tile wide" aria-labelledby="work">{h2("work", "merge", "Recent work")}'
            f'<p class="meta">{c["verified"]} Each has its evidence and a reviewer who isn\'t {e(c["n"])}.</p><ul class="col">{"".join(tile(y) for y in head)}</ul>{more}'
            f'<p class="meta">{c["shown_line"]} <a href="{c["ledger"]}">Full record</a></p></section>')


def about(c):
    rows = f'<li>{ic("map")}<b>Owns</b><span>{e(c["owns"])}</span></li>' + (f'<li>{ic("block")}<b>Can\'t</b><span>{code(c["cant"])}</span></li>' if c["cant"] else "")
    return (f'<section class="tile ab" aria-labelledby="about">{h2("about", "user", "About the role")}<p class="bio">{e(c["bio"])}</p>{c["objective"]}'
            f'<details class="more"><summary>Owns, limits and latest handoff</summary><ul class="kv">{rows}</ul>'
            f'<h3>{ic("quote", "hi")}Latest handoff</h3>{c["latest"]}<p class="links"><a href="{c["rolefile"]}">Role file</a></p></details></section>')


def research(c):
    if not c["rday"]:
        return ""
    last = (f'<p class="rl">{ic("doc")}<span>Last: <a href="{c["rlast_href"]}">{e(c["rlast"]["question"])}</a></span><time datetime="{c["rlast"]["date"]}">{c["rlast"]["date"]}</time></p>'
            if c["rlast"] else '<p class="empty">No notes yet. The weekly rotation adds one.</p>')
    return (f'<section class="tile" aria-labelledby="research">{h2("research", "magnifier", "Research")}'
            f'<p class="meta rs">{ic("cal")}Every {e(c["rday"])}, on the weekly research rotation.</p><p>{e(c["rfocus"])}.</p>{last}</section>')


def training(c):
    if not c["skills"] and not c["tracks"]:
        return ""
    sk = "".join(f'<li>{ic("key")}<a href="{e(u)}">{e(k)}</a><small>{e(src)}</small></li>' for k, u, src, use in c["skills"])
    uses = "".join(f'<li><strong>{e(k)}.</strong> {e(use)}</li>' for k, u, src, use in c["skills"])
    out = (f'<section class="tile wide" aria-labelledby="training">{h2("training", "key", "Training")}'
           f'<p class="meta">Trained {e(c["trained"])} from pinned, MIT-licensed toolkits. Training earns no XP; first real use counts under the normal rules. <a href="{c["skills_src"]}">Sources and pins</a></p>'
           + (f'<ul class="sk">{sk}</ul><details><summary>What each skill does</summary><ul class="worklist">{uses}</ul></details>' if sk else ""))
    for tr in c["tracks"]:
        pips = "".join("<i></i>" for _ in tr["mods"])
        out += (f'<h3 id="track-{tr["id"]}">{ic("book", "hi")}{e(tr["title"])} track</h3><p class="pips">{pips}<span>{len(tr["mods"])} modules from public guides</span></p>'
                f'<p class="chips"><span class="chip {tr["grade"]["state"]}">{e(tr["grade_text"])}</span><span class="chip">{len(tr["findings"])} findings at {tr["width"]}px</span></p>'
                f'<details><summary>The {len(tr["mods"])} modules</summary><ol class="worklist">{tr["mods_html"]}</ol></details>'
                f'<details><summary>Audit of the live site at {tr["width"]}px, {e(tr["day"])}: {len(tr["findings"])} findings</summary><p class="meta">{tr["pages"]} pages, light and dark.</p><ul class="worklist">{tr["findings_html"]}</ul></details>')
    return out + "</section>"


def claimed(c):
    li = "".join(f'<li><time datetime="{s["date"]}">{s["date"]}</time> {e(s["did"])}</li>' for s in c["claimed"])
    return (f'<details class="tile cl2"><summary>{ic("quote", "hi")}Claimed in standups ({len(c["claimed"])})</summary><p class="meta">Standup lines: what {e(c["n"])} said it did. They carry no XP until they link to evidence.</p>'
            + (f'<ul class="worklist">{li}</ul>' if li else '<p class="empty">No standup claims.</p>') + "</details>")


def render(c):
    """The sheet body for one role. c is built in build.py from the records."""
    cls = f't{c["ti"]} r{c["rk"]}' + (f' g-{c["stem"]}' if c["art"] else "") + (" holo" if c["rk"] >= 3 else "")
    chips = [("stats", "chart", "Stats"), ("quest", "flag", "Quest"), ("trophies", "star", "Achievements"), ("work", "merge", "Work"), ("about", "user", "About")]
    if c["skills"] or c["tracks"]:
        chips.append(("training", "key", "Training"))
    jump = "".join(f'<a href="#{i}">{ic(k)}{t}</a>' for i, k, t in chips)
    body = (f'<div class="sb {cls}">{banner(c)}<nav class="jp" aria-label="On this sheet">{jump}</nav>{moves(c)}'
            f'<div class="sg">{stats(c)}{quest(c)}{trophies(c)}{work(c)}{about(c)}{research(c)}{training(c)}</div>{claimed(c)}'
            f'<nav class="sf" aria-label="More sheets"><a href="../">{ic("back")}Team</a><a href="../xp/">How XP works</a>'
            f'<a class="nx" href="{c["next_href"]}">{e(c["next_text"])}{ic("next")}</a></nav></div>')
    return sprite(set(re.findall(r'href="#' + re.escape(P) + r'([a-z]+)"', body))) + body


def errors(files):
    """Sheet rules (code first): every role sheet (not the CEO's team/ryno/: scripts/ceo.py links sheets.css too and adds a small inline style for his gold frame, cards v6) links the shared stylesheet, carries no inline <style>, and no dated quest note."""
    out = []
    for k, doc in files.items():
        if re.fullmatch(r"team/(?!xp/|ryno/)\w+/index\.html", k):  # team/ryno/ is the CEO's own sheet (scripts/ceo.py; inline style for his gold, cards v6)
            if 'href="../../sheets.css"' not in doc:
                out.append(f"site/{k}: doesn't link the shared sheets.css")
            if "<style" in doc:
                out.append(f"site/{k}: inline <style>; sheet CSS belongs in site/sheets.css")
            if re.search(r"Tracking starts in Week 2 \(", doc):
                out.append(f"site/{k}: the quest note carries a date")
    return out
