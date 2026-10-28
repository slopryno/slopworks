#!/usr/bin/env python3
"""Writes data/xp_ledger.json (i34, Week 1) from the real record only. Game Master owns the rules in data/progression.json;
this script never decides anything: it records events that already happened, each with its evidence and a reviewer who
isn't the earner. Totals and levels are never stored: build.py and the tests compute them from approved entries.

Sources: merged PRs (fetch_merged(): a light list of every merged PR, then the heavy fields in small date chunks: Maker lines, sign-off, Block, and deploy-check comments, added test files),
data/aars.json, data/research.json with data/arena.json, and data/ideas.json. Run with gh auth, like scripts/wins.py.
"""
import json, re, subprocess, sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
ET = ZoneInfo("America/New_York")
REPO = "https://github.com/slopryno/slopworks"
SITE = "https://slopryno.com/"
ALIAS = {"scout": "Sketch", "verify": "Lens", "privacy": "Shield", "publish": "Forge", "pixel": "Forge", "core": "Forge", "relay": "Forge", "vault": "Forge"}
TRUSTED = {"OWNER", "MEMBER", "COLLABORATOR"}  # same rule as check.trusted (AAR review-gate-trust)
ROLES = {f.stem.capitalize() for f in (ROOT / "bots").glob("*.md")}
load = lambda n: json.loads((ROOT / f"data/{n}.json").read_text())


def role(name):
    n = name.strip().split()[0].strip("*:().,").lower()
    return ALIAS.get(n, n.capitalize())


