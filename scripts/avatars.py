#!/usr/bin/env python3
"""Each role's self-designed avatar: one shared stylized-robot style, varied by role. Plain SVG, no scripts, no logos.
Changes go through Polish (design) and Shield (safety) review."""
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "site/assets/avatars"
# role: (color, head shape, eyes, antenna, emblem, why)
ROLES = {
    "coordinator": ("#8250df", "round", "dots", "flag", "compass", "Points the team in one direction"),
    "sketch": ("#0969da", "square", "dots", "pencil", "grid", "Scout: drafts and maps what's new"),
    "lens": ("#1a7f37", "round", "lens", "dot", "check", "Verify: one big magnifying eye"),
    "shield": ("#cf222e", "square", "visor", "dot", "shieldshape", "Guards secrets and personal data"),
    "forge": ("#bc4c00", "square", "dots", "bolt", "wrench", "Builds and publishes"),
    "pixel": ("#d63384", "round", "square", "dot", "pixels", "Front-end specialist"),
    "core": ("#57606a", "square", "dots", "bolt", "gear", "Data and build specialist"),
    "trial": ("#9a6700", "round", "dots", "dot", "flask", "Tests before code"),
    "polish": ("#bf3989", "round", "smile", "sparkle", "brush", "Makes it nicer every week"),
    "advisor": ("#4e5ba6", "round", "glasses", "dot", "book", "Turns lessons into rules"),
    "atlas": ("#116329", "square", "dots", "flag", "globe", "Keeps the structure sound"),
    "sweep": ("#0550ae", "square", "dots", "dot", "broom", "Keeps it running and on budget"),
    "analyst": ("#6639ba", "round", "dots", "dot", "bars", "Weekly numbers"),
    "ceo": ("#24292f", "round", "dots", "star", "star", "The human CEO's placeholder, not a photo"),
}
EMBLEM = {
    "compass": '<circle cx="50" cy="80" r="7" fill="none" stroke="#fff" stroke-width="2"/><path d="M50 74l3 6-3 6-3-6z" fill="#fff"/>',
    "grid": '<path d="M43 74h14M43 80h14M43 86h14M46 72v16M54 72v16" stroke="#fff" stroke-width="1.6"/>',
    "check": '<path d="M43 80l5 5 9-10" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round"/>',
    "shieldshape": '<path d="M50 72l8 3v5c0 5-4 8-8 9-4-1-8-4-8-9v-5z" fill="#fff"/>',
    "wrench": '<path d="M44 86l9-9m2-3a4 4 0 1 0 3 3" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round"/>',
    "pixels": '<rect x="43" y="73" width="5" height="5" fill="#fff"/><rect x="52" y="73" width="5" height="5" fill="#fff"/><rect x="47" y="81" width="6" height="5" fill="#fff"/>',
    "gear": '<circle cx="50" cy="80" r="6" fill="none" stroke="#fff" stroke-width="3" stroke-dasharray="3 2"/><circle cx="50" cy="80" r="2" fill="#fff"/>',
    "flask": '<path d="M47 72h6M48 72v5l-5 9h14l-5-9v-5" fill="none" stroke="#fff" stroke-width="2" stroke-linejoin="round"/>',
    "brush": '<path d="M56 72l-8 9" stroke="#fff" stroke-width="3" stroke-linecap="round"/><circle cx="46" cy="84" r="3" fill="#fff"/>',
    "book": '<path d="M42 74h7v12h-7zM51 74h7v12h-7z" fill="none" stroke="#fff" stroke-width="2"/>',
    "globe": '<circle cx="50" cy="80" r="7" fill="none" stroke="#fff" stroke-width="2"/><path d="M43 80h14M50 73c-4 4-4 10 0 14c4-4 4-10 0-14" fill="none" stroke="#fff" stroke-width="1.5"/>',
    "broom": '<path d="M55 71l-6 9M44 88l5-8 4 2-3 6z" stroke="#fff" stroke-width="2" fill="#fff"/>',
    "bars": '<path d="M44 87v-5M50 87v-11M56 87v-8" stroke="#fff" stroke-width="3" stroke-linecap="round"/>',
    "star": '<path d="M50 72l2.4 5 5.6.6-4.2 3.8 1.2 5.6-5-2.9-5 2.9 1.2-5.6-4.2-3.8 5.6-.6z" fill="#fff"/>',
}
EYES = {
    "dots": '<circle cx="40" cy="45" r="5" fill="#1b1f24"/><circle cx="60" cy="45" r="5" fill="#1b1f24"/>',
    "lens": '<circle cx="40" cy="45" r="4" fill="#1b1f24"/><circle cx="60" cy="45" r="9" fill="none" stroke="#1b1f24" stroke-width="3"/><circle cx="60" cy="45" r="3" fill="#1b1f24"/>',
    "visor": '<rect x="30" y="40" width="40" height="10" rx="5" fill="#1b1f24"/><rect x="34" y="43" width="12" height="4" rx="2" fill="#fff"/>',
    "square": '<rect x="35" y="40" width="10" height="10" fill="#1b1f24"/><rect x="55" y="40" width="10" height="10" fill="#1b1f24"/>',
    "smile": '<path d="M35 46q5-6 10 0M55 46q5-6 10 0" fill="none" stroke="#1b1f24" stroke-width="3" stroke-linecap="round"/>',
    "glasses": '<circle cx="40" cy="45" r="7" fill="none" stroke="#1b1f24" stroke-width="2.5"/><circle cx="60" cy="45" r="7" fill="none" stroke="#1b1f24" stroke-width="2.5"/><path d="M47 45h6" stroke="#1b1f24" stroke-width="2.5"/><circle cx="40" cy="45" r="2.5"/><circle cx="60" cy="45" r="2.5"/>',
}
ANT = {
    "dot": '<path d="M50 24V14" stroke="#fff" stroke-width="3"/><circle cx="50" cy="12" r="4" fill="#fff"/>',
    "flag": '<path d="M50 24V10" stroke="#fff" stroke-width="3"/><path d="M50 10h10l-3 4 3 4H50z" fill="#fff"/>',
    "pencil": '<path d="M50 24l-4-12h8z" fill="#fff"/>',
    "bolt": '<path d="M52 8l-6 9h5l-3 8 8-11h-5z" fill="#fff"/>',
    "sparkle": '<path d="M50 6l2 6 6 2-6 2-2 6-2-6-6-2 6-2z" fill="#fff"/>',
    "star": '<path d="M50 6l2.4 5 5.6.6-4.2 3.8 1.2 5.6-5-2.9-5 2.9 1.2-5.6-4.2-3.8 5.6-.6z" fill="#fff"/>',
}


def svg(name, color, head, eyes, ant, emblem, why):
    rx = 20 if head == "round" else 6
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" aria-label="{name.capitalize()} avatar: {why}">'
            f'<rect width="100" height="100" rx="22" fill="{color}"/>{ANT[ant]}'
            f'<rect x="24" y="24" width="52" height="40" rx="{rx}" fill="#f6f8fa"/>{EYES[eyes]}'
            f'<rect x="20" y="38" width="5" height="12" rx="2" fill="#f6f8fa"/><rect x="75" y="38" width="5" height="12" rx="2" fill="#f6f8fa"/>'
            f'<path d="M42 57h16" stroke="#1b1f24" stroke-width="2.5" stroke-linecap="round"/>{EMBLEM[emblem]}</svg>\n')


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for n, spec in ROLES.items():
        (OUT / f"{n}.svg").write_text(svg(n, *spec))
    print(f"wrote {len(ROLES)} avatars")
