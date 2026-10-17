#!/usr/bin/env python3
"""The default path for bot work (i30). Each command does a step the bots used to do by hand and got wrong.

  bot.py roles                      required sign-off roles and the branch type for the changed paths
  bot.py branch <slug> [--kind K]   create bot/<kind>-<slug>; the kind comes from the changed paths
  bot.py chat --from R --to R [--reply-to cN] [--idea iN] "text"
                                    append a Team chat message: next id, today's date, the clock time, checked first
  bot.py count <file> [regex]       count list items in a JSON file, or lines matching a regex, for sign-offs
  bot.py pr --maker R --title T --body FILE [--signoff Role=FILE ...] [--merge]
                                    run the local checks, open a draft, add the Maker line, post sign-offs,
                                    refuse a self sign-off or a missing required role, then mark ready (and merge)

CI stays the backstop (review-gate, path rule, guardrail-gate). This helper only makes the right path the easy one.
"""
import argparse, datetime, json, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check  # noqa: E402  (single source of truth for roles and path rules)

KINDS = ("data", "design", "feature", "ops")
SPECIALISTS = {"Pixel", "Core", "Vault", "Relay"}  # Forge specialists (bots/forge.md)
ET = __import__("zoneinfo").ZoneInfo("America/New_York")
OPS_PATHS = (".github/", "scripts/check.py", "scripts/patterns.json", "data/schema/allowed_handles.json")


class Refused(Exception):
    pass


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def changed_paths(base="origin/main"):
    """Committed, staged, unstaged, and untracked changes against base."""
    paths = set(l for l in git("diff", "--name-only", base).splitlines() if l)
    paths |= set(l for l in git("ls-files", "--others", "--exclude-standard").splitlines() if l)
    return sorted(paths)


def data_ok(path):
    """Same rule as check.run_paths: bot/data-* may touch only data/ and site/, never data/schema/."""
    return path.startswith(("data/", "site/")) and not path.startswith("data/schema/")


def branch_kind(paths):
    if not paths:
        raise Refused("no changed paths yet: make the change first, then pick the branch")
    if all(data_ok(p) for p in paths):
        return "data"
    if any(p.startswith(OPS_PATHS) or p in OPS_PATHS for p in paths):
        return "ops"
    return "feature"


def check_kind(kind, paths):
    if kind not in KINDS:
        raise Refused(f"kind must be one of {', '.join(KINDS)}")
    bad = [p for p in paths if not data_ok(p)]
    if kind == "data" and bad:
        raise Refused(f"bot/data-* can't carry {', '.join(bad)}; use bot/{branch_kind(paths)}-*")


def role(name):
    r = check._role(name)
    known = {f.stem.capitalize() for f in (ROOT / "bots").glob("*.md")} | SPECIALISTS
    if r not in known:
        raise Refused(f"unknown role {name!r}; known roles: {', '.join(sorted(known))}")
    return r


def plan_signoffs(maker, paths, signoffs):
    """signoffs: {role: text}. Returns the comment bodies to post, or raises if any gate would fail."""
    maker = role(maker)
    need = check.required_roles(paths)
    got = {}
    for who, text in signoffs.items():
        r = role(who)
        if r == maker:
            raise Refused(f"{maker} made this PR, so it can't sign it off; ask another role")
        body = text if re.match(r"^\s*Sign-off:", text) else f"Sign-off: {r}\n{text}"
        if check._role(re.match(r"^\s*Sign-off:\s*(\S+)", body).group(1)) != r:
            raise Refused(f"the sign-off text for {r} names another role")
        got[r] = body
    if maker in need:
        raise Refused(f"{maker} is a required reviewer for these paths, so it can't be the maker")
    missing = sorted(need - set(got))
    if missing:
        raise Refused(f"missing sign-off from {', '.join(missing)} (required for these paths: {', '.join(sorted(need))})")
    return [got[r] for r in sorted(got)]


def with_maker(body, maker):
    m = re.search(r"^\s*Maker:\s*(\S+)", body, re.M | re.I)
    if m:
        if check._role(m.group(1)) != role(maker):
            raise Refused(f"the body says Maker: {m.group(1)}, but --maker is {maker}")
        return body
    return f"Maker: {role(maker)}\n\n{body}"


def new_chat(chat, ideas, frm, to, text, reply_to=None, idea=None, now=None):
    now = now or datetime.datetime.now(ET)
    nums = [int(c["id"][1:]) for c in chat if re.fullmatch(r"c\d+", c.get("id", ""))]
    msg = {"id": f"c{max(nums, default=0) + 1}", "date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M"),
           "from": frm, "to": to, "text": text}
    if reply_to:
        msg["reply_to"] = reply_to
    if idea:
        msg["idea"] = idea
    errs = check.validate([msg], check.load_schema("chat")) + check.chat_errors(chat + [msg], ideas)
    if errs:
        raise Refused("; ".join(errs))
    return msg


