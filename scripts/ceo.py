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
X_LINK = f'<a class="sh" href="{X_URL}" rel="noopener noreferrer">slopryno on X</a>'
HOLIDAY = "background-only"
MOVES = [  # (icon, name, line, record, unit)
    ("seal", "Final yes", "Only his yes lets a safety check loosen.", "approvals", ("PR", "PRs")),
    ("rocket", "Override", "Lifts the daily PR limit for named work.", "overrides", ("override", "overrides")),
    ("scale", "The call", "Settles disagreements and sets the direction.", "decisions", ("call", "calls")),
]
WEAK, RESISTS, HANDS_OFF = "routine pings", "overclaiming", "Assistant, Coordinator"
FLAVOUR = "Makes the call, then leaves the work to the team."
BLURB = "The human who owns Slopworks. Steps in only where the rules say."
ART = {"halloween": {"scene": "radial-gradient(circle at 50% 30%,#66def955,#0000 45%),linear-gradient(#071a33,#173a63)", "particles": "up", "particle_colour": "#bfefff"}}


def load(f, root=None):
    return json.loads(((root or ROOT) / "data" / f).read_text())


def facts(root=None):
    """Real counts, never typed: each comes from a committed record."""
    return {"approvals": len(load("ceo_decisions.json", root)), "overrides": len(load("ceo_overrides.json", root)),
            "decisions": sum(1 for i in load("ideas.json", root) if i.get("decided_by") == "CEO")}


def css(season):
    art = ART.get(season)
    g = f'.g-{STEM}{{--g:{art["scene"]};--p:{art["particle_colour"]}}}' if art else ""
    return g + (
        # Leader frame: gold foil border, same card family; the inside keeps the Management colour. The shine is the holo one.
        ".slot.lead{grid-column:span 2;aspect-ratio:auto;height:11.5rem}"
        ".lead .card{background:linear-gradient(var(--card) 0 0) padding-box,linear-gradient(135deg,#b8860b,#ffe9a8 30%,#c99a2e 50%,#fff3c4 70%,#a8790a)}"
        ".lead .open{flex-direction:row;gap:.6rem}.lead .art{flex:0 0 46%}.lead .nm{align-content:center}.lead .nm b{font-size:1.25rem}"
        ".lead .nm:after,.lead .ft:before,.o:target~.card .bl{display:none}.ow{font-size:.875rem;color:var(--muted);margin:.45rem 0}.ow b{color:var(--fg)}"
        ".hu{flex-basis:100%;max-width:fit-content;border:2px solid #b8860b;border-radius:99px;padding:0 .5rem;font-size:.75rem;font-weight:700}"
        ".bl{font-size:.8125rem;color:var(--muted)}.lk{display:flex;flex-wrap:wrap;column-gap:1rem;margin:0}")


def moves(cm, f):
    out = ""
    for k, name, line, rec, unit in MOVES:
        c = f[rec]
        out += (f'<li>{cm.icon(k)}<b>{e(name)}</b><i class="pp n{cm.tier(c)}"></i>'
                f'<em>{c}<small> {unit[0 if c == 1 else 1]}</small></em><span>{e(line)}</span></li>')
    return out


def card(cm, spec, season, total, avatar_src, root=None):
    """His slot: the mini (a link to #ryno) and the full card. avatar_src is the same file in every season (HOLIDAY)."""
    types = [x["name"] for x in spec["types"]]
    ty = spec["types"][types.index(TYPE)]
    art = ART.get(season)
    pk = art["particles"] if art else ty["particles"]
    cls = f"t{types.index(TYPE)} lead" + (f" g-{STEM}" if art else "") + " holo"
    return (f'<div class="slot {cls}"><i class="o" id="{STEM}"></i><i class="c" id="m-{STEM}"></i><div class="card">'
            f'<a class="open" href="#{STEM}"><span class="art {pk}"><img src="{avatar_src}" width="112" height="112" alt=""></span>'
            f'<span class="nm"><b>{NAME}</b><span class="ml">{cm.icon(ty["icon"])}CEO</span>'
            f'<span class="hu">Human, not a bot</span><span class="bl">{e(BLURB)}</span></span></a>'
            f'<div class="body"><a class="cl" href="#m-{STEM}" aria-label="Close"></a>'
            f'<p class="ty"><b>{TYPE}</b></p><p class="ow"><b>The owner</b> · a person, so no XP or level</p>'
            f'<ul class="mv">{moves(cm, facts(root))}</ul><p class="wr"><span>{e(WEAK)}</span><span>{e(RESISTS)}</span><span>{e(HANDS_OFF)}</span></p>'
            f'<p class="ft">One of one<span class="sn">00/{total}</span></p>'
            f'<p class="fl">{e(FLAVOUR)}</p><p class="lk"><a class="sh" href="{STEM}/">Character sheet</a>{X_LINK}</p></div></div></div>')


