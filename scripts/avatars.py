#!/usr/bin/env python3
"""Each role's avatar (v2): a soft single-color blob with two slanted pill eyes and a tiny job badge.
Transparent, flat, animated with inline CSS only (idle squish, staggered blinks), static under
prefers-reduced-motion. Inspired by the Grok Bot app style, not copied. Changes need Polish + Shield review.

Seasonal sets (Ryno, 2026-10-19 9:30 PM ET: "Ship tomorrow but make them see-through, no tiles"; 9:52 PM ET: full
months): for all of October each role becomes its Halloween character and for all of December its winter one, but only once
Ryno's yes for that theme is done on data/calendar.json (9:56 PM ET: "Yes, holiday looks wait for my yes before switching
on"); the rest of the year, or with no yes, it's the blob. Same file names, picked by the ET date when this script runs
(the daily run). Every file also gets a still copy in still/ (no <style>, the neutral pose) for long lists like Team chat.
  avatars.py                     write the set for today's ET date
  avatars.py --date 2026-10-20   write the set for that date
  avatars.py --check             exit 1 unless the committed files are the set for today's ET date"""
import json, math, re, sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cal as cal_mod  # noqa: E402  data/calendar.json helpers: active_set() is the one switch

OUT = Path(__file__).resolve().parent.parent / "site/assets/avatars"
# role: (color, shape, params, badge, why)
ROLES = {
    "coordinator": ("#8250df", "wave", (5, .13), "arrow", "a five-point star blob that points the way"),
    "sketch": ("#0969da", "drop", (-2.3,), "pencil", "Scout: a droplet that leans forward"),
    "lens": ("#1a7f37", "wave", (0, 0), "check", "Verify: a calm round blob"),
    "shield": ("#cf222e", "squircle", (4,), "shield", "a sturdy squircle"),
    "forge": ("#bc4c00", "wave", (7, .07), "bolt", "a cookie-edged builder"),
    "pixel": ("#d63384", "cloud", (4,), "square", "a four-puff cloud"),
    "core": ("#9aa5b1", "wave", (2, .09), "ring", "a bean-shaped data blob"),
    "trial": ("#bf8700", "wave", (8, .05), "flask", "a puffy, careful tester"),
    "polish": ("#bf3989", "cloud", (5,), "sparkle", "a flower-ish puff"),
    "advisor": ("#7d8fe0", "egg", (.12,), "book", "an egg that's seen it all"),
    "atlas": ("#1b7c83", "wave", (6, .11), "globe", "a six-bump cookie"),
    "sweep": ("#218bff", "squircle", (2.6,), "wave", "a soft rounded square"),
    "analyst": ("#a371f7", "wave", (4, .1), "bars", "a four-lobe clover"),
    "scoutmaster": ("#6fa82b", "wave", (9, .05), "target", "a gear-edged strategist that looks ahead"),
    "critic": ("#f0883e", "wave", (3, .12), "bang", "a three-cornered challenger"),
    "advocate": ("#3fb8af", "cloud", (6,), "heart", "a six-puff blob that speaks for readers"),
    "librarian": ("#c9a26b", "drop", (1.6,), "stack", "a settled droplet that keeps the record"),
    "ceo": ("#d4a72c", "drop", (-0.8,), "star", "the human CEO: drawn as FIXED['ceo'] below, the same in every set"),
    "comms": ("#0aa5c4", "wave", (10, .045), "quote", "a scalloped speech burst that says only what's true"),
    "gamemaster": ("#ff8fab", "squircle", (7,), "d20", "a boxy dice-shaped blob that keeps score fairly"),
    "strategy": ("#e5534b", "cloud", (7,), "compass", "a seven-puff cloud that looks a month ahead"),
    "assistant": ("#768390", "egg", (-.1,), "check", "a tidy egg that keeps the CEO's record straight"),
}
BADGE = {
    "arrow": "M0-5l4 9-4-2-4 2z", "pencil": "M-4 4l1-4 6-6 3 3-6 6z", "check": "M-4 0l3 3 5-6",
    "shield": "M0-5l5 2v2c0 4-3 6-5 7-2-1-5-3-5-7v-2z", "bolt": "M1-6l-5 7h4l-1 5 5-7h-4z",
    "square": "M-4-4h8v8h-8z", "ring": "M-4 0a4 4 0 1 0 8 0a4 4 0 1 0-8 0", "flask": "M-2-5h4M-1-5v3l-4 7h10l-4-7v-3",
    "sparkle": "M0-6l1.5 4.5L6 0l-4.5 1.5L0 6l-1.5-4.5L-6 0l4.5-1.5z", "book": "M-5-4h4v8h-4zM1-4h4v8h-4z",
    "globe": "M-5 0h10M0-5c-3 3-3 7 0 10c3-3 3-7 0-10", "wave": "M-5 1q2.5-4 5 0t5 0", "bars": "M-3 4v-3M0 4v-8M3 4v-5",
    "target": "M-4 0a4 4 0 1 0 8 0a4 4 0 1 0-8 0M0 0h.1", "bang": "M0-5v5M0 4v.5",
    "heart": "M0 4.5l-4.5-4.5a2.6 2.6 0 0 1 4.5-3.5a2.6 2.6 0 0 1 4.5 3.5z", "stack": "M-5 3.5h10M-4 0h8M-3-3.5h6",
    "quote": "M-5-3.5h10v6h-5l-3 3v-3h-2z", "compass": "M0-5l2 5-2 5-2-5zM-5 0h1M4 0h1",
    "d20": "M0-5.5l4.8 2.75v5.5L0 5.5l-4.8-2.75v-5.5zM0-2.5l2.6 4.3h-5.2z",
    "star": "M0-5.5l1.6 3.4 3.7.4-2.8 2.5.8 3.7L0 2.6-3.3 4.5l.8-3.7-2.8-2.5 3.7-.4z",
}
STROKED = {"target", "bang", "stack", "ring", "check", "flask", "globe", "wave", "bars"}
STROKED |= {"d20"}  # Game Master badge (added, nothing removed)


