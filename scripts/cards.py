"""Team trading cards (Ryno, 2026-10-20 11:51, 11:53 AM and 12:18 PM ET: "Lock this design, have Comms polish the wording").

The Team page shows a grid of small cards (Variant B). Tapping one opens the full card (Variant A) with CSS :target only:
no script. Each role has a real-world job type (data/cards.json) that sets the frame colour, icon and the light, moving
art-window motif. In a holiday month whose look Ryno approved (scripts/avatars.py season_for, data/calendar.json), the art
window shows the role's costume scene instead. Every number comes from data/xp_ledger.json and data/progression.json.

Badge emblems are a hook only (badges=None): the badge rollout is held, so no badge row renders until it ships.
"""
import html, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
e = lambda s: html.escape(str(s), quote=False)
P = "i-"  # sprite ids are prefixed so they can't clash with role anchors such as #forge (Game Master, v2 notes); short to save bytes

ICONS = {
 "briefcase": "M-6-2.5h12v8h-12zM-2.5-2.5v-2.5h5v2.5M-6 1h12",
 "clipboard": "M-4.5-4.5h9v11h-9zM-2-6h4v2.5h-4zM-2 0h4M-2 3h4",
 "magnifier": "M-1.5-6a4.5 4.5 0 1 0 .1 0M1.8 1.8l4.2 4.2",
 "gear": "M0-2.5a2.5 2.5 0 1 0 .1 0M0-6.5v2M0 4.5v2M-6.5 0h2M4.5 0h2M-4.6-4.6l1.4 1.4M3.2 3.2l1.4 1.4M-4.6 4.6l1.4-1.4M3.2-3.2l1.4-1.4",
 "seal": "M0-6.5l1.8 1.3 2.2-.1.7 2.1 1.8 1.3-.7 2.1.7 2.1-1.8 1.3-.7 2.1-2.2-.1L0 6.5l-1.8-1.3-2.2.1-.7-2.1-1.8-1.3.7-2.1-.7-2.1 1.8-1.3.7-2.1 2.2.1zM-2.5 0l1.7 1.7 3.3-3.4",
 "lock": "M-5-1h10v7.5h-10zM-3-1v-2.5a3 3 0 0 1 6 0v2.5M0 2v1.5",
 "nib": "M0-6.5l4.5 6-4.5 6.5-4.5-6.5zM0 1.5v-8M0 1.5a.5.5 0 1 0 .1 0",
 "megaphone": "M-6-2v4h2.5l6.5 4v-12l-6.5 4zM-3.5 2l1 4.5M4.8-2.2a3 3 0 0 1 0 4.4",
 "chart": "M-6 6h12M-6 6v-12M-4 3l3-3.5 2.5 2 4-5",
 "people": "M-3-2.5a2.2 2.2 0 1 0 .1 0M3.2-3.5a1.9 1.9 0 1 0 .1 0M-6.5 5.5c.5-3 2-4.5 3.5-4.5s3 1.5 3.5 4.5M1.5 1.8c.6-1.3 1.2-1.8 1.8-1.8 1.3 0 2.6 1.3 3.2 4",
 "book": "M-6-5h5c.7 0 1 .4 1 1v10c0-.7-.4-1-1-1h-5zM6-5h-5c-.7 0-1 .4-1 1v10c0-.7.4-1 1-1h5z",
 "merge": "M-3-3.5v8M-3 2q0-4.5 6-4.5M-3-5.5a1.5 1.5 0 1 0 .1 0M3-4a1.5 1.5 0 1 0 .1 0",
 "check": "M-4.5 0l3 3 6-6.5",
 "flask": "M-2-5.5h4M-1-5.5v3l-4 8h10l-4-8v-3",
 "rocket": "M0-6.5c3 2 3.5 6 2 9.5h-4c-1.5-3.5-1-7.5 2-9.5zM-2 3l-2.5 3M2 3l2.5 3",
 "doc": "M-4-6h5l3 3v9h-8zM-2 0h4M-2 3h4",
 "wrench": "M5.5-3.5a3.5 3.5 0 0 1-5 3.2L-4 4.2a1.2 1.2 0 0 1-1.7-1.7l4.5-4.5a3.5 3.5 0 0 1 4.6-4.6L1.3-4.5l2.8 2.8z",
 "block": "M-4.6-4.6l9.2 9.2M0-6.5a6.5 6.5 0 1 0 .1 0",
 "eye": "M-6.5 0q6.5-7.5 13 0q-6.5 7.5-13 0zM0-2a2 2 0 1 0 .1 0",
 "map": "M-6-4l4-2 4 2 4-2v10l-4 2-4-2-4 2zM-2-6v10M2-4v10",
 "quote": "M-5-3.5h10v6h-5l-3 3v-3h-2z",
 "scale": "M0-6v12M-5-3.5h10M-5-3.5l-2 4h4zM5-3.5l-2 4h4zM-3 6h6",
}
UI = {  # CSS-mask icons for the card chrome
 "lv": "M-4.5 1l4.5-4.5 4.5 4.5M-4.5 5.5l4.5-4.5 4.5 4.5",
 "set": "M-5-4h7v10h-7zM-2.5-6.5h7v10",
 "weak": "M-1-6.5L1.5-1-1.5 1 1 6.5",
 "resist": "M0-6l5 2v3c0 4-3 6-5 7-2-1-5-3-5-7v-3z",
 "hand": "M-6.5 0h11M.5-4.5L5 0 .5 4.5",
 "sheet": "M-4.5-6h9v12h-9zM-2-3.5h4v3h-4zM-2 2h4M-2 4h4",  # character sheet (Ryno, Oct 20 7:48 PM ET: the link becomes an icon)
 "x": "M-5.5-5.5h3.2l7.8 11h-3.2zM5-5.5L-5 5.5",  # X mark for his profile link (7:45 PM ET)
 "hv": "M-1.5-5.5a2.3 2.3 0 1 0 .1 0M-6 6c.3-3.2 2-4.8 4.5-4.8 1.3 0 2.3.4 3 1M1 3.8l1.7 1.7 3.6-3.8",  # human verified: a person and a check, original (Ryno, 8:03 PM ET)
}
TEX = {"stripes": "repeating-linear-gradient(135deg,#fff2 0 4px,#0000 4px 12px)", "lines": "repeating-linear-gradient(0deg,#0002 0 1px,#0000 1px 7px)",
       "rings": "repeating-radial-gradient(circle at 50% 0,#fff2 0 2px,#0000 2px 12px)", "grid": "linear-gradient(#fff2 1px,#0000 1px) 0 0/12px 12px,linear-gradient(90deg,#fff2 1px,#0000 1px) 0 0/12px 12px",
       "checker": "repeating-conic-gradient(#fff2 0 25%,#0000 0 50%) 0 0/12px 12px", "metal": "linear-gradient(160deg,#fff5,#0000 35%,#fff3 55%,#0003)",
       "dots": "radial-gradient(#fff3 1.5px,#0000 2px) 0 0/10px 10px"}
