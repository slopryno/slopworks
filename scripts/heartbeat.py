#!/usr/bin/env python3
"""Missed-run heartbeat (#148 item 1): fails when the daily run hasn't recorded itself. Standard library only.
  heartbeat.py            exit 1 if data/state.json's last_run is older than the newest daily run that should exist
  heartbeat.py --grace 4  hours after the scheduled run time before today's run counts as missed (default 4)

The scheduled heartbeat workflow runs this. A failed scheduled workflow emails the repo owner, so a missed run is
noticed the same morning without a model call, a token or a write permission (the Oct 22-26 outage left no record).
"""
import argparse, datetime, json, sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
ET = ZoneInfo("America/New_York")


def daily_time(schedule):
    """(hour, minute) of the daily run, from data/schedule.json's daily cron, so no copy of the time drifts."""
    item = next(i for i in schedule["items"] if i["id"] == "daily")
    minute, hour = item["cron"].split()[:2]
    return int(hour), int(minute)


def expected_day(now, run_at, grace):
    """The newest date that should have a run record: today once the run time plus grace has passed, else yesterday."""
    hour, minute = run_at
    due = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + datetime.timedelta(hours=grace)
    return now.date() if now >= due else now.date() - datetime.timedelta(days=1)


def verdict(state, schedule, now, grace=4):
    """(ok, message) for the newest recorded run against the expected day."""
    last = datetime.date.fromisoformat(state["last_run"])
    want = expected_day(now, daily_time(schedule), grace)
    if last >= want:
        return True, f"ok: last run {last}, expected {want} or later"
    gap = (want - last).days
    return False, (f"missed run: no daily run recorded for {want} (last run {last}, {gap} day{'s' if gap != 1 else ''} behind). "
                   "Sweep: record the missed run and open an after-action review.")


def stale_labels(record, today, judging, committed, wanted):
    """Dated labels on the built site that a reader would now read as wrong (Critic S3, 2026-11-13): the site counts
    "so far" and the next oath judging from the newest record, so they freeze when runs stop. Dates are datetime.date."""
    out = []
    if (today - record).days > 1:
        out.append(f"'so far' labels on the weekly recap and home count to {record}, {(today - record).days} days ago")
    if judging < today:
        out.append(f"the quest board's next oath judging, {judging}, has passed")
    if committed != wanted:
        out.append(f"the Team page shows the {committed} avatar set; {today} needs {wanted} (scripts/avatars.py)")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--grace", type=float, default=4)
    a = ap.parse_args(argv)
    state = json.loads((ROOT / "data/state.json").read_text())
    schedule = json.loads((ROOT / "data/schedule.json").read_text())
    now = datetime.datetime.now(ET)
    ok, msg = verdict(state, schedule, now, a.grace)
    print(msg if ok else f"::error::{msg}")
    sys.path.insert(0, str(ROOT / "scripts"))
    import avatars, roadmap  # repo scripts, standard library only
    record = datetime.date.fromisoformat(state.get("updated") or state["last_run"])
    stale = stale_labels(record, now.date(), datetime.date.fromisoformat(roadmap.next_judging(record.isoformat())),
                         avatars.committed_season(), avatars.season_for(now.date()))
    for s in stale:
        print(f"::error::stale label: {s}")
    return 0 if ok and not stale else 1


if __name__ == "__main__":
    sys.exit(main())