def radius(shape, p, t):
    if shape == "wave":
        k, a = p
        return 1 + a * math.cos(k * t - math.pi / 2)
    if shape == "drop":
        return 1 + .3 * max(0, math.cos(t - p[0])) ** 3
    if shape == "cloud":
        return .86 + .16 * abs(math.cos(p[0] * t / 2))
    if shape == "egg":
        return 1 - p[0] * math.sin(t)
    if shape == "squircle":
        n = p[0]
        return 1 / (abs(math.cos(t)) ** n + abs(math.sin(t)) ** n) ** (1 / n) * .92


def blob(shape, p, cx=50, cy=56, R=34, n=28):
    pts = [(cx + R * radius(shape, p, 2 * math.pi * i / n) * math.cos(2 * math.pi * i / n),
            cy + R * radius(shape, p, 2 * math.pi * i / n) * math.sin(2 * math.pi * i / n)) for i in range(n)]
    f = lambda v: f"{v:.0f}"
    d = f"M{f(pts[0][0])} {f(pts[0][1])}"
    for i in range(n):  # Catmull-Rom to cubic Bezier, closed
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f"C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(p2[0])} {f(p2[1])}"
    return d + "Z"


def shade(hexc, k=.72):
    r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % (int(r * k), int(g * k), int(b * k))


def svg(i, name, color, shape, p, badge, why):
    bob, blink, delay = 3.6 + (i % 4) * .5, 4 + (i % 3), (i * .7) % 4
    glyph = (f'<path d="{BADGE[badge]}" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
             if badge in STROKED else f'<path d="{BADGE[badge]}" fill="#fff"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" aria-label="{name.capitalize()}: {why}">'
            f'<style>.b{{animation:q {bob}s ease-in-out infinite;transform-origin:50px 90px}}'
            f'.e{{animation:k {blink}s {delay:.1f}s infinite;transform-box:fill-box;transform-origin:center}}'
            f'@keyframes q{{50%{{transform:translateY(-3px) scale(1.03,.97)}}}}'
            f'@keyframes k{{0%,92%,100%{{transform:scaleY(1)}}96%{{transform:scaleY(.15)}}}}'
            f'@media(prefers-reduced-motion:reduce){{.b,.e{{animation:none}}}}</style>'
            f'<g class="b"><path d="{blob(shape, p)}" fill="{color}"/>'
            f'<g transform="rotate(-18 44 40)"><rect class="e" x="41" y="33" width="6" height="13" rx="3" fill="#1b1f24"/></g>'
            f'<g transform="rotate(-18 60 40)"><rect class="e" x="57" y="33" width="6" height="13" rx="3" fill="#1b1f24"/></g>'
            f'<g transform="translate(80 82)"><circle r="10" fill="{shade(color)}"/>{glyph}</g></g></svg>\n')


# ---------- seasonal sets ----------
ET = ZoneInfo("America/New_York")
CALENDAR = Path(__file__).resolve().parent.parent / "data/calendar.json"
SEASONS = {"halloween": ((10, 1), (10, 31)), "winter": ((12, 1), (12, 31))}  # full months (Ryno, Oct 19 9:52 PM ET)
EYE = "#1b1f24"  # eyes and cut-outs: the blob's own eye colour, the same in both themes
BAND = (.142, .268)  # relative luminance with 3:1 against both page backgrounds (#F6F5F1, #141418) and both card colours (#FFFFFF, #1C1C22)
RIM_W = 4  # half shows outside the shape: a soft same-hue edge, only on shapes too light (or dark) for one theme


def in_window(d):
    """'halloween' Oct 1-31, 'winter' Dec 1-31, else 'normal' (inclusive, by calendar date). The date alone; see season_for."""
    md = (d.month, d.day)
    return next((n for n, (a, b) in SEASONS.items() if a <= md <= b), "normal")


def load_calendar():
    return json.loads(CALENDAR.read_text())


def season_for(d, cal=None):
    """The set to show on `d`: a holiday set only when `d` is in its window AND that year's theme on data/calendar.json
    has its "Ryno's yes" (ceo-yes) event marked done, the same switch as cal.active_set(). Otherwise the blob.
    (Ryno, 2026-10-19 9:56 PM ET: "Yes, holiday looks wait for my yes before switching on". Only the EA marks a
    ceo-yes done, quoting Ryno's words.)"""
    w = in_window(d)
    if w == "normal":
        return w
    return w if cal_mod.active_set(load_calendar() if cal is None else cal, d) == w else "normal"


def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= .03928 else ((x + .055) / 1.055) ** 2.4 for x in c]
    return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]


def ratio(a, b):
    a, b = lum(a), lum(b)
    return (max(a, b) + .05) / (min(a, b) + .05)


def _mix(h, k, to=0):
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(round(v + (to - v) * k) for v in (r, g, b))


def _into(h, target):
    """The same hue moved toward black (or white) until its luminance reaches target."""
    to = 0 if lum(h) > target else 255
    for k in range(1, 101):
        c = _mix(h, k / 100, to)
        if (lum(c) <= target) if to == 0 else (lum(c) >= target):
            return c
    return c


def fit(f):
    """(fill, rim): near-band colours shift a little into the band; far ones keep their colour and get a rim."""
    L = lum(f)
    if BAND[0] <= L <= BAND[1]:
        return f, None
    if BAND[1] < L <= .34:
        return _into(f, .262), None
    if .09 <= L < BAND[0]:
        return _into(f, .15), None
    return f, _into(f, .24 if L > BAND[1] else .16)


def _rim(r):
    return f' stroke="{r}" stroke-width="{RIM_W}" paint-order="stroke"' if r else ""


def _paint(f, inner):
    if inner or f == EYE:
        return f'fill="{f}"'
    f, r = fit(f)
    return f'fill="{f}"{_rim(r)}'


def P(d, f, inner=False): return f'<path d="{d}" {_paint(f, inner)}/>'
def E(cx, cy, rx, ry, f, inner=False): return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" {_paint(f, inner)}/>'
def C(cx, cy, r, f, inner=False): return f'<circle cx="{cx}" cy="{cy}" r="{r}" {_paint(f, inner)}/>'
def R(x, y, w, h, rx, f, inner=False): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" {_paint(f, inner)}/>'


def S(d, c, w, inner=False, extra=""):
    """A stroked line; out-of-band lines get a wider same-hue line under them."""
    line = lambda col, wd: f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{wd}"{extra}/>'
    if inner or c == EYE:
        return line(c, w)
    c, r = fit(c)
    return (line(r, w + RIM_W) if r else "") + line(c, w)


