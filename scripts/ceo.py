"""Ryno's CEO card and character sheet (Ryno, Oct 20, 2026: 2:34 PM ET "lets create myself as a grok bot blob ... added as
ceo to the teams page"; 3:48 PM ET the rhino is his everyday look; 3:54 PM ET "Today, i will override and have the team review
+ embedd a link to my x account").

Same deck family as scripts/cards.py (details/summary flip in the swipe deck, no script), first in the CEO group above
Leadership. He's the human owner, so there's no XP, level or rarity: his stats are real records counted at build time from
data/ceo_decisions.json, data/ceo_overrides.json and data/ideas.json. Wording by Comms.

Holiday rule (HOLIDAY): background only. His avatar is scripts/avatars.py FIXED["ceo"], the same file in every season; a
holiday month whose look Ryno approved changes only his card's art-window scene (ART).

His X link is plain text in a normal link: no embed, widget, script or image from X, and it carries rel="noopener noreferrer".
X_URL is the only x.com address on the site (tests/test_ceo_card.py)."""
import html, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
e = lambda s: html.escape(str(s), quote=False)
STEM, NAME, TYPE = "ryno", "Ryno", "Management"
X_URL = "https://x.com/slopryno"  # his public profile; Ryno, Oct 20 3:54 PM ET: "embedd a link to my x account"
X_LINK = f'<a class="xl" href="{X_URL}" rel="noopener noreferrer" title="slopryno on X">slopryno on X</a>'  # an X icon on the card; the text is its name (v5)
HOLIDAY = "background-only"
MOVES = [  # (icon, name, line, record, unit)
    ("seal", "Safeguard", "Only his yes loosens a safety check.", "approvals", ("PR", "PRs")),
    ("rocket", "Unblock", "Lifts the daily PR limit for named work.", "overrides", ("override", "overrides")),
    ("scale", "Vision", "Settles disputes and sets the direction.", "decisions", ("call", "calls")),
]
WEAK, RESISTS, HANDS_OFF = "routine pings", "overclaiming", "Assistant, Coordinator"
FLAVOUR = "Makes the call, then leaves the work to the team."
ART = {"halloween": {"scene": "radial-gradient(circle at 50% 30%,#66def955,#0000 45%),linear-gradient(#071a33,#173a63)", "particles": "up", "particle_colour": "#bfefff"}}


def load(f, root=None):
    return json.loads(((root or ROOT) / "data" / f).read_text())


def facts(root=None):
    """Real counts, never typed: each comes from a committed record."""
    return {"approvals": len(load("ceo_decisions.json", root)), "overrides": len(load("ceo_overrides.json", root)),
            "decisions": sum(1 for i in load("ideas.json", root) if i.get("decided_by") == "CEO")}


BATS = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 48'%3E%3Cpath transform='translate(-14 -5)' "
        "d='M30 22c-2-3-6-4-9-2 2-2 2-5 1-7 3 1 6 3 7 6l1-2 1 2c1-3 4-5 7-6-1 2-1 5 1 7-3-2-7-1-9 2z'/%3E%3Cpath fill='%23fff' fill-opacity='.6' fill-rule='evenodd' "
        "d='M42 42v-9a6 6 0 0 1 12 0v9l-2-1.5-2 1.5-2-1.5-2 1.5-2-1.5zM45.5 32h2v2.5h-2zm3 0h2v2.5h-2z'/%3E%3C/svg%3E")  # Ryno, Oct 20: "little bats" (7:46 PM ET), then ghosts in a checkerboard (9:17 PM ET). One 64x48 tile: bat top-left, ghost bottom-right.


