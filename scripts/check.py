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
    """Weekly research notes: 2-3 takeaways in own words, 1-5 fetched public web pages (no X reads), on the role's rotation day."""
    import datetime
    days = {r["role"]: d["day"] for d in schedule.get("research", []) for r in d["roles"]}
    idea_ids = {i["id"] for i in ideas}
    errs = []
    for n in notes:
        k = f"research {n.get('id')}"
        if not 2 <= len(n.get("takeaways", [])) <= 3:
            errs.append(f"{k}: needs 2-3 takeaways")
        src = n.get("sources", [])
        if not 1 <= len(src) <= 5:
            errs.append(f"{k}: needs 1-5 sources (about 5 pages max per session)")
        for u in src:
            host = (urllib.parse.urlparse(u).hostname or "").lower()
            if not u.startswith("https://"):
                errs.append(f"{k}: source must be https: {u}")
            if host in ("x.com", "twitter.com") or host.endswith((".x.com", ".twitter.com")):
                errs.append(f"{k}: research uses web pages only, no X reads: {u}")
        try:
            wd = datetime.date.fromisoformat(n.get("date", "")).strftime("%A")
            if days.get(n.get("role")) != wd:
                errs.append(f"{k}: {n.get('role')} researches on {days.get(n.get('role'), 'no day')}, not {wd}")
        except ValueError:
            errs.append(f"{k}: bad date")
        if n.get("pitch") and n["pitch"] not in idea_ids:
            errs.append(f"{k}: pitch {n['pitch']} isn't in data/ideas.json")
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
    return False


def _diff_lines(base, head, path):
    out = subprocess.run(["git", "diff", "-U0", base, head, "--", path], capture_output=True, text=True, cwd=ROOT).stdout
    added = [l[1:] for l in out.splitlines() if l.startswith("+") and not l.startswith("+++")]
    removed = [l[1:] for l in out.splitlines() if l.startswith("-") and not l.startswith("---")]
    return added, removed


# ---------- runners ----------
def tracked_files():
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=ROOT).stdout.split()
    return [f for f in out if (ROOT / f).is_file()]


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
    errs += research_errors(data.get("research", []), data.get("schedule", {}), data.get("ideas", []))
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