def et(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(ET).isoformat(timespec="minutes")


def xp_for(prog, who, kind):
    t = prog["tables"]
    return t.get(who, {}).get(kind, t["default"].get(kind))


def anchors(files):
    """Where each id lives on the built site, so evidence links land on a real anchor."""
    where = {}
    for k in sorted(files, key=lambda k: ("archive" in k, k)):
        if k.endswith(".html"):
            for i in re.findall(r'id="([^"]+)"', files[k]):
                where.setdefault(i, k.replace("index.html", ""))
    return where


def ledger(prs, prog, files):
    where = anchors(files)
    site = lambda i: SITE + where[i] + "#" + i if i in where else None  # no anchor, no evidence, no entry
    out = []

    def add(kind, who, task, reviewer, evidence, ts, status="approved", note=None, key=None):
        if who not in ROLES or not evidence:
            return
        base = xp_for(prog, who, kind)
        if base is None:
            return
        if reviewer == who or not reviewer:
            status, note, reviewer = "pending", "no reviewer other than the earner yet", None
        e = {"id": f"{kind}-{key}", "agent": who, "task": task[:160], "type": kind, "base_xp": base,
             "quality_pct": prog["quality"]["default_pct"], "reviewer": reviewer or "none", "evidence": evidence,
             "timestamp": ts, "status": status}
        if note:
            e["note"] = note
        out.append(e)

    makers, signers = {}, {}
    for p in sorted(prs, key=lambda p: p["mergedAt"]):
        n = p["number"]
        m = re.search(r"^\s*Maker:\s*(\w+)", p["body"] or "", re.M | re.I)
        if not m:
            continue
        maker = role(m.group(1))
        makers[n] = maker
        title = re.sub(r"\s*\(#\d+\)$", "", p["title"])
        signs = []
        for c in p["comments"]:
            if c.get("authorAssociation") not in TRUSTED:
                continue
            for who in re.findall(r"^\s*Sign-off:\s*(\S+)", c["body"], re.M | re.I):
                r = role(who)
                if r != maker and r not in [s for s, _ in signs]:
                    signs.append((r, c))
            if re.match(r"\s*(Trial\s+)?deploy check", c["body"], re.I):
                add("deploy_check", "Trial", f"Deploy check on #{n}: {title}", maker, c["url"], et(c["createdAt"]), key=f"pr{n}")
        signers[n] = [s for s, _ in signs]
        first = next((s for s in ("Lens", "Trial", "Coordinator", "Shield", "Atlas", "Polish") if s in signers[n]), signers[n][0] if signers[n] else None)
        add("pr_merged", maker, f"#{n}: {title}", first, p["url"], et(p["mergedAt"]), key=f"pr{n}")
        for r, c in signs:
            add("signoff", r, f"Signed off #{n}: {title}", maker, c["url"], et(c["createdAt"]), key=f"pr{n}-{r.lower()}")
        for f in p.get("files", []):
            path = f["path"]
            if f.get("changeType") == "ADDED" and re.match(r"tests/test_\w+\.py$", path):
                live = (ROOT / path).exists()
                author = "Trial" if live and (ROOT / path).read_text().lstrip('"\' ').startswith("Trial's tests") else maker
                rev = next((s for s in ["Lens"] + signers[n] if s != author), maker if maker != author else None)
                add("ci_test_added", author, f"Added {path} in #{n}", rev, p["url"], et(p["mergedAt"]),
                    "approved" if live else "reversed", None if live else "the test file no longer runs in CI", key=path.split("/")[1][:-3])

    # Daily sign-off cap (Critic's rule 2, c168): over-cap entries stay visible as rejected, never hidden.
    cap, seen = prog["events"]["signoff"]["cap_per_day"], Counter()
    for e in sorted((e for e in out if e["type"] == "signoff"), key=lambda e: e["timestamp"]):
        seen[(e["agent"], e["timestamp"][:10])] += 1
        if seen[(e["agent"], e["timestamp"][:10])] > cap and e["status"] == "approved":
            e["status"], e["note"] = "rejected", f"over the daily sign-off cap ({cap})"

    comments = {p["number"]: p["comments"] for p in prs}
    for a in load("aars"):
        if a["status"] != "closed":
            continue
        owner = role(a["owner"])
        rev = "Coordinator" if owner == "Lens" else "Lens"
        add("aar_written", owner, f"AAR: {a['title']}", rev, site(a["id"]), a["closed"], key=a["id"])
        fix = a.get("fix_pr")
        if fix in makers:
            add("aar_fix", makers[fix], f"Fixed what AAR {a['id']} found (#{fix})", owner if owner != makers[fix] else "Lens",
                f"{REPO}/pull/{fix}", a["closed"], key=a["id"])
        if a["trigger"] == "block-upheld":
            for n in a["links"]["prs"]:
                for c in comments.get(n, []):
                    if c.get("authorAssociation") in TRUSTED and re.match(rf"\s*Block:\s*{owner}\b", c["body"], re.I):
                        add("block_upheld", owner, f"Block on #{n} proven right: {a['title']}", makers.get(n), c["url"], et(c["createdAt"]), key=f"pr{n}")

    ideas = {i["id"]: i for i in load("ideas")}
    accepted = lambda i: i in ideas and ideas[i]["state"] in ("yes", "shipped")
    in_round = {r: a["decision"] for a in load("arena") for r in a["reports"]}
    for r in load("research"):
        dec = in_round.get(r["id"]) or r.get("pitch")
        if dec and accepted(dec) and r["id"] in where:
            add("research_accepted", role(r["role"]), f"Research: {r['question']}", ideas[dec].get("decided_by"), site(r["id"]), r["date"], key=r["id"])
    for i in ideas.values():
        if i["state"] == "shipped" and i.get("source") != "ceo" and i["id"] in where:
            add("pitch_shipped", role(i["by"]), f"Pitch {i['id']} shipped: {i['problem']}", i.get("acceptance_verified_by"), site(i["id"]), i["decided"], key=i["id"])
    return sorted(out, key=lambda e: (e["timestamp"], e["id"]))


FIELDS = "number,title,body,mergedAt,url,comments,files"


def gh_json(run, *args, tries=3):
    """One gh call parsed as JSON, retried: GitHub's API 502s on heavy PR queries now and then."""
    for i in range(tries):
        try:
            return json.loads(run(["gh", *args], check=True, capture_output=True, text=True).stdout)
        except subprocess.CalledProcessError:
            if i == tries - 1:
                raise


def fetch_merged(run=subprocess.run, chunk=40):
    """Every merged PR with the fields ledger() reads. One 200-PR call with comments and files 502'd (Oct 27) and
    silently capped the list at 200, so: list numbers and created dates first (cheap, up to 1000), then fetch the heavy
    fields per window of about `chunk` PRs by created date, and fail if any listed PR is missing."""
    repo = ["-R", "slopryno/slopworks", "--state", "merged"]
    light = gh_json(run, "pr", "list", *repo, "--limit", "1000", "--json", "number,createdAt")
    days = sorted(p["createdAt"][:10] for p in light)
    prs = {}
    for i in range(0, len(days), chunk):
        q = f"created:{days[i]}..{days[min(i + chunk, len(days)) - 1]}"
        for p in gh_json(run, "pr", "list", *repo, "--limit", "1000", "--search", q, "--json", FIELDS):
            prs[p["number"]] = p
    missing = sorted({p["number"] for p in light} - set(prs))
    if missing:
        raise SystemExit(f"xp.py: merged PRs missing from the chunked fetch: {missing}")
    return sorted(prs.values(), key=lambda p: p["number"])


if __name__ == "__main__":
    import build
    prs = fetch_merged()
    entries = ledger(prs, load("progression"), build.build())
    (ROOT / "data/xp_ledger.json").write_text(json.dumps(entries, separators=(",", ":"), ensure_ascii=False) + "\n")
    print(f"wrote {len(entries)} XP entries from {len(prs)} merged PRs: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(e['status'] for e in entries).items())))
