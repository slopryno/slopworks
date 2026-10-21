"""Ryno's CEO card and character sheet (Ryno, Oct 20, 2026: 2:34 PM ET "lets create myself as a grok bot blob ... added as
ceo to the teams page"; 3:48 PM ET the rhino is his everyday look; 3:54 PM ET "Today, i will override and have the team review
+ embedd a link to my x account").

Same card family as scripts/cards.py (a mini in the grid that opens with CSS :target, no script), in its own CEO group above
Leadership. He's the human owner, so there's no XP, level or rarity: his stats are real records counted at build time from
data/ceo_decisions.json, data/ceo_overrides.json and data/ideas.json. Wording by Comms.

Holiday rule (HOLIDAY): background only. His avatar is scripts/avatars.py FIXED["ceo"], the same file in every season; a
holiday month whose look Ryno approved changes only his card's art-window scene (ART).

His X link is plain text in a normal link: no embed, widget, script or image from X, and it carries rel="noopener noreferrer".
X_URL is the only x.com address on the site (tests/test_ceo_card.py)."""
import html, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
e = lambda s: html.escape(str(s), quote=False)
STEM, NAME, TYPE = "ryno", "Ryno", "Management"
X_URL = "https://x.com/slopryno"  # his public profile; Ryno, Oct 20 3:54 PM ET: "embedd a link to my x account"
X_LINK = f'<a class="xl" href="{X_URL}" rel="noopener noreferrer" title="slopryno on X">slopryno on X</a>'  # an X icon on the card; the text is its name (v5)
HOLIDAY = "background-only"
_SVG = '<svg width="{0}" height="{0}" viewBox="-7 -7 14 14" fill="none" stroke="{1}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="{2}"/></svg>'
# Sheet only (the Team page draws these from the shared mask strip): inline, original, nothing loaded from X.
ROW = 'style="display:inline-flex;align-items:center;gap:.4rem;min-height:44px"'


def _icons():
    import cards as cm
    hv = _SVG.format(24, "#b8860b", cm.UI["hv"]).replace('aria-hidden="true">', 'role="img" aria-label="Human verified" style="vertical-align:-4px"><title>Human verified</title>')
    return hv, _SVG.format(24, "currentColor", cm.UI["x"])
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
    """His slot: the mini (a link to #ryno) and the full card. avatar_src is the same file in every season (HOLIDAY)."""
    types = [x["name"] for x in spec["types"]]
    ty = spec["types"][types.index(TYPE)]
    art = ART.get(season)
    pk = art["particles"] if art else ty["particles"]
    cls = f"t{types.index(TYPE)} lead" + (f" g-{STEM}" if art else "") + " holo"
    return (f'<div class="slot {cls}"><a class="o" id="{STEM}" href="#m-{STEM}" tabindex="-1" aria-hidden="true"></a><i class="c" id="m-{STEM}"></i><div class="card">'
            f'<a class="open" href="#{STEM}"><span class="art {pk}"><img src="{avatar_src}" width="112" height="112" alt=""></span>{CROWN}'
            f'<span class="nm"><b>{NAME} <span class="hu" title="Human verified">Human verified</span></b><span class="ml" title="{TYPE}">CEO</span>'
            f'</span></a>{X_LINK}'
            f'<div class="body"><a class="cl" href="#m-{STEM}">Close</a>'
            f'<p class="ty"><b>{TYPE}</b></p><p class="lv" title="{TYPE}">CEO</p>'
            f'<ul class="mv">{moves(cm, facts(root))}</ul>'
            f'<p class="ft">One of one<span class="sn">00/{total}</span></p>'
            f'<p class="fl">{e(FLAVOUR)}</p></div><p class="lk"><a class="sh" title="Character sheet" href="{STEM}/">Character sheet</a></p></div></div>')


def _day(ts):
    m, d = ts[5:7], ts[8:10]
    return f"{int(m)}/{int(d)}"


def sheet(repo, total, next_html, root=None):
    """His character sheet, in the same layout as today's role sheets (site/style.css only)."""
    f = facts(root)
    hv, xi = _icons()
    dec, ovr = load("ceo_decisions.json", root), load("ceo_overrides.json", root)
    data = lambda n: f'<a href="{repo}/blob/main/data/{n}">{n}</a>'
    pw = "".join(f'<li><strong>{e(name)}</strong>: {e(line)} <span class="meta">{f[rec]} {unit[0 if f[rec] == 1 else 1]} on record</span></li>'
                 for _, name, line, rec, unit in MOVES)
    # Ryno, Oct 21 8:51 AM ET: no CEO quotes on the site. Each line says what he decided and when; his exact words and their
    # ET time stay on the PR and in the add-only records (tests/test_ceo_quotes.py).
    yes = "".join(f'<li><time datetime="{x["applied_at"][:10]}">{_day(x["applied_at"])}</time> <a href="{e(x["evidence"])}">PR #{x["pr"]}</a> '
                  f'{"CEO approved in chat." if x["quote"] else "He added the label himself on GitHub."} '
                  f'<span class="meta">label by {"the Assistant, after his yes in chat" if x["applied_by"] == "Executive Assistant" else "Ryno"}</span></li>'
                  for x in reversed(dec))
    ov = "".join(f'<li><time datetime="{x["at"][:10]}">{_day(x["at"])}</time> CEO override '
                 f'<span class="meta">up to {x["max_prs"]} PR{"" if x["max_prs"] == 1 else "s"}, named work only, until 11:59 PM ET that day</span></li>' for x in reversed(ovr))
    return (f'<section class="sheet card" style="border-top:4px solid #b8860b;flex-wrap:wrap"><img class="av" src="../../assets/avatars/ceo.svg" width="96" height="96" alt="">'
            f'<div style="flex-basis:10rem"><p class="title">CEO · one of one, 00/{total}</p><p class="lvl" style="display:flex;align-items:center;gap:.35rem;flex-wrap:wrap">The owner {hv}'
            f'<a href="{X_URL}" rel="noopener noreferrer" aria-label="slopryno on X" title="slopryno on X" style="display:inline-grid;place-items:center;width:44px;height:44px;margin-left:-.6rem">{xi}</a></p>'
            f'<p>{e(FLAVOUR)}</p><p style="margin:0"><a href="../#{STEM}" {ROW}>See his card</a></p></div></section>'
            f'<h2>Powers</h2><ul>{pw}</ul>'
            f'<p class="meta">Weak to {e(WEAK)}. Resists {e(RESISTS)}. Hands off to {e(HANDS_OFF)}.</p>'
            f'<h2>Safeguard</h2><p class="meta">Only Ryno\'s yes lets a change that loosens a safety check through. '
            f'The Assistant adds the label only after his yes in chat; his exact words stay on the PR.</p><ul class="worklist">{yes}</ul>'
            f'<h2>Unblock</h2><p class="meta">Each override lifts the daily PR limit for named work, for that day only.</p><ul class="worklist">{ov}</ul>'
            f'<h2>The human</h2><p>Ryno is a person, not a Grok Bot. He owns Slopworks and sets its direction. He doesn\'t sign off routine work: '
            f'bots review and merge each other\'s. The team pings him only for a real disagreement or a safety case.</p>'
            f'<p class="meta">The rhino is his look all year. On holidays only his card\'s background changes.</p>'
            f'<p class="meta">Counted at build time from {data("ceo_decisions.json")}, {data("ceo_overrides.json")} and {data("ideas.json")} '
            f'({f["decisions"]} calls decided by the CEO). Nothing typed by hand.</p>'
            f'<p><a href="../">Back to the team</a> · <a href="../../how/">Where the human decides</a></p>' + next_html)
