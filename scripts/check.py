#!/usr/bin/env python3
"""Slopworks CI checks. Standard library only (free tier, fast, no dependencies).

Usage:
  check.py repo              schema, IDs, sources, secrets, PII, files, a11y, page weight, schedule
  check.py paths             bot/data-* branches may only touch data/ and site/
  check.py review-gate       role sign-offs on the PR (needs PR context in env)
  check.py guardrail-gate    flags changes that loosen safety checks (needs PR context in env)
"""
import html.parser, json, os, re, subprocess, sys, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATTERNS = json.loads((ROOT / "scripts/patterns.json").read_text())
ALLOW = json.loads((ROOT / "data/schema/allowed_handles.json").read_text())
ALLOWED_HANDLES = {h.lower() for h in ALLOW["handles"]}
ALLOWED_EMAILS = {e.lower() for e in ALLOW["emails"]}
CSS_AT_RULES = {"media", "font", "keyframes", "import", "supports", "charset", "page", "layer", "container", "namespace"}
SOURCE_HOSTS = ("x.com", "github.com", "grokbot.com", "grok.com", "x.ai")
DATA_FILES = ["updates", "issues", "runs", "chat", "design_backlog", "state", "schedule"]
DATA_FILES += ["standup", "ideas"]
DATA_FILES += ["wins"]
DATA_FILES += ["research"]
DATA_FILES += ["alumni"]
DATA_FILES += ["arena", "cases", "challenges"]  # showcase data (i22), added in sprint PR 8
DATA_FILES += ["aars"]  # same-day after-action reviews (Ryno, 2026-10-17)
ALIASES = {"verify": "Lens", "scout": "Sketch", "publish": "Forge", "privacy": "Shield"}


# ---------- schema ----------
def load_schema(name):
    return json.loads((ROOT / f"data/schema/{name}.schema.json").read_text())