def PS(d, f, w):
    """A filled shape with a same-colour stroke (soft corners), plus a rim when needed."""
    f, r = fit(f)
    under = f'<path d="{d}" fill="{r}" stroke="{r}" stroke-width="{w + RIM_W}"/>' if r else ""
    return under + f'<path d="{d}" fill="{f}" stroke="{f}" stroke-width="{w}"/>'


def M(s): return f'<g transform="matrix(-1 0 0 1 100 0)">{s}</g>'
def G(c, s): return f'<g class="{c}">{s}</g>'


def star(cx, cy, r, ri):
    return "M" + "L".join(f"{cx + (r if k % 2 == 0 else ri) * math.cos(-math.pi / 2 + k * math.pi / 5):.1f} "
                          f"{cy + (r if k % 2 == 0 else ri) * math.sin(-math.pi / 2 + k * math.pi / 5):.1f}" for k in range(10)) + "Z"


# Motions: the pose at 25% (L) and 75% (R), the neutral pose at 0/50/100%, and the squash at each. Eyes slide toward the
# turn and go from tall pills to circles, like a head turning.
def dance(a=10, sq=.08, dur=3.0):
    return dict(L=f"rotate(-{a}deg)", R=f"rotate({a}deg)", N="rotate(0)", o="50px 90px", qN=(1 - sq / 2, 1 + sq / 2), qS=(1 + sq, 1 - sq), dur=dur)
def floaty(a=6, y=5, dur=3.6):
    return dict(L=f"translateY(-{y}px) rotate(-{a}deg)", R=f"translateY(-{y}px) rotate({a}deg)", N="translateY(0)", o="50px 60px", qN=(.98, 1.03), qS=(1.04, .96), dur=dur)
def hop(a=5, y=8, dur=2.4):
    return dict(L=f"translateY(-{y}px) rotate(-{a}deg)", R=f"translateY(-{y}px) rotate({a}deg)", N="translateY(0)", o="50px 90px", qN=(1.09, .9), qS=(.95, 1.07), dur=dur)
def swing(a=9, px=50, py=6, dur=3.2):
    return dict(L=f"rotate({a}deg)", R=f"rotate(-{a}deg)", N="rotate(0)", o=f"{px}px {py}px", qN=(.98, 1.02), qS=(1.03, .97), dur=dur)
def shuffle(x=5, a=4, dur=2.6):
    return dict(L=f"translateX(-{x}px) rotate({a}deg)", R=f"translateX({x}px) rotate(-{a}deg)", N="translateX(0)", o="50px 90px", qN=(.97, 1.04), qS=(1.06, .93), dur=dur)
def twinkle(a=8, s=1.07, dur=2.8):
    return dict(L=f"rotate(-{a}deg) scale({s})", R=f"rotate({a}deg) scale({s})", N="rotate(0) scale(1)", o="50px 56px", qN=(1, 1), qS=(1.03, .97), dur=dur)


def part(cls, dur, origin, frame, extra=""):
    """A part with its own loop (a tail wag, a wing flap), as CSS."""
    return f".{cls}{{animation:{cls} {dur}s ease-in-out infinite;transform-origin:{origin}{extra}}}@keyframes {cls}{{{frame}}}"