GEM = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 10'%3E%3Cpath d='M5 0l4.3 2.5v5L5 10 .7 7.5v-5z'/%3E%3C/svg%3E"
SH = {'pr_merged': ('PR', 'PRs'), 'signoff': ('sign-off', 'sign-offs'), 'ci_test_added': ('test', 'tests'), 'pitch_shipped': ('shipped', 'shipped'),
      'research_accepted': ('report', 'reports'), 'aar_fix': ('fix', 'fixes'), 'block_upheld': ('block', 'blocks'), 'deploy_check': ('check', 'checks')}
CSS = (Path(__file__).with_name("cards.css")).read_text().replace("GEM", GEM).replace("\n", "")
# The badge row's style ships with the badges (held): no unused CSS on the Team page until then (page budget, v5).
BADGE_CSS = ".bd{display:flex;flex-wrap:wrap;gap:.5rem;margin:.3rem 0}.bd span{display:inline-flex;align-items:center;gap:.15rem;font-size:.8125rem;font-weight:700}.bd img{width:24px;height:24px}"
MAX_LINE = 8  # words per move line (Comms)


def load():
    return json.loads((ROOT / "data/cards.json").read_text())


def rarity(level, spec):
    """(tier 1-4, name) from the level; the tiers are data/cards.json rarity, lowest first."""
    tiers = [r for r in spec["rarity"] if r["from_level"] <= level]
    return len(tiers), tiers[-1]["name"]


