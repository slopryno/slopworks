"""d4 / i17: WCAG contrast for theme text colors in both themes (fails CI below 4.5:1)."""
import re, unittest
from pathlib import Path

CSS = (Path(__file__).resolve().parent.parent / "site/style.css").read_text()
TEXT = ["fg", "muted", "link", "ok", "warn", "accent", "bad"]   # colors used for text
SURFACES = ["bg", "card"]                              # backgrounds text sits on


def themes(css):
    light = re.search(r":root\{([^}]*)\}", css).group(1)
    dark = re.search(r"prefers-color-scheme:\s*dark\)\s*\{\s*:root\{([^}]*)\}", css).group(1)
    parse = lambda s: dict(re.findall(r"--([a-z]+):\s*(#[0-9a-fA-F]{3,6})\b", s))
    return {"light": parse(light), "dark": parse(dark)}


def lum(h):
    if len(h) == 4:
        h = "#" + "".join(x * 2 for x in h[1:])
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def failures(css):
    out = []
    for name, v in themes(css).items():
        colors = {k: v[k] for k in TEXT}
        for t, c in colors.items():
            for s in SURFACES:
                r = ratio(c, v[s])
                if r < 4.5:
                    out.append(f"{name}: {t} {c} on {s} {v[s]} is {r:.2f}:1")
    return out


class Contrast(unittest.TestCase):
    def test_math(self):
        self.assertAlmostEqual(ratio("#000000", "#ffffff"), 21, places=1)

    def test_theme_text_pairs_meet_aa(self):
        self.assertEqual(failures(CSS), [])

    def test_no_hardcoded_text_colors(self):
        # text colors must come from theme variables so the check above covers them
        self.assertEqual(re.findall(r"(?<![-\w])color:\s*#[0-9a-fA-F]+", CSS), [])

    def test_catches_bad_color(self):
        bad = CSS.replace("--muted:#57606a", "--muted:#bbbbbb", 1)
        self.assertTrue(any("light: muted" in f for f in failures(bad)))


if __name__ == "__main__":
    unittest.main()