def css(season):
    art = ART.get(season)
    g = (f'.g-{STEM}{{--g:{art["scene"]};--p:{art["particle_colour"]}}}'
         f'.g-{STEM} .art::before{{--u:url("{BATS}");background:var(--u) 0 0/64px 48px;opacity:.7}}') if art else ""  # drifts up with the card's own particle motion
    return g + (
        # Leader frame: gold foil on the border box (so the corners blend), same card family; the inside keeps the Management colour.
        ".lead .card{background:linear-gradient(var(--card) 0 0) padding-box,linear-gradient(135deg,#b8860b,#ffe9a8 30%,#c99a2e 50%,#fff3c4 70%,#a8790a) border-box}"
        ".lead .nm:after,.lead .ft:before{display:none}.lead .mv{padding:0;font-size:1rem}.lead .lk{--a:#b8860b}"  # his tap cue is gold, like his frame
        ".hu{display:inline-flex;vertical-align:-3px;font-size:0}.hu::before{background:#b8860b;--s:14px}.o:target~.card .hu::before{--s:20px}"  # icon only; its words stay as the name
        ".lead .card>.xl,.lk{display:none}.o:target~.card>.lk{display:block;grid-column:3;margin:0;align-self:center}"
        # Ryno, 10:40 PM ET: his mini card matches the bots' (one grid cell, portrait art, name and role under it); the X and sheet
        # icons show only on the open card. Ryno, 8:59 PM ET: on the open card the X sits on the top row after his badge: the header's name and the X
        # become grid cells (the header boxes use display:contents), the X right after the name; the role spot moves to the CEO label.
        ".lead .xl::before{--s:20px}"
        ".lead .o:target~.card :is(.open,.nm){display:contents}.lead .o:target~.card .nm>b{grid-area:1/1;align-self:center}"
        ".lead .o:target~.card .xl{display:inline-flex;grid-area:1/2;justify-self:start;position:static;margin-left:-13px}.lead .o:target~.card .art{grid-area:2/1/3/-1;min-height:0}"
        ".lead .o:target~.card .ml,.lead .lv::after{display:none}@media(max-height:36rem){.lead .lv{margin:0;line-height:1.1}}.lead .lv::before{--x:var(--y)}")


def moves(cm, f):
    out = ""
    for k, name, line, rec, unit in MOVES:
        c = f[rec]
        out += (f'<li>{cm.icon(k)}<b>{e(name)}</b>'
                f'<em>{c}<small> {unit[0 if c == 1 else 1]}</small></em><span>{e(line)}</span></li>')
    return out


# His corner badge (Ryno, Oct 20 10:47 PM ET: "For ryno change the star to a crown"): the bots' badge style, a gold crown on
# his badge blue; the rhino itself has no crown (10:45 PM ET).
CROWN = '<svg class="jb" viewBox="-10 -10 20 20"><circle r="10" fill="#146fac"/><path d="M-5 5l-.7-6.5 3 3.3 2.7-6.8 2.7 6.8 3-3.3-.7 6.5Z" fill="#f2c14e"/></svg>'


def card(cm, spec, season, total, avatar_src, root=None):
    """His deck slot: details/summary flip. avatar_src is the same file in every season (HOLIDAY)."""
    types = [x["name"] for x in spec["types"]]
    art = ART.get(season)
    cls = f"t{types.index(TYPE)} lead" + (f" g-{STEM}" if art else "") + " holo"
    return (
        f'<li class="slot {cls}" id="card-{STEM}" data-group="CEO">'
        f'<details class="flip"><summary><span class="vh">{NAME}</span>'
        f'<div class="face front" aria-hidden="true">'
        f'<img class="av" src="{avatar_src}" width="112" height="112" alt="">{CROWN}'
        f'<p class="nm">{NAME} <span class="hu" title="Human verified">Human</span></p>'
        f'<p class="role">{TYPE}</p><p class="lv" title="{TYPE}">CEO</p>'
        f'<p class="rar">One of one · 00/{total}</p>'
        f'</div></summary>'
        f'<div class="face rear"><p class="role">{TYPE}</p><p class="nm">{NAME}</p>'
        f'{X_LINK}'
        f'<ul class="mv">{moves(cm, facts(root))}</ul>'
        f'<p class="fl">{e(FLAVOUR)}</p>'
        f'<p class="acts"><a class="sh" title="Character sheet" href="{STEM}/">Character sheet</a></p>'
        f'</div></details></li>')


