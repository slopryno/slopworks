#!/usr/bin/env python3
"""The default path for bot work (i30). Each command does a step the bots used to do by hand and got wrong.

  bot.py roles                      required sign-off roles and the branch type for the changed paths
  bot.py branch <slug> [--kind K]   create bot/<kind>-<slug>; the kind comes from the changed paths
  bot.py chat --from R --to R [--reply-to cN] [--idea iN] "text"
                                    append a Team chat message: next id, today's date, the clock time, checked first
  bot.py count <file> [regex]       count list items in a JSON file, or lines matching a regex, for sign-offs
  bot.py pr --maker R --title T --body FILE [--signoff Role=FILE ...] [--review N] [--merge]
                                    run the local checks, open a draft, add the Maker line, post sign-offs,
                                    refuse a self sign-off or a missing required role, then mark ready (and merge)
                                    a design or CSS PR also needs --review N: screenshots of every page,
                                    a full set on the box (scripts/shots.py N, outside the checkout), the PR's
                                    review-shots-N CI artifact, and Polish and Trial sign-offs that
                                    say which screenshots they looked at and what problems they found (AAR 2026-10-17)

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


VISUAL_PATHS = ("site/style.css", "scripts/build.py", "site/assets/", "scripts/avatars.py")
REVIEWERS = ("Polish", "Trial")
REVIEW_LINES = ("Screenshots reviewed:", "Problems found:")


class Refused(Exception):
    pass


# ---------- Tempo (i44, Ryno 2026-10-18 8:35 AM ET): pace rules live in scripts/tempo.py ----------
import tempo  # noqa: E402


def merged_now():
    """Every merged PR from GitHub right now, so the count doesn't depend on wins.json being fresh."""
    prs = json.loads(gh("pr", "list", "--state", "merged", "--limit", "1000", "--json", "number,mergedAt"))
    at = lambda s: datetime.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(ET).isoformat(timespec="minutes")
    return [{"number": p["number"], "merged": at(p["mergedAt"])} for p in prs]


def tempo_gate(prs, aars, now):
    """Refuse a PR over today's limit for the current mode."""
    mode, used, limit = tempo.today(prs, aars, now)
    if used >= limit:
        raise Refused(f"tempo: {mode} mode allows {limit} merged PRs today and {used} already count; "
                      f"wait for tomorrow (ET){' or 10 clean PRs' if mode == 'slowed' else ''} (scripts/tempo.py, data/tempo.json)")
    return mode, used, limit


def main_red(runs):
    """Refuse while the newest finished CI or Pages run on main failed: write its AAR first (it trips the slowdown)."""
    for name in ("CI", "Pages"):
        done = [r for r in runs if r["name"] == name and r["status"] == "completed"]
        if done and done[0]["conclusion"] == "failure":
            raise Refused(f"main is red: the latest {name} run on main failed; fix it and write the same-day AAR first")


def log_refusal(path, branch, reason, now):
    """Append a refusal to data/refusals.json so pre-merge catches are on the record (Trial, c319).
    Only the first line is kept, and a line naming a possible secret or personal data is redacted."""
    line = (reason.strip().splitlines() or [""])[0][:200]
    if check.secret_hits(reason) or check.pii_hits(reason) or "secret" in line or "personal data" in line:
        line = "redacted: the check output named a possible secret or personal data"
    log = json.loads(path.read_text()) if path.exists() else []
    log.append({"at": now.isoformat(timespec="minutes"), "branch": branch[:80], "reason": line})
    path.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n")


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


def needs_visual_review(kind, paths):
    """The /work/ incident (AAR 2026-10-17): a design or CSS change ships only after people look at every page."""
    return kind == "design" or any(p.startswith(VISUAL_PATHS) for p in paths)


IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".bmp", ".tif", ".tiff", ".ico", ".svg")
IMAGE_OK = ("site/assets/", "site/badges/")  # real site assets; nothing else in git is an image (Ryno, 2026-10-17)
ARTIFACT = "review-shots-{n}"  # uploaded by .github/workflows/review-shots.yml, kept 90 days


def review_problems(n, full=None, root=ROOT):
    """What is missing from the review set of PR <n> on the box (scripts/shots.py <n>, outside the checkout):
    every page at every width and theme, listed in its manifest with hashes that still match the files."""
    import shots  # names only; shooting needs Chrome and PIL
    full = Path(full or shots.REVIEW_DIR / str(n))
    mf = full / "manifest.json"
    if not mf.exists():
        return [f"no review set at {full}; run scripts/shots.py {n}"]
    files = json.loads(mf.read_text()).get("files", {})
    have = lambda sub, s: f"{sub}/{s}.webp" in files or any(k.startswith(f"{sub}/{s}.part") for k in files)
    pages = sorted(str(p.relative_to(root / "site")) for p in (root / "site").rglob("*.html"))
    missing = [f"{theme}-{w}/{shots.slug(page)}" for theme in shots.THEMES for w in shots.WIDTHS for page in pages
               if not have(f"{theme}-{w}", shots.slug(page))]
    problems = [f"{len(missing)} screenshots missing for PR {n} (first: {', '.join(missing[:5])}); run scripts/shots.py {n}"] if missing else []
    bad = [k for k, h in files.items() if not (full / k).exists() or shots.sha(full / k) != h]
    if bad:
        problems.append(f"{len(bad)} files in {mf} don't match (first: {', '.join(bad[:3])}); reshoot with scripts/shots.py {n}")
    return problems


