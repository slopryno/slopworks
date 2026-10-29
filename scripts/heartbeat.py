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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--grace", type=float, default=4)
    a = ap.parse_args(argv)
    state = json.loads((ROOT / "data/state.json").read_text())
    schedule = json.loads((ROOT / "data/schedule.json").read_text())
    ok, msg = verdict(state, schedule, datetime.datetime.now(ET), a.grace)
    print(msg if ok else f"::error::{msg}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