# Each costume: name, line (the role's own pick, in its words), body (shapes, back to front), eyes (cy, left x, right x,
# rx, ry), face (the colour the eyes sit on), motion, and optional css for its own moving parts.
HALLOWEEN = {
    "coordinator": dict(name="Will-o'-the-wisp", line="A floating light that leads the way, in the right order.",
        body=G("fl", P("M54 14C58 30 76 40 76 62C76 79 64 90 50 90C36 90 24 79 24 62C24 46 36 40 40 26C44 36 48 38 48 30C48 24 50 18 54 14Z", "#9d7cf5")
                     + P("M50 44C60 54 65 60 65 70C65 80 58 87 50 87C42 87 35 80 35 70C35 60 42 56 50 44Z", "#ddd3ff", True)),
        eyes=(70, 45, 55, 3, 5.6), face="#ddd3ff", m=floaty(5, 5, 3.4),
        css=part("fl", 1.7, "50px 88px", "50%{transform:skewX(-5deg) scaleY(1.04)}")),
    "sketch": dict(name="Wizard", line="Every plan starts as a spell, drafted in pencil first.",
        body=E(50, 74, 25, 17, "#3b82e6") + G("tp", P("M30 58Q40 48 45 30Q49 14 64 10Q56 20 58 34Q61 48 70 58Z", "#7663ee"))
             + R(22, 55, 56, 7, 3.5, "#7663ee") + P(star(54, 38, 4.6, 2), "#f2c14e", True),
        eyes=(74, 44, 56, 3.2, 5.6), face="#3b82e6", m=dance(11, .08, 3.1),
        css=part("tp", 3.1, "50px 58px", "25%{transform:skewX(8deg)}75%{transform:skewX(-8deg)}")),
    "lens": dict(name="Frankenstein's monster", line="Checks every stitch holds before anything walks out the door.",
        body=R(18, 64, 9, 8, 2, "#9aa3b0") + R(73, 64, 9, 8, 2, "#9aa3b0") + R(25, 28, 50, 60, 15, "#43a050")
             + P("M25 46V38Q25 26 37 26H63Q75 26 75 38V46L69 41L63 46L57 41L50 46L43 41L37 46L31 41Z", "#5f6575")
             + S("M60 76h10M62 73v6M66 73v6", EYE, 1.6),
        eyes=(61, 43, 57, 3.8, 6.6), face="#43a050", m=dance(6, .11, 2.8)),
    "shield": dict(name="Vampire", line="Nothing comes in uninvited. Nothing personal goes out.",
        body=P("M50 30C70 30 80 44 82 60L86 90Q68 84 50 90Q32 84 14 90L18 60C20 44 30 30 50 30Z", "#5c6482")
             + P("M31 46L14 22L40 36Z", "#e5484d") + M(P("M31 46L14 22L40 36Z", "#e5484d"))
             + E(50, 58, 17, 21, "#ece4f2", True) + P("M33 52Q33 37 50 37Q67 37 67 52Q58 45 50 54Q42 45 33 52Z", "#5c6482", True),
        eyes=(64, 44, 56, 3, 5.4), face="#ece4f2", m=dance(8, .07, 3.4)),
    "forge": dict(name="Pumpkin", line="Carved exactly to the locked plan.",
        body=G("st", P("M47 38C47 29 50 22 57 17L62 21C56 26 54 31 54 38Z", "#6b6b78"))
             + E(35, 63, 18, 23, "#f26b0f") + E(65, 63, 18, 23, "#f26b0f") + E(50, 61, 20, 27, "#f26b0f"),
        eyes=(64, 43, 57, 4, 7.2), face="#f26b0f", m=dance(12, .09, 3.0),
        css=part("st", 1.5, "50px 38px", "50%{transform:rotate(9deg)}")),
    "trial": dict(name="Mummy", line="Wrapped head to toe in test tape.",
        body=R(28, 24, 44, 66, 20, "#efe6cf") + S("M32 36L68 33.5M31 46L69 48.5M31 77L69 75M32 84L68 86.5", EYE, 1.6)
             + G("tl", S("M68 69Q82 73 84 86", "#e0a400", 4.5)) + S("M29 69L69 67", "#e0a400", 4.5, True),
        eyes=(56, 43, 57, 3.6, 6.4), face="#efe6cf", m=shuffle(5, 4, 2.6),
        css=part("tl", 1.3, "68px 69px", "50%{transform:rotate(14deg)}")),
    "polish": dict(name="Witch", line="A little magic on every pixel.",
        body=E(50, 74, 25, 17, "#e05aa8") + G("tp", P("M32 58Q42 46 46 28Q48 16 34 8Q60 12 60 30Q62 46 68 58Z", "#8f62dc"))
             + R(18, 55, 64, 7, 3.5, "#8f62dc") + R(34, 50, 32, 5, 1.5, "#f2c14e", True),
        eyes=(74, 44, 56, 3.2, 5.6), face="#e05aa8", m=dance(14, .08, 2.9),
        css=part("tp", 2.9, "50px 58px", "25%{transform:skewX(10deg)}75%{transform:skewX(-10deg)}")),
    "advisor": dict(name="Friendly ghost", line="The ghost of lessons past, here to help.",
        body=G("gt", P("M22 88V54C22 34 34 22 50 22C66 22 78 34 78 54V88Q73 82 68 88Q63 94 58 88Q54 82 50 88Q46 94 42 88Q37 82 32 88Q27 94 22 88Z", "#eceefb")),
        eyes=(56, 43, 57, 4, 7.2), face="#eceefb", m=floaty(6, 6, 4.0),
        css=part("gt", 2, "50px 30px", "50%{transform:skewX(4deg)}")),
    "atlas": dict(name="Skeleton", line="Shows the bones of the build.",
        body=P("M50 22C68 22 78 34 78 50C78 60 72 66 68 68V78Q68 84 62 84H38Q32 84 32 78V68C28 66 22 60 22 50C22 34 32 22 50 22Z", "#ecebe4")
             + S("M42 74V84M50 74V84M58 74V84", EYE, 2) + P("M50 90L40 85V95ZM50 90L60 85V95Z", "#1b7c83"),
        eyes=(53, 42, 58, 5, 6.4), face="#ecebe4", m=dance(7, .06, 2.2)),
    "sweep": dict(name="Enchanted broom", line="Sweeps the site clean every night, on time and on budget.",
        body=R(47, 6, 6, 42, 3, "#a8743f") + R(37, 44, 26, 7, 2, "#218bff") + P("M38 50H62C70 64 76 78 78 90H22C24 78 30 64 38 50Z", "#eab54a")
             + S("M34 80L32 90M66 80L68 90M50 82V90", "#a8743f", 1.6, True),
        eyes=(67, 44, 56, 3, 5.4), face="#eab54a", m=swing(10, 50, 8, 2.8)),
    "analyst": dict(name="Spider", line="Counts every strand in the web.",
        body=S("M50 0V48", "#868b9e", 1.2) + G("lg", S("M37 56Q24 46 17 52M35 62Q21 58 15 66M36 68Q23 72 17 80M39 72Q30 82 26 90", "#8a63e8", 3.2)
             + M(S("M37 56Q24 46 17 52M35 62Q21 58 15 66M36 68Q23 72 17 80M39 72Q30 82 26 90", "#8a63e8", 3.2))) + E(50, 63, 16, 15, "#a371f7"),
        eyes=(64, 45, 55, 3, 5.6), face="#a371f7", m=swing(8, 50, 0, 3.4),
        css=part("lg", 1.2, "50px 63px", "50%{transform:scaleY(.9)}")),
    "scoutmaster": dict(name="Scarecrow", line="Watches the field for what's growing next.",
        body=P("M30 44L17 50L28 51L19 59L31 54Z", "#e8c34f") + M(P("M30 44L17 50L28 51L19 59L31 54Z", "#e8c34f")) + E(50, 62, 22, 25, "#d6b06e")
             + S("M34 80q4 4 8 0q4 4 8 0q4 4 8 0q4 4 8 0", EYE, 1.4) + E(50, 41, 32, 6, "#5e9e2a") + P("M36 41Q36 22 50 22Q64 22 64 41Z", "#5e9e2a"),
        eyes=(62, 43, 57, 3.6, 6.4), face="#d6b06e", m=dance(10, .05, 4.2)),
    "critic": dict(name="Devil's advocate", line="Plays devil's advocate, professionally.",
        body=G("tl", S("M70 80Q87 82 85 64", "#c4302b", 3.6) + P("M85 56L78 67L91 65Z", "#c4302b"))
             + P("M32 48Q23 34 30 22Q34 36 43 42Z", "#c4302b") + M(P("M32 48Q23 34 30 22Q34 36 43 42Z", "#c4302b")) + E(50, 65, 25, 24, "#f0883e"),
        eyes=(65, 43, 57, 3.6, 6.4), face="#f0883e", m=hop(5, 7, 2.3),
        css=part("tl", 1.15, "70px 80px", "50%{transform:rotate(-16deg)}")),
    "advocate": dict(name="Candy corn", line="Asks visitors which treats they actually want.",
        body=P("M50 20C58 20 80 70 78 84C76 92 24 92 22 84C20 70 42 20 50 20Z", "#fbf7ef")
             + '<clipPath id="k"><path d="M50 20C58 20 80 70 78 84C76 92 24 92 22 84C20 70 42 20 50 20Z"/></clipPath><g clip-path="url(#k)">'
             + R(0, 46, 100, 30, 0, "#e87a1c", True) + R(0, 76, 100, 30, 0, "#f6c445", True) + "</g>",
        eyes=(61, 44, 56, 3.2, 5.8), face="#e87a1c", m=hop(4, 9, 2.1)),
    "librarian": dict(name="Night owl", line="Up late keeping the record.",
        body=P("M26 42L29 22L41 32Q50 29 59 32L71 22L74 42C80 57 78 80 66 88Q50 94 34 88C22 80 20 57 26 42Z", "#c9a26b")
             + E(50, 76, 14, 12, "#ead6ae", True) + C(42, 54, 9, "#ead6ae", True) + C(58, 54, 9, "#ead6ae", True) + P("M47.5 64H52.5L50 68.5Z", "#b5781c", True),
        eyes=(54, 42, 58, 3.4, 5.6), face="#ead6ae", m=dance(15, .04, 3.8)),
    "comms": dict(name="Bat", line="Echolocation for exactly the right word.",
        body=G("wg", P("M40 56C30 40 14 36 5 44C11 48 12 54 10 60C16 58 20 62 22 68C28 62 34 64 40 70Z", "#7a72aa")
                     + M(P("M40 56C30 40 14 36 5 44C11 48 12 54 10 60C16 58 20 62 22 68C28 62 34 64 40 70Z", "#7a72aa")))
             + P("M38 52L36 34L47 47Z", "#7a72aa") + M(P("M38 52L36 34L47 47Z", "#7a72aa"))
             + P("M39 47L38 39L43 45Z", "#0aa5c4", True) + M(P("M39 47L38 39L43 45Z", "#0aa5c4", True)) + E(50, 63, 15, 17, "#7a72aa"),
        eyes=(63, 45, 55, 3, 5.4), face="#7a72aa", m=floaty(4, 6, 2.6),
        css=part("wg", .9, "50px 58px", "50%{transform:scaleY(.62) translateY(4px)}")),
    "gamemaster": dict(name="Black cat", line="Nine lives per quest, scored fairly.",
        body=G("tl", S("M68 84Q86 84 84 64Q82 56 88 52", "#6e6e84", 6))
             + P("M28 38L30 18L43 30Q50 28 57 30L70 18L72 38C80 52 80 76 70 86Q50 94 30 86C20 76 20 52 28 38Z", "#6e6e84")
             + P("M32 32L33 24L39 30Z", "#ff8fab", True) + M(P("M32 32L33 24L39 30Z", "#ff8fab", True)) + R(30, 74, 40, 5, 2.5, "#ff8fab", True),
        eyes=(56, 43, 57, 3.6, 6.4), face="#6e6e84", m=dance(9, .08, 3.3),
        css=part("tl", 1.65, "68px 84px", "50%{transform:rotate(-12deg)}")),
    "strategy": dict(name="Crystal ball", line="Reads a month ahead.",
        body=P("M30 90L36 78H64L70 90Z", "#e5534b") + C(50, 54, 26, "#c4ccff") + G("mi", S("M36 66Q44 60 50 66T64 66", "#7d8ae0", 2.4, True)),
        eyes=(55, 44, 56, 3.2, 5.8), face="#c4ccff", m=floaty(3, 3, 4.4),
        css=part("mi", 2.2, "50px 66px", "50%{transform:translateX(3px)}")),
    "assistant": dict(name="Haunted-house butler", line="Opens the door only on Ryno's word.",
        body=P("M30 40C30 28 38 22 50 22C62 22 70 28 70 40V82L62 90L56 82H44L38 90L30 82Z", "#7d8a99") + P("M41 60L50 86L59 60Z", "#f2f2f2", True)
             + P("M44 60L50 64L44 68ZM56 60L50 64L56 68Z", EYE),
        eyes=(46, 44, 56, 3, 5.4), face="#7d8a99", m=dance(5, .05, 3.6)),
}
_flake = "".join(f"M50 56l{30 * math.cos(a):.1f} {30 * math.sin(a):.1f}M{50 + 19 * math.cos(a):.1f} {56 + 19 * math.sin(a):.1f}l{8 * math.cos(a + .9):.1f} {8 * math.sin(a + .9):.1f}"
                 f"M{50 + 19 * math.cos(a):.1f} {56 + 19 * math.sin(a):.1f}l{8 * math.cos(a - .9):.1f} {8 * math.sin(a - .9):.1f}" for a in (k * math.pi / 3 - math.pi / 2 for k in range(6)))
