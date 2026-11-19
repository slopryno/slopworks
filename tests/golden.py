"""Stdlib expect/golden helper. No third-party snapshot library.

Compare text to a file under tests/goldens/. On a mismatch the test fails with a
unified diff. Rewrite a golden only when you have read that diff and then rerun
with UPDATE=1. Never accept a golden in CI, and never set UPDATE=1 to silence a
failure you have not read.
"""
from __future__ import annotations

import difflib
import os
import re
from pathlib import Path

GOLDENS = Path(__file__).resolve().parent / "goldens"
UPDATE_ENV = "UPDATE"


def update_mode():
    """True only for the explicit UPDATE=1 rewrite path."""
    return os.environ.get(UPDATE_ENV) == "1"


def path_for(name, root=None):
    return Path(root) / name if root is not None else GOLDENS / name


def unified_diff(want, got, name):
    """Readable unified diff; labels the golden as the from-file and the test output as actual."""
    return "".join(
        difflib.unified_diff(
            want.splitlines(keepends=True),
            got.splitlines(keepends=True),
            fromfile=f"goldens/{name}",
            tofile="actual",
            n=3,
        )
    )


def assert_matches(test, name, text, root=None):
    """Compare text to tests/goldens/<name>, or rewrite that file when UPDATE=1."""
    if not isinstance(text, str):
        test.fail(f"golden {name}: expected str, got {type(text).__name__}")
    path = path_for(name, root)
    if update_mode():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return
    if not path.is_file():
        test.fail(
            f"missing golden {path}. After you have read the output, rewrite it with "
            f"UPDATE=1 python3 -m unittest …"
        )
    want = path.read_text()
    if want != text:
        diff = unified_diff(want, text, name) or "(texts differ but the unified diff is empty)"
        test.fail(
            f"golden {name} differs. Read this diff before accepting, then rerun with "
            f"UPDATE=1 to rewrite the file:\n{diff}"
        )


def team_slice(html):
    """Tabs, main, and footer sitelist — Team chrome without the inlined CSS or page wrapper."""
    tabs = re.search(r'<nav class="tabs" aria-label="Main">.*?</nav>', html, re.S)
    main = re.search(r"<main\b.*?</main>", html, re.S)
    foot = re.search(r'<nav class="sitelist" aria-label="Sections">.*?</nav>', html, re.S)
    missing = [n for n, m in (("tabs", tabs), ("main", main), ("sitelist", foot)) if not m]
    if missing:
        raise ValueError(f"team page is missing {', '.join(missing)}")
    return f"{tabs.group(0)}\n{main.group(0)}\n{foot.group(0)}\n"


def _strip_slot_rarity(match):
    """Drop level-derived rarity classes (rN, holo); keep type, lead, and other stable classes."""
    kept = [c for c in match.group(2).split() if c != "holo" and not re.fullmatch(r"r\d+", c)]
    return match.group(1) + (" " + " ".join(kept) if kept else "") + match.group(3)


def normalize_team(html):
    """Strip record-backed and other volatile bits so a records refresh does not churn goldens.

    Keeps season art, flavour, flip/badge/footer wiring, and other markup a CSS or structure
    change would still move.
    """
    text = html
    text = re.sub(r'<li class="lvf">.*?</li>', '<li class="lvf">Last verified · #N</li>', text)
    text = re.sub(r"<li><b>XP</b><em>\d+</em></li>", "<li><b>XP</b><em>N</em></li>", text)
    text = re.sub(r"Lv <span>\d+</span></span> · [^<]+", "Lv <span>N</span></span> · RANK", text)
    text = re.sub(
        r'(<div class="bar" aria-hidden="true"><span style="width:)\d+(%)',
        r"\1PCT\2",
        text,
    )
    text = re.sub(r"<em>\d+<small>[^<]*</small></em>", "<em>N<small> UNIT</small></em>", text)
    text = re.sub(r'(<ol class="recent">).*?(</ol>)', r"\1<li>ROLE · PR</li>\2", text, flags=re.S)
    text = re.sub(r'(<p class="rar">)[^·<]+ · (\d+/\d+</p>)', r"\1RARITY · \2", text)
    text = re.sub(r'(<li class="slot)([^"]*)(")', _strip_slot_rarity, text)
    return text

TAB_NAV = re.compile(r'<nav class="tabs" aria-label="Main">.*?</nav>', re.S)
SITELIST = re.compile(r'<nav class="sitelist" aria-label="Sections">.*?</nav>', re.S)


def nav_tabs(html):
    """The five-tab main nav, or ValueError if the page is missing it."""
    m = TAB_NAV.search(html)
    if not m:
        raise ValueError("page is missing the main tab bar")
    return m.group(0)


def footer_sitelist(html):
    """The footer section list, or ValueError if the page is missing it."""
    m = SITELIST.search(html)
    if not m:
        raise ValueError("page is missing the footer sitelist")
    return m.group(0)


def normalize_chrome(fragment):
    """Strip relative-path prefixes so Home, Team, and nested pages share one chrome golden.

    href="../updates/" and href="../../updates/" both become href="updates/"; the home
    tab's href="../" or href="../../" becomes href="". Nothing record-backed lives in
    the tab bar or sitelist, so there is nothing else to strip.
    """
    return re.sub(r'href="(?:\.\./)+', 'href="', fragment)


def tabs_golden_name(slug):
    """tests/goldens/ name for the tab bar on this hub (Home is tabs-home.html)."""
    return "tabs-home.html" if slug == "" else f"tabs-{slug.strip('/')}.html"


ASOF_ET = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} ET")


def metrics_chart_slice(html):
    """Trends table: two-day comparison plus sparklines. Raises if the table is missing."""
    m = re.search(r'<table class="trend">.*?</table>', html, re.S)
    if not m:
        raise ValueError("metrics page is missing the trends table")
    return m.group(0) + "\n"


def normalize_metrics_charts(html):
    """Strip as-of clock times; break rows so a unified diff stays readable. Does not change the page."""
    text = ASOF_ET.sub("AS-OF ET", html)
    for a in ("</caption>", "</thead>", "</tr>"):
        text = text.replace(a, a + "\n") if a != "</tr>" else text
    return text.replace("</tr><tr", "</tr>\n<tr")