def _day(ts):
    m, d = ts[5:7], ts[8:10]
    return f"{int(m)}/{int(d)}"


def sheet(repo, total, next_html, root=None):
    """His character sheet, in the same layout as today's role sheets (site/style.css only)."""
    f = facts(root)
    dec, ovr = load("ceo_decisions.json", root), load("ceo_overrides.json", root)
    data = lambda n: f'<a href="{repo}/blob/main/data/{n}">{n}</a>'
    pw = "".join(f'<li><strong>{e(name)}</strong>: {e(line)} <span class="meta">{f[rec]} {unit[0 if f[rec] == 1 else 1]} on record</span></li>'
                 for _, name, line, rec, unit in MOVES)
    yes = "".join(f'<li><time datetime="{x["applied_at"][:10]}">{_day(x["applied_at"])}</time> <a href="{e(x["evidence"])}">PR #{x["pr"]}</a> '
                  f'{e(chr(8220) + x["quote"] + chr(8221)) if x["quote"] else "He added the label himself on GitHub."} '
                  f'<span class="meta">label by {"the Assistant, after his yes in chat" if x["applied_by"] == "Executive Assistant" else "Ryno"}</span></li>'
                  for x in reversed(dec))
    ov = "".join(f'<li><time datetime="{x["at"][:10]}">{_day(x["at"])}</time> {e(chr(8220) + x["quote"] + chr(8221))} '
                 f'<span class="meta">up to {x["max_prs"]} PRs, named work only, ended 11:59 PM ET that day</span></li>' for x in reversed(ovr))
    return (f'<section class="sheet card" style="border-top:4px solid #b8860b"><img class="av" src="../../assets/avatars/ceo.svg" width="96" height="96" alt="">'
            f'<div><p class="title">CEO · human, not a bot</p><p class="lvl">The owner · one of one, 00/{total}</p>'
            f'<p>{e(FLAVOUR)}</p><p><a href="../#{STEM}">See his card</a> · {X_LINK}</p></div></section>'
            f'<h2>Powers</h2><ul>{pw}</ul>'
            f'<p class="meta">Weak to {e(WEAK)}. Resists {e(RESISTS)}. Hands off to {e(HANDS_OFF)}.</p>'
            f'<h2>Final yes</h2><p class="meta">Only Ryno\'s yes lets a change that loosens a safety check through. '
            f'The Assistant adds the label only after his yes in chat, quoted on the PR.</p><ul class="worklist">{yes}</ul>'
            f'<h2>Overrides</h2><p class="meta">Each lifts the daily PR limit for named work, for that day only.</p><ul class="worklist">{ov}</ul>'
            f'<h2>The human</h2><p>Ryno is a person, not a Grok Bot. He owns Slopworks and sets its direction. He doesn\'t sign off routine work: '
            f'bots review and merge each other\'s. The team pings him only for a real disagreement or a safety case.</p>'
            f'<p class="meta">The rhino is his look all year. On holidays only his card\'s background changes.</p>'
            f'<p class="meta">Counted at build time from {data("ceo_decisions.json")}, {data("ceo_overrides.json")} and {data("ideas.json")} '
            f'({f["decisions"]} calls decided by the CEO). Nothing typed by hand.</p>'
            f'<p><a href="../">Back to the team</a> · <a href="../../how/">Where the human decides</a></p>' + next_html)