WINTER = {
    "coordinator": dict(name="Santa", line="Makes the list, checks it twice, ships it in order.",
        body=E(50, 64, 26, 26, "#e03a3e") + P("M28 64C30 82 40 90 50 90C60 90 70 82 72 64Q61 70 50 66Q39 70 28 64Z", "#f4f4f4")
             + P("M28 42Q32 18 52 16Q70 16 79 34Q72 30 68 33L70 42Z", "#e03a3e") + R(25, 38, 50, 8, 4, "#f4f4f4") + C(80, 36, 5, "#f4f4f4"),
        eyes=(55, 44, 56, 3.2, 5.6), face="#e03a3e", m=hop(4, 6, 2.6)),
    "sketch": dict(name="Workshop elf", line="Draws the blueprints before anyone picks up a hammer.",
        body=P("M29 62L13 52L29 70Z", "#2f9e4f") + M(P("M29 62L13 52L29 70Z", "#2f9e4f")) + E(50, 69, 22, 21, "#2f9e4f")
             + G("tp", P("M30 52Q40 28 73 19Q60 33 70 52Z", "#e03a3e") + C(73, 19, 4, "#f2c14e")) + R(27, 49, 46, 6, 3, "#0969da"),
        eyes=(67, 44, 56, 3.2, 5.6), face="#2f9e4f", m=hop(5, 9, 2.0),
        css=part("tp", 1.2, "50px 52px", "50%{transform:skewX(-7deg)}")),
    "lens": dict(name="Rudolph", line="A bright red nose that spots problems through the fog.",
        body=S("M40 38V22M40 31L32 25M40 26L46 18", "#d9b27c", 3.6) + M(S("M40 38V22M40 31L32 25M40 26L46 18", "#d9b27c", 3.6))
             + E(50, 62, 22, 25, "#a8743f") + R(32, 81, 36, 5, 2.5, "#1a7f37", True) + C(50, 74, 4.6, "#ef4444", True),
        eyes=(59, 44, 56, 3.2, 5.6), face="#a8743f", m=hop(6, 7, 2.5)),
    "shield": dict(name="Nutcracker", line="Stands guard at the door all season.",
        body=R(34, 12, 32, 26, 3, "#cf222e") + R(34, 32, 32, 5, 0, "#f2c14e", True) + R(32, 37, 36, 28, 6, "#f3dcc4") + R(30, 64, 40, 26, 8, "#cf222e")
             + C(50, 72, 2.2, "#f2c14e", True) + C(50, 81, 2.2, "#f2c14e", True) + S("M33 44Q50 70 67 44", "#b5781c", 1.4, True),
        eyes=(50, 44, 56, 2.8, 5), face="#f3dcc4", m=dance(4, .06, 1.8)),
    "forge": dict(name="Gingerbread", line="Baked fresh from the recipe, icing to spec.",
        body=P("M50 18C60 18 66 25 66 33C66 37 64 40 62 42H76C82 42 84 52 78 54L64 56L70 82C72 90 62 92 60 86L50 70L40 86C38 92 28 90 30 82L36 56L22 54C16 52 18 42 24 42H38C36 40 34 37 34 33C34 25 40 18 50 18Z", "#bc6a30")
             + S("M21 46q2 2 0 4M79 46q-2 2 0 4M32 85q3 2 6 0M62 85q3 2 6 0", "#ffffff", 1.8, True) + C(50, 50, 2.4, "#ffffff", True) + C(50, 59, 2.4, "#ffffff", True),
        eyes=(32, 45, 55, 2.6, 4.6), face="#bc6a30", m=dance(10, .07, 2.4)),
    "trial": dict(name="Present", line="Wrapped, tagged, and tested before anyone opens it.",
        body=R(24, 42, 52, 46, 6, "#e0a400") + R(20, 35, 60, 12, 4, "#f0b400") + R(46, 35, 8, 53, 0, "#e03a3e", True)
             + P("M50 35C40 21 30 27 36 33Q42 37 50 35C60 21 70 27 64 33Q58 37 50 35Z", "#e03a3e"),
        eyes=(64, 40, 60, 3.2, 5.8), face="#e0a400", m=hop(6, 6, 2.2)),
    "polish": dict(name="Bauble", line="Adds the finishing sparkle, never more than it needs.",
        body=S("M50 18A4 4 0 1 1 50.1 18", "#f2c14e", 2) + R(42, 20, 16, 8, 2, "#f2c14e")
             + C(50, 58, 28, "#d6479b") + S("M31 73Q40.5 79 50 73T69 73", "#f7a8d3", 3, True),
        eyes=(56, 43, 57, 3.6, 6.4), face="#d6479b", m=swing(10, 50, 12, 3.0)),
    "advisor": dict(name="Bundled-up walker", line="Bundled up with lessons from every season.",
        body=E(50, 66, 25, 24, "#8b9bf0") + P("M26 53C26 33 38 25 50 25C62 25 74 33 74 53Z", "#e03a3e") + R(24, 48, 52, 9, 4.5, "#f4f4f4")
             + C(50, 23, 6, "#f4f4f4") + R(25, 73, 50, 8, 4, "#e03a3e") + G("sf", R(58, 76, 9, 17, 3, "#e03a3e")),
        eyes=(64, 44, 56, 3, 5.2), face="#8b9bf0", m=dance(6, .06, 2.0),
        css=part("sf", 1.2, "62px 76px", "50%{transform:rotate(-12deg)}")),
    "atlas": dict(name="Snowflake", line="Six-fold symmetry: a structure that stays simple.",
        body=G("sp", S(_flake, "#dff1ff", 6)) + C(50, 56, 15, "#dff1ff"),
        eyes=(58, 45, 55, 2.6, 4.8), face="#dff1ff", m=floaty(4, 4, 3.8),
        css=part("sp", 9, "50px 56px", "to{transform:rotate(60deg)}").replace("ease-in-out", "linear")),
    "sweep": dict(name="Snowman", line="Keeps cool under load, all winter.",
        body=E(50, 75, 23, 17, "#f4f6fb") + C(50, 47, 16, "#f4f6fb") + R(32, 30, 36, 5, 2.5, "#218bff") + R(38, 12, 24, 20, 3, "#218bff")
             + R(33, 59, 34, 6, 3, "#218bff") + P("M50 52L62 54.5L50 57Z", "#f28c28", True),
        eyes=(45, 45, 55, 2.6, 4.6), face="#f4f6fb", m=dance(8, .04, 2.4)),
    "analyst": dict(name="Advent calendar", line="Counts down the days, one honest number at a time.",
        body=R(23, 25, 54, 63, 8, "#a371f7") + "".join(R(x, 31, 11, 9, 1.5, "#d3bdff", True) for x in (29, 44.5, 60)) + R(29, 72, 11, 10, 1.5, "#d3bdff", True)
             + R(60, 72, 11, 10, 1.5, "#d3bdff", True) + R(44.5, 72, 11, 10, 1.5, "#f2c14e", True),
        eyes=(56, 44, 56, 3.2, 5.6), face="#a371f7", m=dance(9, .07, 2.7)),
    "scoutmaster": dict(name="North Star", line="Follows the brightest opportunity on the horizon.",
        body=PS(star(50, 56, 32, 15), "#f6c445", 7),
        eyes=(59, 45, 55, 3, 5.4), face="#f6c445", m=twinkle(8, 1.07, 2.6)),
    "critic": dict(name="Scrooge in his nightcap", line="Asks what it really costs before anyone spends it.",
        body=P("M30 50C30 40 38 34 50 34C62 34 70 40 70 50C72 64 78 78 76 86Q50 94 24 86C22 78 28 64 30 50Z", "#b4b8c8")
             + G("cp", P("M30 44C30 24 46 16 62 20C76 24 82 40 86 62Q78 46 70 44Z", "#f0883e") + C(86, 64, 4.2, "#f4f4f4")) + R(28, 40, 44, 7, 3.5, "#f4f4f4"),
        eyes=(57, 44, 56, 3, 5.2), face="#b4b8c8", m=dance(5, .05, 4.4),
        css=part("cp", 2.2, "70px 40px", "50%{transform:rotate(8deg)}")),
    "advocate": dict(name="Stocking", line="Hangs one up for every reader.",
        body=S("M48 0V14", "#868b9e", 1.2) + P("M34 18H62V60C62 66 66 70 74 72C84 74 84 90 72 90H48C38 90 34 82 34 74Z", "#3fb8af")
             + '<clipPath id="k"><path d="M34 18H62V60C62 66 66 70 74 72C84 74 84 90 72 90H48C38 90 34 82 34 74Z"/></clipPath><g clip-path="url(#k)">'
             + C(76, 82, 11, "#e03a3e", True) + "</g>" + R(30, 13, 36, 14, 4, "#f4f4f4"),
        eyes=(46, 42, 54, 3, 5.4), face="#3fb8af", m=swing(9, 48, 4, 3.4)),
    "librarian": dict(name="Keeper of the long list", line="Keeps the list of who did what, every name on record.",
        body=R(28, 24, 44, 58, 2, "#f1dfb4") + R(24, 18, 52, 8, 4, "#8a5a2b") + R(24, 80, 52, 8, 4, "#8a5a2b") + S("M37 64H63M37 71H57", "#b58a4f", 2.2, True),
        eyes=(47, 44, 56, 3.2, 5.6), face="#f1dfb4", m=dance(7, .06, 3.5)),
    "comms": dict(name="Caroler", line="Every verse true and on key.",
        body=E(50, 62, 24, 26, "#0aa5c4") + R(27, 70, 46, 7, 3.5, "#e03a3e") + R(56, 72, 8, 15, 3, "#e03a3e") + P("M31 80L50 84L69 80V91L50 95L31 91Z", "#f4f4f4")
             + G("nt", S("M82 30V20L88 18V28", "#868b9e", 2) + C(80.5, 30, 2.4, "#868b9e") + C(86.5, 28, 2.4, "#868b9e")),
        eyes=(56, 44, 56, 3.2, 5.6), face="#0aa5c4", m=dance(9, .06, 3.0),
        css=part("nt", 3, "84px 24px", "50%{transform:translate(-3px,-5px)}")),
    "gamemaster": dict(name="Jingle bell", line="Rings only when a quest is truly earned.",
        body=G("cl", C(50, 88, 6, "#a87700")) + P("M50 22C64 22 70 34 70 50C70 66 74 74 82 80H18C26 74 30 66 30 50C30 34 36 22 50 22Z", "#f6c445")
             + R(16, 78, 68, 8, 4, "#e0a400") + P("M50 22C42 10 33 16 40 23ZM50 22C58 10 67 16 60 23Z", "#ff8fab"),
        eyes=(53, 44, 56, 3.2, 5.6), face="#f6c445", m=swing(11, 50, 16, 1.9),
        css=part("cl", 1.3, "50px 82px", "50%{transform:rotate(-20deg)}")),
    "strategy": dict(name="Christmas tree", line="Plants early and aims for the star on top.",
        body=R(44, 80, 12, 9, 1, "#8a5a2b") + PS("M50 16L65 37H58L73 58H64L81 82H19L36 58H27L42 37H35Z", "#2f9e4f", 4)
             + C(35, 76, 3, "#e5534b", True) + C(63, 50, 3, "#e5534b", True) + C(60, 74, 3, "#e5534b", True) + P(star(50, 13, 7.5, 3.2), "#f6c445"),
        eyes=(62, 45, 55, 2.8, 5), face="#2f9e4f", m=dance(8, .07, 3.2)),
    "assistant": dict(name="Candy cane", line="Keeps every stripe of the record in order.",
        body=S("M42 90V40C42 22 70 22 70 40V46", "#f6f6f6", 18)
             + '<path d="M42 90V40C42 22 70 22 70 40V46" fill="none" stroke="#e03a3e" stroke-width="18" stroke-dasharray="6 8" stroke-linecap="butt" stroke-linejoin="miter"/>',
        eyes=(63, 38, 46, 2.6, 4.6), face="#f6f6f6", m=dance(9, .06, 2.8)),
}
COSTUMES = {"halloween": HALLOWEEN, "winter": WINTER}
PROPER = ("Santa", "Rudolph", "Frankenstein's monster", "North Star", "Scrooge in his nightcap")


