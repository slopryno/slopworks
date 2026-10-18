#!/usr/bin/env python3
"""Writes data/wins.json from merged PRs (their 'Maker:' line). Run from the box routine with gh auth before publishing."""
import json, re, subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
ET = ZoneInfo("America/New_York")  # dates are ET, not UTC (AAR 2026-10-17 wins-utc-dates)
ALIAS = {"scout": "Sketch", "verify": "Lens", "privacy": "Shield", "publish": "Forge", "pixel": "Forge", "core": "Forge"}
prs = json.loads(subprocess.run(["gh", "pr", "list", "-R", "slopryno/slopworks", "--state", "merged", "--limit", "1000",
                                 "--json", "number,title,body,mergedAt,createdAt,url"], check=True, capture_output=True, text=True).stdout)
wins = []
for p in sorted(prs, key=lambda p: p["mergedAt"], reverse=True):
    m = re.search(r"^\s*Maker:\s*(\w+)", p["body"] or "", re.M | re.I)
    if m:
        merged = datetime.fromisoformat(p["mergedAt"].replace("Z", "+00:00")).astimezone(ET)
        role = ALIAS.get(m.group(1).lower(), m.group(1).capitalize())
        wins.append({"id": f"pr{p['number']}", "role": role, "title": re.sub(r"\s*\(#\d+\)$", "", p["title"])[:160], "pr": p["url"],
                     "date": merged.strftime("%Y-%m-%d"), "merged": merged.isoformat(timespec="minutes"),
                     "opened": datetime.fromisoformat(p["createdAt"].replace("Z", "+00:00")).astimezone(ET).isoformat(timespec="minutes")})
(ROOT / "data/wins.json").write_text(json.dumps(wins, indent=2, ensure_ascii=False) + "\n")
print(f"wrote {len(wins)} wins")

import tempo  # noqa: E402  (i44: the pace is derived from the same records, right after them)
tempo.write()

# i45 metrics (Analyst): a daily summary of GitHub Actions runs, so CI catches and main failures are on the record.
runs = json.loads(subprocess.run(["gh", "run", "list", "-R", "slopryno/slopworks", "--limit", "1000", "--json",
                                  "name,headBranch,conclusion,status,createdAt"], check=True, capture_output=True, text=True).stdout)
days = {}
for r in runs:
    if r["status"] != "completed" or r["name"] not in ("CI", "Pages"):
        continue
    d = datetime.fromisoformat(r["createdAt"].replace("Z", "+00:00")).astimezone(ET).strftime("%Y-%m-%d")
    kind = "main" if r["headBranch"] == "main" else ("dependabot" if r["headBranch"].startswith("dependabot/") else "bot")
    k = days.setdefault(d, {"date": d, "main_ci_runs": 0, "main_ci_failed": 0, "pages_runs": 0, "pages_failed": 0,
                            "pr_ci_failed_bot": 0, "pr_ci_failed_dependabot": 0})
    if r["name"] == "Pages" and kind == "main":
        k["pages_runs"] += 1; k["pages_failed"] += r["conclusion"] == "failure"
    elif r["name"] == "CI" and kind == "main":
        k["main_ci_runs"] += 1; k["main_ci_failed"] += r["conclusion"] == "failure"
    elif r["name"] == "CI" and r["conclusion"] == "failure":
        k["pr_ci_failed_" + kind] += 1
first = min(r["createdAt"] for r in runs) if runs else None
ci = {"window_start": datetime.fromisoformat(first.replace("Z", "+00:00")).astimezone(ET).isoformat(timespec="minutes") if first else None,
      "days": [days[d] for d in sorted(days)]}
(ROOT / "data/ci.json").write_text(json.dumps(ci, indent=2) + "\n")

import metrics  # noqa: E402
metrics.write()
