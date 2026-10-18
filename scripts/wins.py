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
                                 "--json", "number,title,body,mergedAt,url"], check=True, capture_output=True, text=True).stdout)
wins = []
for p in sorted(prs, key=lambda p: p["mergedAt"], reverse=True):
    m = re.search(r"^\s*Maker:\s*(\w+)", p["body"] or "", re.M | re.I)
    if m:
        merged = datetime.fromisoformat(p["mergedAt"].replace("Z", "+00:00")).astimezone(ET)
        role = ALIAS.get(m.group(1).lower(), m.group(1).capitalize())
        wins.append({"id": f"pr{p['number']}", "role": role, "title": re.sub(r"\s*\(#\d+\)$", "", p["title"])[:160], "pr": p["url"],
                     "date": merged.strftime("%Y-%m-%d"), "merged": merged.isoformat(timespec="minutes")})
(ROOT / "data/wins.json").write_text(json.dumps(wins, indent=2, ensure_ascii=False) + "\n")
print(f"wrote {len(wins)} wins")

import tempo  # noqa: E402  (i44: the pace is derived from the same records, right after them)
tempo.write()