def costume_svg(i, name, season):
    """One role in its seasonal character: flat, transparent, eyes #1b1f24, CSS-only motion, still under reduced motion."""
    ch = COSTUMES[season][name]
    n = ch["name"]
    who = name.capitalize() if name != "gamemaster" else "Game Master"
    label = f"{who} as {n if n in PROPER else ('an ' if n[0] in 'AEIOU' else 'a ') + n[0].lower() + n[1:]}, {'Halloween' if season == 'halloween' else 'winter holidays'}"
    return character(i, ch, label, shade(ROLES[name][0]), ROLES[name][3])


def character(i, ch, label, badge_fill, badge):
    """A drawn character (costume or fixed): the shared motion, eyes and job badge around ch["body"]."""
    m, dur = ch["m"], ch["m"]["dur"]
    lag = round((i * .37) % dur, 2)
    a = f"{dur}s{f' -{lag}s' if lag else ''} ease-in-out infinite"  # negative delay: out of step, already moving
    cy, xl, xr, rx, ry = ch["eyes"]
    k = 3.2 if rx < 3.4 else 4
    qn, qs = m["qN"], m["qS"]
    # One shared timing for the four loops, then each loop's name and origin (same motion as four full shorthands).
    # Keyframes leave out 0% and 100% where the pose is the resting one: a missing end keyframe is the element's own
    # transform (none), so it draws the same (page budget, Oct 20 3:54 PM ET).
    if ch.get("calm"):  # a slow sway and the blink only (the CEO: calm motion, fewer bytes on the Team page)
        css = (f".s,.e{{animation:{a}}}.s{{animation-name:s;transform-origin:{m['o']}}}.e{{animation-name:e;transform-box:fill-box;transform-origin:center}}"
               f"@keyframes s{{50%{{transform:{m['N']}}}25%{{transform:{m['L']}}}75%{{transform:{m['R']}}}}}"
               f"@keyframes e{{10%,50%,60%{{transform:none}}25%,75%{{transform:scale(1.32,.7)}}}}@media(prefers-reduced-motion:reduce){{*{{animation:none!important}}}}")
    else:
        css = (f".s,.q,.g,.e{{animation:{a}}}.s{{animation-name:s;transform-origin:{m['o']}}}.q{{animation-name:q;transform-origin:50px 90px}}"
               f".g{{animation-name:g}}.e{{animation-name:e;transform-box:fill-box;transform-origin:center}}"
               f"@keyframes s{{50%{{transform:{m['N']}}}25%{{transform:{m['L']}}}75%{{transform:{m['R']}}}}}"
               f"@keyframes q{{0%,50%,to{{transform:scale({qn[0]},{qn[1]})}}25%,75%{{transform:scale({qs[0]},{qs[1]})}}}}"
               f"@keyframes g{{50%{{transform:none}}25%{{transform:translateX(-{k}px)}}75%{{transform:translateX({k}px)}}}}"
               f"@keyframes e{{10%,50%,60%{{transform:none}}25%,75%{{transform:scale(1.32,.7)}}}}"
               + ch.get("css", "") + "@media(prefers-reduced-motion:reduce){*{animation:none!important}}")
    glyph = (f'<path d="{BADGE[badge]}" fill="none" stroke="#fff" stroke-width="1.8"/>'
             if badge in STROKED else f'<path d="{BADGE[badge]}" fill="#fff"/>')
    eyes = "".join(f'<ellipse class="e" cx="{x}" cy="{cy}" rx="{rx}" ry="{ry}"/>' for x in (xl, xr))
    # Page budget (Ryno, Oct 20 7:27 AM ET): round caps and joins are set once on the root and the eye colour once on the
    # eye group (SVG attributes inherit; the stills keep them because still() only drops <style>). Same pixels, fewer bytes.
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" aria-label="{label}"'
            f' stroke-linecap="round" stroke-linejoin="round"><style>{css}</style>'
            + (f'<g class="s">{ch["body"]}<g fill="{EYE}">{eyes}</g></g>' if ch.get("calm") else f'<g class="s"><g class="q">{ch["body"]}<g class="g" fill="{EYE}">{eyes}</g></g></g>')
            + f'<g transform="translate(80 82)"><circle r="10" fill="{badge_fill}"/>{glyph}</g></svg>\n')