def _shift(d, dx):
    """The path moved right by dx: only absolute M and L carry x, every other command in UI is relative."""
    out, cmd, k = [], "", 0
    for t in re.findall(r"[A-Za-z]|-?(?:\d+\.?\d*|\.\d+)", d):
        if t.isalpha():
            assert t in "MLlhvczasq", t  # only M and L are absolute
            cmd, k = t, 0
            out.append(t)
            continue
        n = float(t) + (dx if cmd in "ML" and k % 2 == 0 else 0)
        k += 1
        n = f"{n:g}".replace("0.", ".") if abs(n) < 1 else f"{n:g}"
        out.append(n if out[-1].isalpha() or n.startswith("-") else " " + n)
    return "".join(out)


def strip():
    """The UI icons, then the job-type icons, as one mask strip, 14 units per slot (page budget, Oct 20 3:54 PM ET: room for
    the CEO card; 7:48 PM ET: the type icon moved here from the sprite so every card's markup is shorter)."""
    ds = list(UI.values()) + list(ICONS.values())  # 7:48 PM ET and 8:06 PM ET: every card icon is a slot here, no sprite
    paths = "<path d='" + "".join(_shift(d, 14 * i) for i, d in enumerate(ds)) + "'/>"  # one path: same stroke for all
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='-7 -7 {14 * len(ds)} 14' fill='none' stroke='#000' stroke-width='1.7'"
           f" stroke-linecap='round' stroke-linejoin='round'>{paths}</svg>")
    return "data:image/svg+xml," + svg.replace("<", "%3C").replace(">", "%3E").replace("#", "%23")


def slot(k):
    return len(UI) + list(ICONS).index(k)


def icon(k):
    """A move icon: an empty box whose ::before draws slot --x of the mask strip (decorative; the move name says it)."""
    return f'<i style="--x:{slot(k)}"></i>'


def css(spec, season, stems, badges=False):
    types = list(spec["types"])
    t = "".join(f'.t{i}{{--a:{v["colour"]};--b:{v["tint"]};--m:{v["motif"]};--y:{slot(v["icon"])}}}' for i, v in enumerate(types))
    for k in ("texture", "particle_colour"):  # a value shared by several types is written once (page budget)
        vals = {}
        for i, v in enumerate(types):
            vals.setdefault(v[k], []).append(f".t{i}")
        t += "".join(f'{",".join(s)}{{--{k[0]}:{TEX[x] if k == "texture" else x}}}' for x, s in vals.items())
    for n, s in stems.items():
        art = spec["roles"][n].get("art", {}).get(season)
        if art:
            t += f'.g-{s}{{--g:{art["scene"]};--p:{art["particle_colour"]}}}'
    sel = {"lv": ".lv::before", "set": ".sn::before", "weak": ".wr :nth-child(1)::before",
           "resist": ".wr :nth-child(2)::before", "hand": ".wr :nth-child(3)::before", "sheet": ".sh::before",
           "x": ".xl::before", "hv": ".hu::before", "type": ".ml::before", "move": ".mv i[style]::before"}
    # One strip, each rule picks its slot (--x) at its size (--s, 16px by default; the link icons 20px).
    t += ",".join(sel.values()) + f'{{content:"";width:var(--s);height:var(--s);flex:none;background:var(--a);mask:url("{strip()}") calc(var(--x,0)*-1*var(--s)) 0/calc({len(UI) + len(ICONS)}*var(--s)) var(--s) no-repeat}}'
    t += "".join(f'{sel[k]}{{--x:{i}}}' for i, k in enumerate(UI) if i) + ".ml::before{--x:var(--y)}"
    return t + CSS + (BADGE_CSS if badges else "")