def validate(value, schema, path="$"):
    errs = []
    t = schema.get("type")
    types = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool, "null": type(None)}
    if t:
        allowed = t if isinstance(t, list) else [t]
        if not any(isinstance(value, types[x]) and not (x == "integer" and isinstance(value, bool)) for x in allowed):
            return [f"{path}: expected {t}"]
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path}: {value!r} not in {schema['enum']}")
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errs.append(f"{path}: {value!r} does not match {schema['pattern']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errs.append(f"{path}: longer than {schema['maxLength']}")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for k in schema.get("required", []):
            if k not in value:
                errs.append(f"{path}: missing {k}")
        for k, v in value.items():
            if k in props:
                errs += validate(v, props[k], f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: unexpected field {k}")
    if isinstance(value, list) and "items" in schema:
        for i, v in enumerate(value):
            errs += validate(v, schema["items"], f"{path}[{i}]")
    return errs


def duplicate_ids(entries):
    seen, dups = set(), []
    for e in entries:
        if e.get("id") in seen:
            dups.append(e.get("id"))
        seen.add(e.get("id"))
    return dups


def bad_source(url):
    u = urllib.parse.urlparse(url)
    if u.scheme != "https":
        return "must be https"
    if u.query or u.fragment:
        return "no query strings or fragments (tracking)"
    host = (u.hostname or "").lower()
    if not any(host == h or host.endswith("." + h) for h in SOURCE_HOSTS):
        return f"host {host} is not an allowed public source"
    if host == "x.com" and not re.fullmatch(r"/[A-Za-z0-9_]{1,15}/status/\d+", u.path):
        return "x.com source must be a post URL"
    return ""


def live_link_errors(urls):
    """Network check for non-X sources (X blocks automated fetches; its URLs are format-checked)."""
    errs = []
    for url in sorted(set(urls)):
        if urllib.parse.urlparse(url).hostname == "x.com":
            continue
        try:
            req = urllib.request.Request(url, method="GET", headers={"User-Agent": "slopworks-linkcheck"})
            urllib.request.urlopen(req, timeout=15)
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                errs.append(f"dead source ({e.code}): {url}")
        except Exception as e:  # network hiccup: warn, don't fail
            print(f"warning: could not reach {url}: {e}")
    return errs


# ---------- standup pitches and idea log ----------
DECIDED = {"yes", "no", "later", "vetoed", "needs-ceo", "shipped"}


def idea_errors(ideas):
    """Rules from plans/tracker.md: Coordinator decides, only Shield vetoes, 2+ strong objections go to the CEO."""
    errs = []
    for i in ideas:
        n, st = i.get("id"), i.get("state")
        if st in DECIDED and not (i.get("decided") and i.get("reason") and i.get("decided_by")):
            errs.append(f"idea {n}: a {st} decision needs decided, decided_by, and reason")
        if st == "vetoed" and i.get("decided_by") != "Shield":
            errs.append(f"idea {n}: only Shield can veto")
        if st in ("yes", "no", "later") and i.get("decided_by") != "Coordinator" and i.get("source") != "ceo":
            errs.append(f"idea {n}: only Coordinator decides yes/no/later")
        strong = {c["role"] for c in i.get("comments", []) if c.get("stance") == "oppose" and c.get("strong") and c["role"] != "Coordinator"}
        if st in ("yes", "no", "later") and len(strong) >= 2:
            errs.append(f"idea {n}: {len(strong)} roles strongly disagree, so it must be needs-ceo")
        if i.get("repitch_of") and not i.get("evidence"):
            errs.append(f"idea {n}: a re-pitch needs new evidence")
        errs += ceo_pitch_errors(i)
        errs += decision_errors(i)
    return errs


SCORE_KEYS = ("impact", "evidence", "fit", "effort", "risk", "reversibility")
MIN_EVIDENCE, MAX_RISK = 2, 4


def priority(s):
    """Priority = (Impact x Evidence x Fit) / (Effort x Risk), each scored 1-5."""
    return round(s["impact"] * s["evidence"] * s["fit"] / (s["effort"] * s["risk"]), 2)


def decision_errors(i):
    """Decision record gates for team pitches: scored, checked by Librarian, acceptance criteria set before building,
    security overrides any score, Critic only advises, Trial verifies, uncertain ideas need a passing experiment."""
    n, st, errs = i.get("id"), i.get("state"), []
    s = i.get("scores")
    if s and any(not isinstance(s.get(k), int) or not 1 <= s[k] <= 5 for k in SCORE_KEYS):
        errs.append(f"idea {n}: scores must be 1-5 for {', '.join(SCORE_KEYS)}")
        s = None
    if i.get("challenge") and i["challenge"].get("by") != "Critic":
        errs.append(f"idea {n}: challenge reports come from Critic")
    if i.get("source") == "ceo" or st not in ("yes", "shipped"):
        return errs
    if not s:
        errs.append(f"idea {n}: a yes needs Coordinator's 1-5 scores")
    else:
        if s["evidence"] < MIN_EVIDENCE:
            errs.append(f"idea {n}: evidence score below the minimum ({MIN_EVIDENCE})")
        if s["risk"] > MAX_RISK:
            errs.append(f"idea {n}: risk score above the maximum ({MAX_RISK})")
    if not i.get("librarian_checked"):
        errs.append(f"idea {n}: Librarian must check duplicates and prior work first")
    if not i.get("acceptance_criteria"):
        errs.append(f"idea {n}: set acceptance criteria before building")
    if any(c.get("role") == "Shield" and c.get("stance") == "oppose" for c in i.get("comments", [])):
        errs.append(f"idea {n}: Shield opposes on security, which overrides any score")
    if st == "shipped":
        if i.get("acceptance_verified_by") != "Trial" or not i.get("shipped"):
            errs.append(f"idea {n}: shipped needs what shipped and Trial's acceptance check")
        if s and s["evidence"] < 4 and i.get("experiment_result") != "pass":
            errs.append(f"idea {n}: uncertain (evidence < 4), so it needs a passing experiment before building")
    return errs


def ceo_pitch_errors(i):
    """CEO pitches: the team only advises and Ryno decides, except a unanimous yes, which goes straight into the next sprint."""
    n, st, ceo = i.get("id"), i.get("state"), i.get("source") == "ceo"
    errs = []
    if (i.get("by") == "CEO") != ceo:
        errs.append(f"idea {n}: by CEO and source ceo go together")
    if not ceo:
        return errs
    if st == "vetoed":
        errs.append(f"idea {n}: CEO pitches can't be vetoed; Shield advises and Ryno decides")
    if st in ("advised", "yes", "no", "later") and i.get("decided_by") != "CEO":
        if not all(i.get(k) for k in ("recommendation", "pros", "cons", "target_sprint")) or not i.get("comments"):
            errs.append(f"idea {n}: the huddle report needs comments, recommendation, pros, cons, and target_sprint")
    if st in ("yes", "no", "later") and i.get("decided_by") != "CEO":
        roles = {c["role"] for c in i.get("comments", [])}
        unanimous = st == "yes" and i.get("decided_by") == "Coordinator" and i.get("recommendation") == "yes" \
            and len(roles) >= 2 and all(c.get("stance") == "support" for c in i.get("comments", []))
        if not unanimous:
            errs.append(f"idea {n}: only Ryno decides a CEO pitch, unless the team is unanimous in favor (2+ roles, all support)")
    return errs


def chat_errors(chat, ideas=None):
    """Threads are flat: a reply points at an earlier root message. Times are HH:MM ET."""
    errs, seen = [], {}
    idea_ids = {i["id"] for i in ideas} if ideas is not None else None
    for c in chat:
        r = c.get("reply_to")
        if r is not None:
            if r == c.get("id"):
                errs.append(f"chat {c.get('id')}: can't reply to itself")
            elif r not in seen:
                errs.append(f"chat {c.get('id')}: reply_to {r} isn't an earlier message")
            elif seen[r].get("reply_to"):
                errs.append(f"chat {c.get('id')}: reply to the thread root, not to a reply")
        t = c.get("time")
        if t is not None and not (re.fullmatch(r"\d{2}:\d{2}", t) and int(t[:2]) < 24 and int(t[3:]) < 60):
            errs.append(f"chat {c.get('id')}: time must be HH:MM (ET)")
        if c.get("idea") and idea_ids is not None and c["idea"] not in idea_ids:
            errs.append(f"chat {c.get('id')}: idea {c['idea']} isn't in data/ideas.json")
        seen[c.get("id")] = c
    return errs


def research_errors(notes, schedule, ideas):
    """Standard research reports: facts kept apart from inferences, 1-5 fetched public web pages (no X reads),
    rotation reports on the role's day, proposals carry the full report, demand claims stay hypothesis without real feedback."""
    import datetime
    days = {r["role"]: d["day"] for d in schedule.get("research", []) for r in d["roles"]}
    idea_ids = {i["id"] for i in ideas}
    errs = []
    for n in notes:
        k = f"research {n.get('id')}"
        src = n.get("evidence", [])
        if not 1 <= len(src) <= 5:
            errs.append(f"{k}: needs 1-5 evidence URLs that were actually fetched")
        for u in src:
            host = (urllib.parse.urlparse(u).hostname or "").lower()
            if not u.startswith("https://"):
                errs.append(f"{k}: evidence must be https: {u}")
            if host in ("x.com", "twitter.com") or host.endswith((".x.com", ".twitter.com")):
                errs.append(f"{k}: research uses web pages only, no X reads: {u}")
        if n.get("kind", "rotation") == "rotation":
            try:
                wd = datetime.date.fromisoformat(n.get("date", "")).strftime("%A")
                if days.get(n.get("role")) != wd:
                    errs.append(f"{k}: {n.get('role')} researches on {days.get(n.get('role'), 'no day')}, not {wd}")
            except ValueError:
                errs.append(f"{k}: bad date")
        if n.get("status") == "verified" and not n.get("facts"):
            errs.append(f"{k}: a verified report lists its facts (separate from inferences)")
        if n.get("outcome") == "proposal":
            missing = [f for f in ("existing_work", "opportunity", "alternatives", "effort", "risks", "experiment", "success_metric", "recommendation") if not n.get(f)]
            if missing:
                errs.append(f"{k}: a proposal needs {', '.join(missing)}")
        if n.get("role") == "Advocate" and n.get("status") not in ("hypothesis", "disproved", "stale") and not n.get("reader_feedback"):
            errs.append(f"{k}: demand claims stay hypothesis until real reader feedback exists")
        if not n.get("fresh_until") and n.get("status") != "stale":
            errs.append(f"{k}: set fresh_until (or mark it stale)")
        if n.get("pitch") and n["pitch"] not in idea_ids:
            errs.append(f"{k}: pitch {n['pitch']} isn't in data/ideas.json")
    return errs


def alumni_errors(alumni, schedule, active_bots=None):
    """Offboarded roles: no active bot file, no rotation slot. History stays, archived under bots/alumni/."""
    if active_bots is None:
        active_bots = [f.stem for f in (ROOT / "bots").glob("*.md")]
    rot = {r["role"].lower() for d in schedule.get("research", []) for r in d["roles"]}
    errs = []
    for a in alumni:
        r = a["role"].lower()
        if r in active_bots:
            errs.append(f"offboarded role {a['role']}: move bots/{r}.md to bots/alumni/ (archive, don't delete)")
        if r in rot:
            errs.append(f"offboarded role {a['role']}: still in the research rotation")
        if not a.get("successor"):
            errs.append(f"offboarded role {a['role']}: open work needs a successor")
    return errs


EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF]")


def x_draft_errors(text):
    """Ryno's style for X drafts. Bots never post; drafts go to Ryno in the run report."""
    errs = []
    if text != text.lower():
        errs.append("use lowercase")
    if re.search(r"(^|\s)#\w", text):
        errs.append("no hashtags")
    if len(EMOJI.findall(text)) > 1:
        errs.append("at most one emoji")
    if "slopryno.github.io/slopworks" not in text:
        errs.append("link the site")
    if len(text) > 280:
        errs.append("over 280 characters")
    return errs


# ---------- scans ----------
def secret_hits(text):
    hits = []
    for name, pat in PATTERNS["secrets"].items():
        for m in re.finditer(pat, text):
            if name == "high_entropy" and not (re.search(r"\d", m.group()) and re.search(r"[A-Z]", m.group()) and re.search(r"[a-z]", m.group())):
                continue
            hits.append((name, m.group()[:12] + "…"))
    return hits


def pii_hits(text):
    hits = []
    for m in re.finditer(PATTERNS["pii"]["email"], text):
        if m.group().lower() not in ALLOWED_EMAILS:
            hits.append(("email", m.group()))
    for m in re.finditer(PATTERNS["pii"]["phone"], text):
        hits.append(("phone", m.group()))
    for m in re.finditer(PATTERNS["pii"]["handle"], text):
        h = m.group(1).lower()
        if h in CSS_AT_RULES or h in ALLOWED_HANDLES:
            continue
        if any(m.start() >= e.start() and m.end() <= e.end() for e in re.finditer(PATTERNS["pii"]["email"], text)):
            continue
        hits.append(("handle", m.group()))
    for m in re.finditer(PATTERNS["pii"]["x_url_handle"], text):
        if m.group(1).lower() not in ALLOWED_HANDLES | {"i"}:
            hits.append(("x_url_handle", m.group()))
    return hits


def blocked_file(path):
    return any(re.search(p, path, re.I) for p in PATTERNS["blocked_files"])


class _A11y(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.issues, self.h1, self.tags, self.title = [], 0, set(), False
        self._in_title = False
        self.lang = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.add(tag)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "h1":
            self.h1 += 1
        if tag == "img" and "alt" not in a:
            self.issues.append("img without alt")
        if tag == "script":
            self.issues.append("scripts are not allowed (static, no external code)")
        if tag in ("link",) and a.get("rel") == "stylesheet" and re.match(r"https?://", a.get("href", "")):
            self.issues.append("external stylesheet")
        if tag in ("iframe", "form", "input"):
            self.issues.append(f"<{tag}> not allowed: the site only displays")
        if tag == "title":
            self._in_title = True

    def handle_data(self, data):
        if self._in_title and data.strip():
            self.title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False


def a11y_issues(doc):
    p = _A11y()
    p.feed(doc)
    issues = list(p.issues)
    if not p.lang:
        issues.append("<html> needs lang")
    if not p.title:
        issues.append("missing <title>")
    if p.h1 != 1:
        issues.append(f"needs exactly one <h1> (found {p.h1})")
    if "main" not in p.tags:
        issues.append("missing <main> landmark")
    if 'name="viewport"' not in doc:
        issues.append("missing viewport meta (mobile)")
    return issues


# ---------- review gate ----------
def classify(path):
    if path.startswith("site/assets/avatars/") or path == "scripts/avatars.py":
        return {"Polish", "Shield"}  # avatar changes: design and safety review
    if path.startswith(".github/") or path in ("scripts/patterns.json", "scripts/check.py", "data/schema/allowed_handles.json"):
        return {"Shield", "Atlas"}
    if path.startswith(("bots/", "plans/", "docs/")) or path in ("README.md", "CONTRIBUTING.md", "SECURITY.md", "LICENSE"):
        return {"Lens", "Coordinator"}
    if path.startswith("data/"):
        return {"Lens"}
    return {"Lens", "Trial"}  # site/, scripts/, tests/, anything else


def required_roles(paths):
    need = set()
    for p in paths:
        need |= classify(p)
    return need


def _role(name):
    n = name.strip().split()[0].strip("*:().,").lower() if name.strip() else ""
    return ALIASES.get(n, n.capitalize())


def review_gate(paths, pr_body, comments):
    errs = []
    m = re.search(r"^\s*Maker:\s*(\S+)", pr_body or "", re.M | re.I)
    if not m:
        return ["PR body must name its maker, e.g. 'Maker: Forge'"]
    maker = _role(m.group(1))
    latest = {}
    for c in trusted(comments):
        for kind, who in re.findall(r"^\s*(Sign-off|Block):\s*(\S+)", c.get("body", ""), re.M | re.I):
            latest[_role(who)] = kind.lower()
    for role in sorted(required_roles(paths)):
        if role == maker:
            errs.append(f"{role} made this PR, so it cannot review it; ask another reviewer")
        state = latest.get(role)
        if state == "block":
            errs.append(f"{role} blocked this PR")
        elif state != "sign-off":
            errs.append(f"missing sign-off from {role}")
        elif role == maker:
            errs.append(f"self-approval by {role} does not count")
    return sorted(set(errs))


TRUSTED = {"OWNER", "MEMBER", "COLLABORATOR"}


def trusted(comments):
    """Public repo: anyone can comment, so only comments from people with write access count."""
    return [c for c in comments if c.get("author_association", "OWNER") in TRUSTED]


def block_count(comments, role=None):
    n = {}
    for c in trusted(comments):
        for who in re.findall(r"^\s*Block:\s*(\S+)", c.get("body", ""), re.M | re.I):
            n[_role(who)] = n.get(_role(who), 0) + 1
    return n


# ---------- showcase (i22): additions only, these only tighten ----------
SHOWCASE_PAGES = ["site/index.html", "site/arena/index.html", "site/cases/index.html", "site/challenges/index.html", "site/team/index.html"]
SHOWCASE_LINK = re.compile(r"^(\.\./(chat|arena|cases|challenges)/#[a-z0-9-]+|https://github\.com/slopryno/slopworks/pull/\d+)$")
LIVE_WORDING = re.compile(r"\b(live now|happening now|real-time|in real time|right now)\b", re.I)
DEMO_NOTE = "not advice, not a quote, and not client work"


def anchor_missing(link, root=None):
    """True when a ../page/#id link points at an id the built page does not have."""
    m = re.match(r"^\.\./([a-z]+)/#([a-z0-9-]+)$", link)
    if not m:
        return False
    page = (root or ROOT) / f"site/{m.group(1)}/index.html"
    return not page.exists() or f'id="{m.group(2)}"' not in page.read_text()


def showcase_errors(data, root=None):
    errs = []
    research = {r["id"]: r for r in data.get("research", [])}
    for c in data.get("cases", []):
        for s in c.get("steps", []):
            link = s.get("link")
            if link and not SHOWCASE_LINK.match(link):
                errs.append(f"data/cases.json {c['id']}: link {link} is not a merged PR, chat, arena, case, or challenge link")
            elif link and anchor_missing(link, root):
                errs.append(f"data/cases.json {c['id']}: link {link} points at nothing on the built site")
    for a in data.get("arena", []):
        for rid in a.get("reports", []):
            if rid not in research:
                errs.append(f"data/arena.json {a['id']}: report {rid} is not in data/research.json")
    used = set()
    for c in data.get("challenges", []):
        if c.get("demo") is not True:
            errs.append(f"data/challenges.json {c.get('id')}: every challenge must be demo: true")
        for sec in c.get("sections", []):
            for x in sec.get("items", []):
                used.add(x["research"])
                if x["research"] not in research:
                    errs.append(f"data/challenges.json {c.get('id')}: research {x['research']} is not in data/research.json")
                elif not research[x["research"]]["question"].startswith("Demo challenge"):
                    errs.append(f"data/challenges.json {c.get('id')}: {x['research']} is real research, not a demo report")
    for rid, r in research.items():
        if r["question"].startswith("Demo challenge") and rid not in used:
            errs.append(f"data/research.json {rid}: demo research must belong to a challenge so it is shown labeled Demo")
    page = (root or ROOT) / "site/challenges/index.html"
    if data.get("challenges") and page.exists():
        doc = page.read_text()
        for c in data["challenges"]:
            if f'id="{c["id"]}"' not in doc:
                errs.append(f"site/challenges: {c['id']} missing")
        if "lbl-demo" not in doc or DEMO_NOTE not in doc:
            errs.append("site/challenges: every challenge must show the Demo label and the not-advice note")
    for f in SHOWCASE_PAGES:
        fp = (root or ROOT) / f
        if fp.exists():
            errs += [f"{f}: showcase pages must not claim live activity ('{m}')" for m in sorted({m.group(0) for m in LIVE_WORDING.finditer(fp.read_text())})]
    return errs


# ---------- after-action reviews (Ryno, 2026-10-17): additions only, these only tighten ----------
SHOWCASE_PAGES += ["site/lessons/index.html"]
AAR_FIELDS = ("expected", "actual", "why", "change")


def aar_errors(aars, chat, runs, root=None):
    errs = []
    chat_ids = {c["id"]: c for c in chat}
    run_ids = {r["id"] for r in runs}
    dated = {a["date"] for a in aars}
    for a in aars:
        where = f"data/aars.json {a.get('id')}"
        links = a.get("links", {})
        known = {f"pr:{n}" for n in links.get("prs", [])} | {f"run:{n}" for n in links.get("runs", [])} | {f"commit:{n}" for n in links.get("commits", [])}
        for cid in links.get("chat", []) + [a.get("thread", "")]:
            if cid not in chat_ids:
                errs.append(f"{where}: chat {cid} is not in data/chat.json")
            known.add(f"chat:{cid}")
        known.add(f"pr:{a.get('change_pr')}")
        for k in AAR_FIELDS:
            if not a.get(k, {}).get("cite") or len(a.get(k, {}).get("text", "")) < 10:
                errs.append(f"{where}: '{k}' needs text and at least one cited artifact")
            for ref in a.get(k, {}).get("cite", []):
                kind, _, val = ref.partition(":")
                if kind == "runlog":
                    if val not in run_ids:
                        errs.append(f"{where}: {k} cites run log {val}, which is not in data/runs.json")
                elif kind == "file":
                    if ".." in val or not ((root or ROOT) / val).exists():
                        errs.append(f"{where}: {k} cites missing file {val}")
                elif ref not in known:
                    errs.append(f"{where}: {k} cites {ref}, which is not in its links")
        if f"pr:{a.get('change_pr')}" not in a.get("change", {}).get("cite", []):
            errs.append(f"{where}: 'what we change' must cite the PR that adds the rule, test, or check")
        th = chat_ids.get(a.get("thread"))
        if th and (th.get("reply_to") or not th["text"].startswith("AAR")):
            errs.append(f"{where}: thread {a.get('thread')} must be a Team chat root message that starts with 'AAR'")
        if a.get("status") == "closed":
            if not a.get("fix_pr") or not a.get("closed"):
                errs.append(f"{where}: a closed review needs fix_pr and a closed date")
            elif a["closed"] < a["date"]:
                errs.append(f"{where}: closed before it happened")
            elif a["fix_pr"] not in links.get("prs", []) and a["fix_pr"] != a.get("change_pr"):
                errs.append(f"{where}: fix_pr must be one of its linked PRs")
        elif a.get("closed"):
            errs.append(f"{where}: an open review can't have a closed date")
    for r in runs:
        if r.get("status") not in ("ok", "skipped") and r.get("date") not in dated:
            errs.append(f"data/runs.json {r.get('id')}: a {r.get('status')} run needs a same-day after-action review in data/aars.json")
    return errs


def chat_future_errors(chat, now=None, grace_minutes=10):
    """A Team chat time can't be later than when CI sees it (times are ET, from the clock when written)."""
    import datetime as dt
    try:
        from zoneinfo import ZoneInfo
        et = ZoneInfo("America/New_York")
    except Exception:
        et = dt.timezone(dt.timedelta(hours=-4))
    now = now or dt.datetime.now(et)
    errs = []
    for c in chat:
        if not c.get("time") or not re.match(r"^\d{4}-\d{2}-\d{2}$", c.get("date", "")) or not re.match(r"^\d{2}:\d{2}$", c["time"]):
            continue
        try:
            when = dt.datetime.fromisoformat(f"{c['date']}T{c['time']}").replace(tzinfo=et)
        except ValueError:
            continue
        if when > now + dt.timedelta(minutes=grace_minutes):
            errs.append(f"data/chat.json {c['id']}: time {c['date']} {c['time']} ET is later than now; use the clock when the message is written")
    return errs


# ---------- feeds (i26) and Comms page checks (i28): additions only, these only tighten ----------
HYPE = re.compile(r"\b(revolutionary|game[- ]changing|game changer|world[- ]class|best[- ]in[- ]class|industry[- ]leading|cutting[- ]edge|state[- ]of[- ]the[- ]art|"
                  r"unparalleled|unmatched|guaranteed|10x|number one|blazing[- ]fast|next[- ]gen|groundbreaking)\b|(?<!PR )(?<![#\w])#1(?![\d\w-])", re.I)


def feed_errors(name, text):
    """RSS 2.0 (feed.xml, chat.xml) and JSON Feed 1.1 (feed.json, chat.json) stay valid for readers and routines."""
    errs = []
    if name.endswith(".xml"):
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(text)
        except ET.ParseError as x:
            return [f"{name}: not well-formed XML ({x})"]
        ch = root.find("channel")
        if root.tag != "rss" or root.get("version") != "2.0" or ch is None:
            return [f"{name}: must be RSS 2.0 with a channel"]
        errs += [f"{name}: channel needs {k}" for k in ("title", "link", "description") if not (ch.findtext(k) or "").strip()]
        guids = []
        for n, it in enumerate(ch.findall("item")):
            errs += [f"{name}: item {n} needs {k}" for k in ("title", "link", "guid") if not (it.findtext(k) or "").strip()]
            guids.append(it.findtext("guid"))
        if len(guids) != len(set(guids)):
            errs.append(f"{name}: duplicate guid")
    else:
        try:
            f = json.loads(text)
        except ValueError as x:
            return [f"{name}: not valid JSON ({x})"]
        if f.get("version") != "https://jsonfeed.org/version/1.1" or not f.get("title") or not isinstance(f.get("items"), list):
            return [f"{name}: must be JSON Feed 1.1 with a title and items"]
        ids = [i.get("id") for i in f["items"]]
        errs += [f"{name}: item {n} needs an id and a url" for n, i in enumerate(f["items"]) if not i.get("id") or not i.get("url")]
        if len(ids) != len(set(ids)):
            errs.append(f"{name}: duplicate item id")
    return errs


def page_meta_errors(name, doc):
    errs = []
    t = re.search(r"<title>([^<]*)</title>", doc)
    d = re.search(r'<meta name="description" content="([^"]*)">', doc)
    if not t or not t.group(1).strip():
        errs.append(f"{name}: needs a <title>")
    if not d or not d.group(1).strip():
        errs.append(f"{name}: needs a meta description")
    return errs


def hype_hits(doc):
    """Clear hype only: visible text, with quoted text skipped (official wording is quoted as written)."""
    text = re.sub(r"<[^>]+>", " ", re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", doc, flags=re.S))
    text = re.sub(r"\u201c[^\u201d]*\u201d|&quot;[^&]*&quot;|\"[^\"]*\"|&#x27;[^&]*?&#x27;", " ", text)
    return sorted({m.group(0).lower() for m in HYPE.finditer(text)})


def sitemap_errors(files, root=None):
    sm = (root or ROOT) / "site/sitemap.xml"
    pages = [f for f in files if f.startswith("site/") and f.endswith(".html")]
    if not sm.exists():
        return ["site/sitemap.xml is missing"] if pages else []
    locs = set(re.findall(r"<loc>([^<]+)</loc>", sm.read_text()))
    base = "https://slopryno.github.io/slopworks/"
    want = {base + (f[5:-len("index.html")] if f.endswith("index.html") else f[5:]) for f in pages}
    return [f"site/sitemap.xml: missing {u}" for u in sorted(want - locs)] + [f"site/sitemap.xml: lists {u}, which isn't a page" for u in sorted(locs - want)]


def comms_feed_errors(files, root=None):
    errs = sitemap_errors(files, root)
    for f in files:
        p = (root or ROOT) / f
        if f in ("site/feed.xml", "site/chat.xml", "site/feed.json", "site/chat.json"):
            errs += feed_errors(f, p.read_text())
        elif f.startswith("site/") and f.endswith(".html"):
            doc = p.read_text()
            errs += page_meta_errors(f, doc)
            errs += [f"{f}: hype word '{w}' (see docs/style-guide.md)" for w in hype_hits(doc)]
    return errs


# ---------- guardrail gate ----------
def loosening(path, added, removed):
    real = lambda lines: [l for l in lines if l.strip() and not l.strip().startswith(("#", "//", '"_note"'))]
    if path == "data/schema/allowed_handles.json":
        return any(re.search(r'"[^"]+"', l) for l in real(added))
    if path in ("scripts/patterns.json", "scripts/check.py"):
        return bool(real(removed))
    if path.startswith(".github/workflows/"):
        if any(re.search(r":\s*write\b|write-all|pull_request_target", l) for l in real(added)):
            return True
        return path.endswith("ci.yml") and bool(real(removed))
    if path == ".github/CODEOWNERS" or path == ".gitignore":
        return bool(real(removed))
    if path == "data/ceo_overrides.json":  # Ryno 2026-10-19: CEO overrides are add-only; an edit or removal needs-ceo
        return bool(real(removed))
    return False


def _diff_lines(base, head, path):
    out = subprocess.run(["git", "diff", "-U0", base, head, "--", path], capture_output=True, text=True, cwd=ROOT).stdout
    added = [l[1:] for l in out.splitlines() if l.startswith("+") and not l.startswith("+++")]
    removed = [l[1:] for l in out.splitlines() if l.startswith("-") and not l.startswith("---")]
    return added, removed


# ---------- lean repo (Ryno, 2026-10-17, 8:49 and 8:51 PM ET): additions only, these only tighten ----------
LEAN_TREE_BYTES = 4_000_000  # the tracked tree was 1.9 MB after the cleanup PR; this leaves room, not slack for screenshots
LEAN_FILE_BYTES = 512_000  # per tracked file (CI's 1 MB rule stays as a backstop)
LEAN_IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".bmp", ".tif", ".tiff", ".ico", ".svg")
LEAN_IMAGE_OK = ("site/assets/", "site/badges/")
LEAN_TEMP = re.compile(r"(^|/)(__pycache__|\.cache|\.pytest_cache|tmp|temp|build|dist|node_modules|slopworks-review)/|"
                       r"(^|/)docs/design/review/|"
                       r"(\.(tmp|temp|log|swp|swo|bak|orig|rej|pyc|zip|tar|tgz|gz)|~|(^|/)(\.DS_Store|Thumbs\.db))$", re.I)


def lean_errors(files, sizes, ignored=()):
    """files: tracked paths; sizes: {path: bytes}; ignored: tracked paths that .gitignore says shouldn't be tracked."""
    errs = []
    for f in files:
        if f.lower().endswith(LEAN_IMAGE_EXT) and not f.startswith(LEAN_IMAGE_OK):
            errs.append(f"{f}: images live only in {' or '.join(LEAN_IMAGE_OK)}; screenshots go in the PR's CI artifact, never in git")
        if LEAN_TEMP.search(f):
            errs.append(f"{f}: temp, cache or build output doesn't belong in git")
        if sizes.get(f, 0) > LEAN_FILE_BYTES:
            errs.append(f"{f}: {sizes[f] // 1024} KB is over the {LEAN_FILE_BYTES // 1024} KB per-file budget")
    errs += [f"{f}: tracked but matches .gitignore; remove it from git" for f in ignored]
    total = sum(sizes.get(f, 0) for f in files)
    if total > LEAN_TREE_BYTES:
        errs.append(f"repo: the tracked tree is {total // 1024} KB, over the {LEAN_TREE_BYTES // 1024} KB budget")
    return errs


def tracked_ignored():
    out = subprocess.run(["git", "ls-files", "-ci", "--exclude-standard"], capture_output=True, text=True, cwd=ROOT).stdout
    return [l for l in out.splitlines() if l]


# ---------- runners ----------
def tracked_files():
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=ROOT).stdout.split()
    return [f for f in out if (ROOT / f).is_file()]


def override_errors(root=None):
    """Ryno 2026-10-19 4:31 PM ET: CEO tempo overrides (data/ceo_overrides.json) match their schema and tempo.py's
    rules: named branches, the CEO's quote, an expiry the same ET day. They are add-only (see loosening)."""
    import tempo
    root = root or ROOT
    p = root / "data/ceo_overrides.json"
    if not p.exists():
        return []
    try:
        errs = [f"data/ceo_overrides.json {e}" for e in validate(json.loads(p.read_text()), load_schema("ceo_overrides"))]
        tempo.load_overrides(root)
    except (OSError, ValueError, KeyError, TypeError) as err:
        errs = [f"data/ceo_overrides.json: {err}"]
    return errs


def tempo_errors(root=None):
    """i44 (Ryno 2026-10-18): data/tempo.json must equal what the records give, and no merged PR since the decision
    may have gone over its day's limit (18 a day normal, 3 a day slowed). Refusals are logged in data/refusals.json."""
    import tempo
    root = root or ROOT
    errs = []
    load = lambda n: json.loads((root / f"data/{n}.json").read_text())
    for name in ("tempo", "refusals"):
        try:
            errs += [f"data/{name}.json {e}" for e in validate(load(name), load_schema(name))]
        except (OSError, ValueError) as err:
            errs.append(f"data/{name}.json: {err}")
    if errs:
        return errs
    want = tempo.derive(load("wins"), load("aars"))
    if load("tempo") != want:
        errs.append("data/tempo.json doesn't match data/wins.json and data/aars.json; run scripts/wins.py (or scripts/tempo.py)")
    errs += [f"tempo: {v}" for v in want["violations"]]
    return errs


# ---------- blast radius (Ryno, 2026-10-18 10:48 PM ET, i46): additions only, these only tighten ----------
BLAST_SHARED = ("scripts/", ".github/", "data/schema/", "site/style.css", ".gitignore")  # shared by every page, feed, record or run
BLAST_FIELDS = ("Scope", "Could break", "Rollback", "Size")  # the template in bots/atlas.md
BLAST_SIZES = ("small", "medium", "large")
BLAST_CHECKERS = ("Trial", "Lens")
BLAST_RESULTS = ("matched", "bigger", "smaller")


def blast_shared(paths):
    return [p for p in paths if p.startswith(BLAST_SHARED) or p in BLAST_SHARED]


def blast_note_errors(text):
    """Problems with an Atlas blast-radius note: 'Blast radius: Atlas', then Scope, Could break, Rollback and Size lines."""
    if not re.match(r"^\s*Blast radius:\s*Atlas\b", text or "", re.I):
        return ["the note must start with 'Blast radius: Atlas'"]
    errs = [f"the note needs a '{f}: ...' line" for f in BLAST_FIELDS
            if not re.search(rf"^\s*{re.escape(f)}:\s*\S", text, re.M | re.I)]
    size = re.search(r"^\s*Size:\s*(\w+)", text, re.M | re.I)
    if size and size.group(1).lower() not in BLAST_SIZES:
        errs.append(f"Size must be one of {', '.join(BLAST_SIZES)}, not {size.group(1)!r}")
    return errs


def blast_size(text):
    m = re.search(r"^\s*Size:\s*(small|medium|large)\b", text or "", re.M | re.I)
    return m.group(1).lower() if m else None


def blast_radius_errors(paths, pr_body, comments):
    """A PR that touches shared paths merges only after Atlas, not the maker, posts a blast-radius note on it."""
    shared = blast_shared(paths)
    if not shared:
        return []
    m = re.search(r"^\s*Maker:\s*(\S+)", pr_body or "", re.M | re.I)
    if m and _role(m.group(1)) == "Atlas":
        return ["Atlas made this PR, so it can't assess its own blast radius; another role builds shared-path changes"]
    notes = [c.get("body", "") for c in trusted(comments) if re.match(r"^\s*Blast radius:\s*Atlas\b", c.get("body", ""), re.I)]
    if not notes:
        return [f"missing Atlas blast-radius note (shared paths: {', '.join(shared[:5])}); see bots/atlas.md"]
    return [f"Atlas blast-radius note: {e}" for e in blast_note_errors(notes[-1])]


def blast_check_errors(root=None):
    """data/blast_checks.json: Trial or Lens compares Atlas's prediction with what happened, after the PR merged."""
    root = root or ROOT
    p = root / "data/blast_checks.json"
    if not p.exists():
        return []
    try:
        checks = json.loads(p.read_text())
    except ValueError as err:
        return [f"data/blast_checks.json: {err}"]
    errs = [f"data/blast_checks.json {e}" for e in validate(checks, load_schema("blast_checks"))]
    if errs or not isinstance(checks, list):
        return errs
    merged = {int(str(w.get("pr", "")).rsplit("/", 1)[-1]) for w in json.loads((root / "data/wins.json").read_text())
              if str(w.get("pr", "")).rsplit("/", 1)[-1].isdigit()}
    for c in checks:
        if c.get("pr") not in merged:
            errs.append(f"data/blast_checks.json: PR {c.get('pr')} isn't merged (compare after merge)")
        if c.get("by") not in BLAST_CHECKERS:
            errs.append(f"data/blast_checks.json PR {c.get('pr')}: by must be Trial or Lens")
    seen = [c.get("pr") for c in checks]
    errs += [f"data/blast_checks.json: PR {n} checked twice" for n in sorted({n for n in seen if seen.count(n) > 1})]
    return errs


# ---------- training plan (Ryno, 2026-10-19 7:27 AM ET, i59): additions only, these only tighten ----------
DERIVED = re.compile(r'^\s*Derived:\s*count\s+(\S+)(?:\s+"([^"]*)")?\s*=\s*(\d+)\s*$', re.M)


def derived_count(path, pattern=None, root=None):
    """The one command a Derived: line may name: list items in a JSON file, or lines matching a regex."""
    p = (root or ROOT) / path
    if not str(p.resolve()).startswith(str((root or ROOT).resolve())) or not p.is_file():
        raise ValueError(f"{path} isn't a file in the repo")
    if pattern is not None:
        return sum(1 for l in p.read_text().splitlines() if re.search(pattern, l))
    return len(json.loads(p.read_text()))


def derived_errors(text, root=None):
    """Re-run every 'Derived: count <file> ["regex"] = N' line in a sign-off; a mismatch or a bad line is an error."""
    errs = []
    for path, pattern, want in DERIVED.findall(text or ""):
        try:
            got = derived_count(path, pattern or None, root)
        except (OSError, ValueError, re.error) as err:
            errs.append(f"Derived line for {path}: {err}")
            continue
        if got != int(want):
            errs.append(f"Derived: count {path}{' ' + repr(pattern) if pattern else ''} is {got}, not {want}")
    return errs


def lens_derived_errors(comments, root=None):
    """Lens's latest sign-off must carry at least one Derived: line, and every Derived: line must re-run to its number."""
    lens = [c.get("body", "") for c in trusted(comments) if re.match(r"^\s*Sign-off:\s*(Lens|Verify)\b", c.get("body", ""), re.I)]
    if not lens:
        return []
    if not DERIVED.search(lens[-1]):
        return ["Lens's sign-off needs at least one 'Derived: count <file> = N' line (training plan, i59)"]
    return [f"Lens's sign-off: {e}" for e in derived_errors(lens[-1], root)]


def objective_loop_errors(objectives, ideas):
    """Close the loop: an objective tied to a shipped, rejected or vetoed idea is stale and must be closed or replaced."""
    state = {i["id"]: i.get("state") for i in ideas}
    return [f"data/objectives.json: {o['role']}'s objective is tied to {o['idea']}, which is {state[o['idea']]}; close or replace it"
            for o in objectives if o.get("idea") in state and state[o["idea"]] in ("shipped", "no", "vetoed")]


def drill_errors(root=None):
    """data/drills.json: each re-derive drill names who answered and who checked, and they differ."""
    root = root or ROOT
    p = root / "data/drills.json"
    if not p.exists():
        return []
    try:
        drills = json.loads(p.read_text())
    except ValueError as err:
        return [f"data/drills.json: {err}"]
    errs = [f"data/drills.json {e}" for e in validate(drills, load_schema("drills"))]
    for d in drills if isinstance(drills, list) and not errs else []:
        if d["by"] == d["checked_by"]:
            errs.append(f"data/drills.json {d['id']}: {d['by']} can't check its own drill")
    return errs


def training_errors(root=None):
    root = root or ROOT
    load = lambda n: json.loads((root / f"data/{n}.json").read_text())
    return objective_loop_errors(load("objectives"), load("ideas")) + drill_errors(root)


def run_repo():
    errs = []
    files = tracked_files()
    data = {}
    for name in DATA_FILES:
        p = ROOT / f"data/{name}.json"
        try:
            data[name] = json.loads(p.read_text())
        except Exception as e:
            errs.append(f"data/{name}.json: {e}")
            continue
        errs += [f"data/{name}.json {e}" for e in validate(data[name], load_schema(name))]
        if isinstance(data[name], list):
            errs += [f"data/{name}.json duplicate id {d}" for d in duplicate_ids(data[name])]
    urls = []
    for name in ("updates", "issues"):
        for e in data.get(name, []):
            for key in ("source", "fixed_source"):
                if e.get(key):
                    urls.append(e[key])
                    if bad_source(e[key]):
                        errs.append(f"data/{name}.json {e.get('id')}: {key} {bad_source(e[key])}")
    if os.environ.get("LINKCHECK") == "1":
        errs += live_link_errors(urls)
    for f in files:
        if blocked_file(f):
            errs.append(f"{f}: this file type must never be committed")
        if (ROOT / f).stat().st_size > PATTERNS["max_file_bytes"]:
            errs.append(f"{f}: over 1 MB")
        if f == "scripts/patterns.json" or f.endswith((".png", ".jpg", ".ico", ".webp")):
            continue
        text = (ROOT / f).read_text(errors="ignore")
        errs += [f"{f}: possible secret ({n}: {s})" for n, s in secret_hits(text)]
        if f.startswith(("data/", "site/")) and f != "data/schema/allowed_handles.json":
            errs += [f"{f}: personal data ({n}: {s})" for n, s in pii_hits(text)]
    errs += idea_errors(data.get("ideas", []))
    errs += chat_errors(data.get("chat", []), data.get("ideas", []))
    errs += alumni_errors(data.get("alumni", []), data.get("schedule", {}))
    errs += research_errors(data.get("research", []), data.get("schedule", {}), data.get("ideas", []))
    errs += showcase_errors(data)
    errs += aar_errors(data.get("aars", []), data.get("chat", []), data.get("runs", []))
    errs += chat_future_errors(data.get("chat", []))
    errs += tempo_errors()
    errs += override_errors()
    errs += blast_check_errors()
    errs += training_errors()
    errs += comms_feed_errors(files)
    css = sum((ROOT / f).stat().st_size for f in files if f.startswith("site/") and f.endswith(".css"))
    for f in files:
        if f.startswith("site/") and f.endswith(".html"):
            doc = (ROOT / f).read_text()
            errs += [f"{f}: a11y: {i}" for i in a11y_issues(doc)]
            if len(doc.encode()) + css > PATTERNS["max_page_bytes"]:
                errs.append(f"{f}: page weight over {PATTERNS['max_page_bytes'] // 1024} KB budget")
    sched = ROOT / "site/schedule/index.html"
    if sched.exists() and "schedule" in data:
        page = sched.read_text()
        for item in data["schedule"]["items"]:
            if html_escape(item["when"]) not in page or html_escape(item["what"]) not in page:
                errs.append(f"site/schedule: out of sync with data/schedule.json ({item['id']})")
    errs += lean_errors(files, {f: (ROOT / f).stat().st_size for f in files}, tracked_ignored())
    return errs


def html_escape(s):
    import html as h
    return h.escape(s, quote=True)


def pr_context():
    return os.environ["BASE"], os.environ["HEAD"]


def changed(base, head):
    out = subprocess.run(["git", "diff", "--name-only", base, head], capture_output=True, text=True, cwd=ROOT).stdout
    return [l for l in out.splitlines() if l]


def gh(method, path, body=None):
    req = urllib.request.Request(f"https://api.github.com/repos/{os.environ['REPO']}{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {os.environ['GH_TOKEN']}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read() or b"null")


def flag_ceo(reason):
    n = os.environ["PR"]
    labels = [l["name"] for l in gh("GET", f"/issues/{n}/labels")]
    if "needs-ceo" not in labels:
        gh("POST", f"/issues/{n}/labels", {"labels": ["needs-ceo"]})
        gh("POST", f"/issues/{n}/comments", {"body": f"@slopryno this PR needs your call (`needs-ceo`).\n\n{reason}\n\nNothing here merges until you decide. Add `ceo-approved` to let it through, or close it."})


def review_deferred(pr):
    """A draft can't merge, and marking it ready re-runs CI, so the sign-off check waits for that run."""
    return pr.get("draft") is True


def run_review_gate():
    base, head = pr_context()
    comments = []
    page = 1
    while True:
        batch = gh("GET", f"/issues/{os.environ['PR']}/comments?per_page=100&page={page}")
        comments += batch
        if len(batch) < 100:
            break
        page += 1
    pr = gh("GET", f"/pulls/{os.environ['PR']}")
    if review_deferred(pr):
        print("review-gate: draft PR, sign-offs are checked when it is marked ready for review")
        return []
    errs = review_gate(changed(base, head), pr.get("body") or "", comments)
    errs += blast_radius_errors(changed(base, head), pr.get("body") or "", comments)
    errs += lens_derived_errors(comments)
    repeat = {r: n for r, n in block_count(comments).items() if n >= 2}
    if repeat:
        flag_ceo("Disagreement: " + ", ".join(f"{r} blocked {n} times" for r, n in repeat.items()) + ". Each side's position is in the comments above.")
    return errs


def run_guardrail_gate():
    base, head = pr_context()
    if subprocess.run(["git", "cat-file", "-e", f"{base}:scripts/check.py"], cwd=ROOT).returncode != 0:
        print("guardrail-gate: bootstrap PR (gate not on base yet); skipping")
        return []
    loose = [p for p in changed(base, head) if loosening(p, *_diff_lines(base, head, p))]
    if not loose:
        return []
    labels = [l["name"] for l in gh("GET", f"/issues/{os.environ['PR']}/labels")]
    if "ceo-approved" in labels:
        print("guardrail-gate: loosening approved by CEO label")
        return []
    flag_ceo("Safety case: this PR may loosen a guardrail in: " + ", ".join(f"`{p}`" for p in loose))
    return [f"loosens a guardrail: {p} (labeled needs-ceo)" for p in loose]


def run_paths():
    branch = os.environ.get("BRANCH", "")
    if not branch.startswith("bot/data-"):
        return []
    base, head = pr_context()
    return [f"{p}: bot/data-* PRs may only touch data/ and site/" for p in changed(base, head)
            if not p.startswith(("data/", "site/")) or p.startswith("data/schema/")]


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "repo"
    if cmd == "x-draft":
        problems = x_draft_errors(" ".join(sys.argv[2:]))
        print("\n".join(problems) or "x-draft: ok")
        sys.exit(1 if problems else 0)
    errs = {"repo": run_repo, "paths": run_paths, "review-gate": run_review_gate, "guardrail-gate": run_guardrail_gate}[cmd]()
    for e in errs:
        print(f"::error::{e}")
    print(f"{cmd}: {'FAIL' if errs else 'ok'} ({len(errs)} problems)")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