def _day(ts):
    m, d = ts[5:7], ts[8:10]
    return f"{int(m)}/{int(d)}"


GOLD = "linear-gradient(135deg,#b8860b,#ffe9a8 30%,#c99a2e 50%,#fff3c4 70%,#a8790a) border-box"
ABIL = {"approvals": "safeguard", "overrides": "unblock", "decisions": "vision"}
HEAD = {"approvals": "Only Ryno's yes lets a change that loosens a safety check through. The Assistant adds the label only after his yes in chat.",
        "overrides": "Each override lifts the daily PR limit for named work, for that day only.",
        "decisions": "Ideas the CEO decided, newest first, with where each one stands."}
STATE = {"shipped": "Shipped", "yes": "In progress", "later": "Later", "no": "No"}


def calls(root=None):
    """His calls from data/ideas.json: (date, short title, state), newest first. Titles are the team's words, never his."""
    return sorted(((i["decided"], i.get("short_title") or i["id"], i["state"]) for i in load("ideas.json", root) if i.get("decided_by") == "CEO"), reverse=True)


def records(root=None):
    """Each power's uses, newest first, as (ISO date, line). Dates and PR links only: his words stay on the PRs and records."""
    dec, ovr = load("ceo_decisions.json", root), load("ceo_overrides.json", root)
    return {"approvals": [(x["applied_at"][:10], f'<a href="{e(x["evidence"])}">PR #{x["pr"]}</a> '
                           + ("CEO approved in chat." if x["quote"] else "He added the label himself on GitHub.")) for x in reversed(dec)],
            "overrides": [(x["at"][:10], f'CEO override <span class="meta">up to {x["max_prs"]} PR{"" if x["max_prs"] == 1 else "s"}, named work only, that day</span>') for x in reversed(ovr)],
            "decisions": [(d, f'{e(t)} <span class="meta">{STATE.get(st, e(st))}</span>') for d, t, st in calls(root)]}


def sheet_css(season):
    """Inline on team/ryno/ only; site/sheets.css carries the shared card back. Gold frame, crown, three power cards."""
    return css(season) + (
        f".ceo{{--a:#946c0a}}.ceo .cb{{background:linear-gradient(var(--card) 0 0) padding-box,{GOLD}}}.ceo .gm::before,.ceo .id .lv::before{{display:none}}"
        ".ceo .bn .jb{top:.5rem;right:.5rem;bottom:auto;width:30px;height:30px}.ceo .jr{gap:.25rem}.ceo .jr .xl{margin-left:-.4rem}.ceo .jr .hu::before{--s:20px}"
        ".worklist time{font-variant-numeric:tabular-nums;color:var(--muted);margin-right:.25rem}"
        ".sb .pw{list-style:none;margin:1rem 0;padding:0;display:grid;gap:.75rem}"
        f".pw>li{{border:3px solid #0000;border-radius:14px;background:linear-gradient(var(--card) 0 0) padding-box,{GOLD};padding:.8rem .9rem}}"
        ".pw .ph{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:.6rem}.pw .ph>svg{width:40px;height:40px;padding:9px;border-radius:12px;background:var(--a);color:#fff}"
        ".pw h2{margin:0;font-size:1.125rem}.pw .n{font-size:1.75rem;font-weight:800;line-height:1;text-align:right;font-variant-numeric:tabular-nums}.pw .n small{display:block;font-size:.75rem;font-weight:600;color:var(--muted)}"
        ".pw p{margin:.45rem 0}.pw summary{min-height:44px;display:flex;align-items:center;font-weight:600;cursor:pointer}"
        "@media(max-width:20rem){.pw .ph{grid-template-columns:minmax(0,1fr) auto}.pw .ph>svg{display:none}.sb .pw>li{padding:.6rem .5rem}}"
        "@media(min-width:48rem){.sb .pw{grid-template-columns:repeat(3,minmax(0,1fr));align-items:start}}")