def committed_images(paths):
    """Screenshots and other images never go in git; only real site assets do."""
    return [p for p in paths if p.lower().endswith(IMAGE_EXT) and not p.startswith(IMAGE_OK)]


def plan_review(n, kind, paths, signoffs, root=ROOT, full=None, removed=()):
    """Refuse a design or CSS PR without a full screenshot set on the box and real Polish and Trial reviews of it.
    removed: paths this PR deletes; deleting an old screenshot is the point, not a problem."""
    imgs = [p for p in committed_images(paths) if p not in set(removed)]
    if imgs:
        raise Refused(f"images can't be committed outside {', '.join(IMAGE_OK)}: {', '.join(imgs[:5])}; "
                      "review screenshots live on the box and in the PR's CI artifact")
    if not needs_visual_review(kind, paths):
        return
    if n is None:
        raise Refused(f"design or CSS PR ({', '.join(p for p in paths if p.startswith(VISUAL_PATHS)) or 'bot/design-*'}): "
                      "pass --review N with the screenshots from scripts/shots.py N, N being this PR's number")
    problems = review_problems(n, full, root)
    by_role = {role(w): t for w, t in signoffs.items()}
    for r in REVIEWERS:
        text = by_role.get(r)
        if text is None:
            problems.append(f"{r} must sign off on the screenshots")
            continue
        for line in REVIEW_LINES:
            if not re.search(rf"^\s*{re.escape(line)}\s*\S", text, re.M):
                problems.append(f"{r}'s sign-off needs a '{line} ...' line")
    if problems:
        raise Refused("visual review incomplete:\n- " + "\n- ".join(problems))


def artifact_problems(n, artifacts):
    """artifacts: the run's list from the GitHub API. The PR needs its unexpired review-shots-<n> artifact."""
    ok = [a for a in artifacts if a.get("name") == ARTIFACT.format(n=n) and not a.get("expired")]
    return [] if ok else [f"no {ARTIFACT.format(n=n)} artifact on the PR's review-shots run"]


def wait_for_artifact(n, sha, timeout=1200):
    """Wait for review-shots.yml on the PR's head commit and return its artifact problems."""
    end = time.time() + timeout
    while time.time() < end:
        runs = json.loads(gh("run", "list", "--workflow", "review-shots.yml", "--commit", sha, "--json", "databaseId,status,conclusion"))
        done = [r for r in runs if r["status"] == "completed"]
        if done:
            if done[0]["conclusion"] != "success":
                return [f"review-shots run {done[0]['databaseId']} ended {done[0]['conclusion']}"]
            arts = json.loads(gh("api", f"repos/{{owner}}/{{repo}}/actions/runs/{done[0]['databaseId']}/artifacts"))["artifacts"]
            return artifact_problems(n, arts)
        time.sleep(15)
    return [f"review-shots didn't finish within {timeout // 60} minutes"]


def review_note(n, full=None):
    """One line for the PR body: how big the box set is, and the digest of its manifest."""
    import hashlib, shots
    mf = Path(full or shots.REVIEW_DIR / str(n)) / "manifest.json"
    m = json.loads(mf.read_text())
    return (f"\n\nReview screenshots: {m['count']} files ({m['bytes'] // 1024} KB) reviewed on the box, manifest sha256 "
            f"{hashlib.sha256(mf.read_bytes()).hexdigest()[:16]}; the CI copy is the `{ARTIFACT.format(n=n)}` artifact. None are in git.")


def next_pr_number():
    out = gh("api", "repos/{owner}/{repo}/issues?state=all&per_page=1&sort=created&direction=desc")
    items = json.loads(out)
    return (items[0]["number"] if items else 0) + 1


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
    plan_review(a.review, m.group(1), paths, signoffs, removed=[p for p in paths if not (ROOT / p).exists()])
    main_red(json.loads(gh("run", "list", "--branch", "main", "--limit", "10", "--json", "name,status,conclusion")))
    mode, used, limit = tempo_gate(merged_now(), json.loads((ROOT / "data/aars.json").read_text()), datetime.datetime.now(ET))
    print(f"tempo: {mode}, this is PR {used + 1} of {limit} today")
    if needs_visual_review(m.group(1), paths) and next_pr_number() != a.review:
        raise Refused(f"--review {a.review} but this PR will be #{next_pr_number()}; reshoot into that number")
    visual = needs_visual_review(m.group(1), paths)
    if visual:
        body += review_note(a.review)
    local_checks()
    git("push", "-q", "-u", "origin", "HEAD")
    url = gh("pr", "create", "--draft", "--title", a.title, "--body", body).splitlines()[-1]
    n = url.rsplit("/", 1)[-1]
    if visual and int(n) != a.review:
        print(f"PR {n} left as a draft: its screenshots are for #{a.review}, not #{n}")
        sys.exit(1)
    if visual:
        problems = wait_for_artifact(n, git("rev-parse", "HEAD").strip())
        if problems:
            print(f"PR {n} left as a draft: " + "; ".join(problems))
            sys.exit(1)
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
    r.add_argument("--review", type=int)
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
        if a.cmd == "pr":
            log_refusal(ROOT / "data/refusals.json", git("rev-parse", "--abbrev-ref", "HEAD").strip(), str(e), datetime.datetime.now(ET))
        print(f"bot.py: refused: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