def count(path, pattern=None):
    p = Path(path)
    if pattern:
        return sum(1 for l in p.read_text().splitlines() if re.search(pattern, l))
    data = json.loads(p.read_text())
    return len(data)


def local_checks():
    for cmd in (["python3", "scripts/build.py"], ["python3", "scripts/check.py"], ["python3", "scripts/build.py", "--check"],
                ["python3", "-m", "unittest", "discover", "-s", "tests", "-q"]):
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if r.returncode:
            raise Refused(f"{' '.join(cmd)} failed:\n{(r.stdout + r.stderr)[-1500:]}")
    if git("status", "--porcelain"):
        raise Refused("the build changed files or there are uncommitted changes; commit them first")


def gh(*args):
    return subprocess.run(["gh", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def cmd_pr(a):
    branch = git("rev-parse", "--abbrev-ref", "HEAD").strip()
    m = re.fullmatch(r"bot/(data|design|feature|ops)-[\w.-]+", branch)
    if not m:
        raise Refused(f"branch {branch!r} isn't bot/<kind>-<slug>; run bot.py branch <slug>")
    paths = changed_paths()
    check_kind(m.group(1), paths)
    body = with_maker(Path(a.body).read_text(), a.maker)
    signoffs = {}
    for s in a.signoff or []:
        who, _, f = s.partition("=")
        signoffs[who] = Path(f).read_text()
    comments = plan_signoffs(a.maker, paths, signoffs)  # refuse before anything is pushed
    local_checks()
    git("push", "-q", "-u", "origin", "HEAD")
    url = gh("pr", "create", "--draft", "--title", a.title, "--body", body).splitlines()[-1]
    n = url.rsplit("/", 1)[-1]
    for c in comments:
        gh("pr", "comment", n, "--body", c)
    gh("pr", "ready", n)
    print(f"PR {n} ready: {url}")
    if not a.merge:
        return
    time.sleep(6)
    subprocess.run(["gh", "pr", "checks", n, "--watch", "--interval", "8"], cwd=ROOT, capture_output=True)
    states = set(re.findall(r"\t(pass|fail|pending|skipping)\t", subprocess.run(["gh", "pr", "checks", n], cwd=ROOT, capture_output=True, text=True).stdout))
    labels = json.loads(gh("pr", "view", n, "--json", "labels"))["labels"]
    if "pass" not in states or states - {"pass", "skipping"} or labels:
        print(f"PR {n} not merged: checks {sorted(states)}, labels {[l['name'] for l in labels]}")
        sys.exit(1)
    gh("pr", "merge", n, "--squash", "--delete-branch")
    git("checkout", "-q", "main")
    git("pull", "-q")
    print(f"merged {n}: {git('log', '--oneline', '-1').strip()}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="bot.py", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("roles")
    b = sub.add_parser("branch"); b.add_argument("slug"); b.add_argument("--kind")
    c = sub.add_parser("chat"); c.add_argument("--from", dest="frm", required=True); c.add_argument("--to", required=True)
    c.add_argument("--reply-to"); c.add_argument("--idea"); c.add_argument("text")
    n = sub.add_parser("count"); n.add_argument("file"); n.add_argument("pattern", nargs="?")
    r = sub.add_parser("pr"); r.add_argument("--maker", required=True); r.add_argument("--title", required=True)
    r.add_argument("--body", required=True); r.add_argument("--signoff", action="append"); r.add_argument("--merge", action="store_true")
    a = p.parse_args(argv)
    try:
        if a.cmd == "roles":
            paths = changed_paths()
            print(f"paths: {len(paths)}\nbranch: bot/{branch_kind(paths)}-*\nsign-offs: {', '.join(sorted(check.required_roles(paths)))}")
        elif a.cmd == "branch":
            paths = changed_paths()
            kind = a.kind or branch_kind(paths)
            check_kind(kind, paths)
            git("checkout", "-q", "-b", f"bot/{kind}-{a.slug}")
            print(f"bot/{kind}-{a.slug}")
        elif a.cmd == "chat":
            f = ROOT / "data/chat.json"
            chat = json.loads(f.read_text())
            ideas = json.loads((ROOT / "data/ideas.json").read_text())
            msg = new_chat(chat, ideas, a.frm, a.to, a.text, a.reply_to, a.idea)
            f.write_text(json.dumps(chat + [msg], indent=2, ensure_ascii=False) + "\n")
            print(f"{msg['id']} {msg['time']} ET")
        elif a.cmd == "count":
            print(f"{a.file}: {count(a.file, a.pattern)}")
        elif a.cmd == "pr":
            cmd_pr(a)
    except Refused as e:
        print(f"bot.py: refused: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