def card(n, i, total, stem, spec, season, xp, level, lv, nxt, kinds, avatar_src, badges=None, jb=""):
    """One slot: the mini (a link to #stem) and the full card body. badges: {family: count} once the badge engine ships."""
    r = spec["roles"][n]
    tl = [x["name"] for x in spec["types"]]
    ty = next(x for x in spec["types"] if x["name"] == r["type"])
    rk, rname = rarity(level, spec)
    art = r.get("art", {}).get(season)
    pct = 100 if not nxt else int(100 * (xp - lv["xp"]) / (nxt["xp"] - lv["xp"]))
    cls = f't{tl.index(r["type"])} r{rk}' + (f' g-{stem}' if art else "") + (" holo" if rk >= 3 else "")
    pk = art["particles"] if art else ty["particles"]
    mv = ""
    for m in r["moves"]:
        c = kinds.get(m["stat"]) if m["stat"] else None
        st = f'<em>{c}<small> {SH[m["stat"]][0 if c == 1 else 1]}</small></em>' if c else ""
        mv += f'<li>{icon(m["icon"])}<b>{e(m["name"])}</b>{st}<span>{e(m["line"])}</span></li>'
    bd = ('<p class="bd">' + "".join(f'<span><img src="{avatar_src.rsplit("avatars/", 1)[0]}badges/{f}.svg" width="24" height="24" alt="{e(f.capitalize())} badges:">{c}</span>'
                                     for f, c in badges.items()) + "</p>") if badges else ""
    fl = r["flavour"].get(season) or r["flavour"]["normal"]
    return (f'<div class="slot {cls}"><a class="o" id="{stem}" href="#m-{stem}" tabindex="-1" aria-hidden="true"></a><i class="c" id="m-{stem}"></i><div class="card">'
            f'<a class="open" href="#{stem}"><span class="art {pk}"><img src="{avatar_src}" width="112" height="112" alt=""></span>{jb}'
            f'<span class="nm"><b>{e(n)}</b><span class="ml" title="{e(r["type"])}">Lv <span>{level}</span></span></span></a>'
            f'<div class="body"><a class="cl" href="#m-{stem}">Close</a><p class="ty"><b>{e(r["type"])}</b></p>'
            f'<p class="lv" style="--w:{pct}%">{e(lv["name"])}</p>'
            f'<ul class="mv">{mv}</ul>'
            f'{bd}<p class="ft">{e(rname)}<span class="sn">{i:02d}/{total}</span></p>'
            f'<p class="fl">{e(fl)}</p><a class="sh" title="Character sheet" href="{stem}/">Character sheet</a></div></div></div>')


def errors(spec=None, roles=None):
    """Card data rules (code first): every role has a card, a known type and icons, short move lines, no typed numbers."""
    spec = spec or load()
    out, names = [], {t["name"] for t in spec["types"]}
    for t in spec["types"]:
        if t["icon"] not in ICONS or t["texture"] not in TEX:
            out.append(f"data/cards.json type {t['name']}: unknown icon or texture")
    for n, r in spec["roles"].items():
        if r["type"] not in names:
            out.append(f"data/cards.json {n}: type {r['type']} isn't in types")
        for m in r["moves"]:
            if m["icon"] not in ICONS:
                out.append(f"data/cards.json {n}: unknown icon {m['icon']}")
            if len(m["line"].split()) > MAX_LINE:
                out.append(f"data/cards.json {n}: move line over {MAX_LINE} words: {m['line']}")
            if m["stat"] and m["stat"] not in SH:
                out.append(f"data/cards.json {n}: unknown stat {m['stat']}")
        if "normal" not in r["flavour"]:
            out.append(f"data/cards.json {n}: no normal-season flavour line")
    if roles is not None:
        out += [f"data/cards.json: no card for {n}" for n in roles if n not in spec["roles"]]
    return out