# Ryno, the human CEO (Oct 20, 2026: 3:45 PM ET "Rhino b no glasses"; 3:48 PM ET "lets let the rhino be the every day look
# and the trading card background only changes with holiday theme"). One drawing all year: it is never in a costume set, and
# files() writes the same file for every season. Slate body (#748699, darkened for the Management card and still 3:1 with
# the eyes) with a dark slate outline (#2e3a48) so he reads on the light lilac art window; gold crown; CEO star badge.
CEO_SLATE, CEO_LINE = "#748699", "#2e3a48"


def _ceo(d, f=CEO_SLATE):
    return f'<path d="{d}" fill="{f}" stroke="{CEO_LINE}" stroke-width="3" paint-order="stroke"/>'


FIXED = {"ceo": dict(label="Ryno, the human CEO, as a crowned rhino", badge="#146fac", i=17, ch=dict(
    body=_ceo("M22 36L18 22L32 30ZM78 36L82 22L68 30ZM18 52Q18 28 50 28Q82 28 82 52Q84 70 72 82Q62 90 50 90Q38 90 28 82Q16 70 18 52Z")  # ears + head
    + P("M30 74Q30 62 50 62Q70 62 70 74Q70 86 50 86Q30 86 30 74Z", "#9fb0c2", True)
    + P("M43 66Q45 40 50 26Q55 40 57 66Z", "#ece6d6") + P("M46 40Q48 32 50 26Q52 32 54 40Z", "#d8d0bc", True)
    + P("M40 78a2 3 0 1 0 4 0a2 3 0 1 0-4 0M56 78a2 3 0 1 0 4 0a2 3 0 1 0-4 0", "#5d6d80", True)  # nostrils
    + P("M42 26l-1-10.8 4.48 5.4 3.52-12 3.52 12 4.48-5.4-1 10.8Z", "#f2c14e"),
    eyes=(50, 33, 67, 2.8, 4.8), face=CEO_SLATE, m=dance(6, .06, 3.4), calm=True))}