def sheet(repo, total, next_html, root=None):
    """His own card back (cards v6, CEO direction Oct 21): the gold banner, then his three powers as three gold cards, each
    with its count and its record behind a fold. Every number and line comes from the records; no quotes (Oct 21 rule)."""
    import cards as cm, sheets as sh, avatars
    f, rec = facts(root), records(root)
    ic = sh.ic
    spec = cm.load()
    types = [x["name"] for x in spec["types"]]
    season = avatars.committed_season() or "normal"
    art = ART.get(season)
    pk = art["particles"] if art else spec["types"][types.index(TYPE)]["particles"]
    crown = CROWN.replace("<svg ", '<svg role="img" aria-label="CEO" ', 1)
    cls = f"t{types.index(TYPE)} lead holo ceo" + (f" g-{STEM}" if art else "")
    ban = (f'<section class="cb" aria-label="Ryno\'s card back"><div class="bn"><span class="art {pk}"><img src="../../assets/avatars/ceo.svg" width="112" height="112" alt=""></span>'
           f'{crown}<p class="gm">One of one · 00/{total}</p></div>'
           f'<div class="id"><p class="jr"><span class="hu" title="Human verified">Human</span><span class="jt">CEO</span>'
           f'<a class="xl" href="{X_URL}" rel="noopener noreferrer" aria-label="slopryno on X" title="slopryno on X">slopryno on X</a></p>'
           f'<p class="lv">The one human on a team of {total} bots</p>'
           f'<p class="fl">{e(FLAVOUR)} <a class="tc" href="../#card-{STEM}">{ic("cards")}See the card</a></p></div></section>')
    pw = "".join(
        f'<li id="{ABIL[r]}"><div class="ph">{ic(k)}<h2>{e(name)}</h2><p class="n">{f[r]}<small>{unit[0 if f[r] == 1 else 1]}</small></p></div>'
        f'<p>{e(line)}</p><p class="meta">{HEAD[r]}</p><details><summary>The record ({len(rec[r])})</summary><ul class="worklist">'
        + "".join(f'<li><time datetime="{d}">{_day(d)}</time> {h}</li>' for d, h in rec[r]) + "</ul></details></li>"
        for k, name, line, r, unit in MOVES)
    human = ('<div class="sg"><section class="tile ab" id="human" aria-labelledby="human-h">' + sh.h2("human-h", "user", "The human")
             + '<p class="bio">Ryno is a person, not a Grok Bot. He owns Slopworks and sets its direction.</p>'
             '<p>He doesn\'t sign off routine work: bots review and merge each other\'s. The team pings him only for a real disagreement or a safety case.</p>'
             '<p class="meta">The rhino is his look all year. On holidays only his card\'s background changes.</p></section></div>')
    src = (f'<p class="meta">Counted at build time from <a href="{repo}/blob/main/data/ceo_decisions.json">ceo_decisions.json</a>, '
           f'<a href="{repo}/blob/main/data/ceo_overrides.json">ceo_overrides.json</a> and <a href="{repo}/blob/main/data/ideas.json">ideas.json</a>. Nothing typed by hand.</p>')
    nx = re.search(r'href="([^"]+)">([^<]+)</a>', next_html)
    foot = (f'<nav class="sf" aria-label="More sheets"><a href="../">{ic("back")}Team</a><a href="../../how/">Where the human decides</a>'
            + (f'<a class="nx" href="{nx[1]}">{nx[2]}{ic("next")}</a>' if nx else "") + '</nav>')
    jump = "".join(f'<a href="#{i}">{ic(k)}{t}</a>' for i, k, t in (("safeguard", "seal", "Safeguard"), ("unblock", "rocket", "Unblock"), ("vision", "scale", "Vision"), ("human", "user", "The human")))
    body = f'<div class="sb {cls}">{ban}<nav class="jp" aria-label="On this sheet">{jump}</nav><ul class="pw" aria-label="Powers">{pw}</ul>{human}{src}{foot}</div>'
    return sh.sprite(set(re.findall(r'href="#' + re.escape(sh.P) + r'([a-z]+)"', body))) + body
