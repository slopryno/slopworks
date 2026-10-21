"""No CEO quotes on the site (Ryno, Oct 21, 2026, 8:51 AM ET). His exact words and their ET time stay on the PR and in the
add-only records (data/ceo_decisions.json, data/ceo_overrides.json) for the audit trail; the site says what he decided, not
what he wrote.

build.py runs every data record through scrub_all() as it loads, so a quote typed into a chat message, an idea's reason, a
calendar note or a PR title is rendered as a neutral line ("Ryno's call", "Approved by Ryno ... ET.") and never in quote marks.
check.py (ceo_quote_errors) and tests/test_ceo_quotes.py fail the build if one still reaches a built page. Standard library only."""
import html, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# A quoted span: curly double, straight double, or single quotes that aren't apostrophes.
Q = r'(?:“[^”\n]{1,240}”|"[^"\n<>{}]{1,240}"|(?<![\w’\'])\'[^\'\n]{1,240}?\'(?![\w]))'
WHO = r"(?:Ryno|the CEO|CEO)"
TIME = r"\d{1,2}:\d\d\s?[AP]M ET"
MIN_REGISTRY = 4  # registry quotes shorter than this ("Yes") are only caught by their attribution


def _inner(q):
    return q[1:-1].strip()


def _fix(s):
    s = re.sub(r"\s+([.,;:)])", r"\1", s)
    s = re.sub(r"\(\s*\)", "", s)
    s = re.sub(r"\.\.(?!\.)", ".", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip() if s.strip() != s and s[:1] == " " else s


def _end(m):
    """A full stop where a dropped quote ended its sentence."""
    q, rest = _inner(m.group("q")), m.string[m.end():m.end() + 1]
    return "." if q[-1:] in ".!?" and rest in (" ", "") else ""


def _cont(m):
    if m.group(0).startswith("At "):
        return f"He added more at {m.group(1)}" + _end(m)
    return _drop(m)


def _drop(m):
    """Take out ': QUOTE' or ' (QUOTE, ' and keep the sentence whole."""
    head, sep, after, q = m.group(1), m.group("sep"), m.group("after") or "", _inner(m.group("q"))
    if sep.strip() == "(":
        return head + (" (" if after == ", " else "")
    if after == ")":
        return head + ")"
    if after == ", ":
        return head + ", "
    return head + _end(m)


RULES = [
    # "Ryno said 'Build it' (i42) to the list" -> "Ryno decided (i42) on the list"
    (re.compile(rf"\b({WHO}) said (?P<q>{Q})((?:\s\([^)]*\))?) to\b"), lambda m: f"{m.group(1)} decided{m.group(3)} on"),
    (re.compile(rf"\b({WHO}) said (?P<q>{Q})"), lambda m: f"{m.group(1)} decided"),
    # "(Ryno: 'too dark?')" -> "(Ryno's feedback)"
    (re.compile(rf"\(({WHO}): (?P<q>{Q})\)"), lambda m: f"({m.group(1).replace('the CEO', 'CEO')}'s feedback)"),
    # "Switch-on "Yes" from Ryno" -> "Switch-on decision from Ryno"
    (re.compile(rf"(?P<q>{Q}) (from|by) ({WHO})\b"), lambda m: f"decision {m.group(2)} {m.group(3)}"),
    # "Ryno, 11:02 AM ET: "Lets run another sprint"." -> "Ryno's call, 11:02 AM ET."
    (re.compile(rf"\b(Ryno), ((?:[A-Z][a-z]{{2}} \d{{1,2}},? )?{TIME}): (?P<q>{Q})"), lambda m: f"{m.group(1)}'s call, {m.group(2)}"),
    # "Ryno in Grok Bot chat 2026-10-18 1:17 AM ET: 'Build it', on ..." -> "Decided by Ryno in Grok Bot chat ... ET, on ..."
    (re.compile(rf"(^|(?<=[.:] ))({WHO}) in ([^.;\n]{{0,90}}?): (?P<q>{Q})"), lambda m: f"{m.group(1)}Decided by {m.group(2)} in {m.group(3)}" + _end(m)),
    # "Training note on Ryno's Oct 21 ask, "Have the team review": 8 roles" -> "Training note on Ryno's Oct 21 ask: 8 roles"
    (re.compile(rf"\b((?:Ryno|the CEO|CEO)'s [^.;\n\"“']{{0,60}}?),? (?P<q>{Q})"), lambda m: m.group(1) + _end(m)),
    # "Approved by Ryno in Grok Bot chat 2026-10-17 7:24 AM ET: 'Lift the cap.' One-time" -> "Approved by Ryno in Grok Bot chat 2026-10-17 7:24 AM ET. One-time"
    # "Directed by Ryno ... ET ('lets heed her words', on X)" -> "Directed by Ryno ... ET (on X)"
    (re.compile(rf"\b({WHO}\b[^.;\n\"“']{{0,90}}?)(?P<sep>: | \()(?P<q>{Q})(?P<after>, |\))?"), lambda m: _drop(m)),
]
CONT = re.compile(rf"(?:\bAt )?({TIME})(?P<sep>: )(?P<q>{Q})(?P<after>)")  # "At 7:12 PM ET: 'UX will be top priority'"


def scrub(s, registry=()):
    """Return (text without CEO quotes, list of the quotes taken out)."""
    if not isinstance(s, str) or not re.search(r"[\"“'‘]", s):
        return s, []
    found = []
    def take(fn):
        def sub(m):
            found.append(_inner(m.group("q")))
            return fn(m)
        return sub
    named = bool(re.search(rf"\b{WHO}\b", s))
    if named:
        for rx, fn in RULES:
            s = rx.sub(take(fn), s)
        s = CONT.sub(take(_cont), s)  # a timed quote in a line that names him is his
    for q in registry:
        if len(q) >= MIN_REGISTRY:
            rx = re.compile(r"(?:“|\"|(?<![\w’'])')" + re.escape(q) + r"(?:”|\"|'(?!\w))")
            if rx.search(s):
                found.append(q)
                s = rx.sub("CEO feedback", s)
    return (_fix(s) if found else s), found


def records_registry(root=None):
    """His exact words from the structured records: these must never reach a page, attributed or not."""
    root = root or ROOT
    load = lambda n: json.loads((root / "data" / n).read_text()) if (root / "data" / n).exists() else []
    qs = {(r.get("quote") or "").strip() for f in ("ceo_decisions.json", "ceo_overrides.json") for r in load(f)}
    for r in load("ceo_decisions.json"):
        qs.update(_inner(m.group(0)) for m in re.finditer(Q, r.get("authority") or ""))
    return sorted((q for q in qs if q), key=len, reverse=True)


def _strings(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from _strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from _strings(v)
    elif isinstance(o, str):
        yield o


def registry(root=None):
    """records_registry plus every quote the rules take out of any data file, so the same words are caught unattributed."""
    root = root or ROOT
    qs = set(records_registry(root))
    for p in sorted((root / "data").glob("*.json")):
        try:
            for s in _strings(json.loads(p.read_text())):
                qs.update(scrub(s)[1])
        except ValueError:
            continue
    return sorted((q for q in qs if len(q) >= MIN_REGISTRY), key=len, reverse=True)


def scrub_all(o, reg):
    if isinstance(o, dict):
        return {k: scrub_all(v, reg) for k, v in o.items()}
    if isinstance(o, list):
        return [scrub_all(v, reg) for v in o]
    return scrub(o, reg)[0] if isinstance(o, str) else o


def page_text(rel, raw):
    """Visible text of a built file, unescaped, for the check."""
    if rel.endswith((".html", ".xml")):
        raw = re.sub(r"<(style|script|svg)\b.*?</\1>", " ", raw, flags=re.S)
        raw = html.unescape(re.sub(r"<[^>]+>", " ", raw))
        return html.unescape(raw)
    if rel.endswith(".json"):
        try:
            return "\n".join(_strings(json.loads(raw)))
        except ValueError:
            return raw
    if rel.endswith(".ics"):
        return raw.replace("\\,", ",").replace("\\;", ";").replace("\r\n ", "")
    return raw


def hits(text, reg):
    """CEO quotes still in a page's text: attributed ones, and any registry quote in quote marks."""
    out = []
    for line in text.split("\n"):
        out += scrub(line, reg)[1]
    return out