def fixed_svg(name):
    f = FIXED[name]
    return character(f["i"], f["ch"], f["label"], f["badge"], ROLES[name][3])


def still(s):
    """The same drawing with no motion: the neutral pose, for long lists."""
    return re.sub(r"<style>.*?</style>", "", s)


def files(season):
    """{relative path: svg} for a whole set: one animated and one still file per role."""
    out = {}
    for i, (n, spec) in enumerate(ROLES.items()):
        s = fixed_svg(n) if n in FIXED else costume_svg(i, n, season) if n in COSTUMES.get(season, {}) else svg(i, n, *spec)
        out[f"{n}.svg"], out[f"still/{n}.svg"] = s, still(s)
    return out


def today_et():
    return datetime.now(ET).date()


def committed_season():
    """Which complete set is committed now, or None if the files match no set."""
    for season in ("normal", *COSTUMES):
        if all((OUT / f).exists() and (OUT / f).read_text() == s for f, s in files(season).items()):
            return season
    return None


if __name__ == "__main__":
    when = date.fromisoformat(sys.argv[sys.argv.index("--date") + 1]) if "--date" in sys.argv else today_et()
    want = season_for(when)
    if "--check" in sys.argv:
        have = committed_season()
        print(f"avatars: committed set {have or 'mixed'}, {when} needs {want}")
        sys.exit(0 if have == want else 1)
    (OUT / "still").mkdir(parents=True, exist_ok=True)
    out = files(want)
    for f, s in out.items():
        (OUT / f).write_text(s)
    print(f"wrote the {want} set for {when}: {len(out)} files, max {max(len(s.encode()) for s in out.values())} bytes")
