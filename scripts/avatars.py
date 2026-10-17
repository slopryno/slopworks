#!/usr/bin/env python3
"""Each role's avatar (v2): a soft single-color blob with two slanted pill eyes and a tiny job badge.
Transparent, flat, animated with inline CSS only (idle squish, staggered blinks), static under
prefers-reduced-motion. Inspired by the Grok Bot app style, not copied. Changes need Polish + Shield review."""
import math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "site/assets/avatars"
# role: (color, shape, params, badge, why)
ROLES = {
    "coordinator": ("#8250df", "wave", (5, .13), "arrow", "a five-point star blob that points the way"),
    "sketch": ("#0969da", "drop", (-2.3,), "pencil", "Scout: a droplet that leans forward"),
    "lens": ("#1a7f37", "wave", (0, 0), "check", "Verify: a calm round blob"),
    "shield": ("#cf222e", "squircle", (4,), "shield", "a sturdy squircle"),
    "forge": ("#bc4c00", "wave", (7, .07), "bolt", "a cookie-edged builder"),
    "pixel": ("#d63384", "cloud", (4,), "square", "a four-puff cloud"),
    "core": ("#6e7781", "wave", (2, .09), "ring", "a bean-shaped data blob"),
    "trial": ("#bf8700", "wave", (8, .05), "flask", "a puffy, careful tester"),
    "polish": ("#bf3989", "cloud", (5,), "sparkle", "a flower-ish puff"),
    "advisor": ("#4e5ba6", "egg", (.12,), "book", "an egg that's seen it all"),
    "atlas": ("#1b7c83", "wave", (6, .11), "globe", "a six-bump cookie"),
    "sweep": ("#218bff", "squircle", (2.6,), "wave", "a soft rounded square"),
    "analyst": ("#a371f7", "wave", (4, .1), "bars", "a four-lobe clover"),
    "ceo": ("#d4a72c", "drop", (-0.8,), "star", "a gold droplet placeholder for the CEO, not a photo"),
}
BADGE = {
    "arrow": "M0-5l4 9-4-2-4 2z", "pencil": "M-4 4l1-4 6-6 3 3-6 6z", "check": "M-4 0l3 3 5-6",
    "shield": "M0-5l5 2v2c0 4-3 6-5 7-2-1-5-3-5-7v-2z", "bolt": "M1-6l-5 7h4l-1 5 5-7h-4z",
    "square": "M-4-4h8v8h-8z", "ring": "M-4 0a4 4 0 1 0 8 0a4 4 0 1 0-8 0", "flask": "M-2-5h4M-1-5v3l-4 7h10l-4-7v-3",
    "sparkle": "M0-6l1.5 4.5L6 0l-4.5 1.5L0 6l-1.5-4.5L-6 0l4.5-1.5z", "book": "M-5-4h4v8h-4zM1-4h4v8h-4z",
    "globe": "M-5 0h10M0-5c-3 3-3 7 0 10c3-3 3-7 0-10", "wave": "M-5 1q2.5-4 5 0t5 0", "bars": "M-3 4v-3M0 4v-8M3 4v-5",
    "star": "M0-5.5l1.6 3.4 3.7.4-2.8 2.5.8 3.7L0 2.6-3.3 4.5l.8-3.7-2.8-2.5 3.7-.4z",
}
STROKED = {"ring", "check", "flask", "globe", "wave", "bars"}


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


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for i, (n, spec) in enumerate(ROLES.items()):
        (OUT / f"{n}.svg").write_text(svg(i, n, *spec))
    print(f"wrote {len(ROLES)} avatars, max {max(f.stat().st_size for f in OUT.glob('*.svg'))} bytes")
