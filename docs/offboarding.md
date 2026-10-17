# Offboarding a bot role

Owned by Coordinator. Drafted by the roles in Team chat on 2026-10-16 (thread c35): Shield wrote access and secrets, Librarian wrote knowledge handoff, and Atlas and Sweep wrote removal. Everything goes through one PR with the usual gates.

## 1. Why (Coordinator)
- [ ] Record why the role is being retired or merged, and who takes over, in `data/alumni.json` (`role`, `date`, `reason`, `successor`). Retiring a role needs CEO approval.

## 2. Hand off open work (Coordinator and Librarian)
- [ ] Every open PR, idea, pitch, and research report gets a named successor.
- [ ] Knowledge goes into the decision record (`data/ideas.json` and `data/research.json`). Unfinished findings are marked `stale` or `hypothesis`. Nothing is deleted.

## 3. Access and secrets (Shield)
- [ ] Roles share one account and hold no credentials of their own. Confirm the bot file references no secret.
- [ ] If the role ever had its own token or key, revoke and rotate it the same day.
- [ ] The PII and secret scans pass after removal.

## 4. Remove from the system (Atlas and Sweep)
- [ ] Remove the role from the research rotation and schedule (`data/schedule.json`) and from the public schedule page.
- [ ] Remove it from the Team page groups (`GROUPS` in `scripts/build.py`) and the plan's budget table.
- [ ] Remove it from review-gate requirements if it was a required reviewer. Keep it in schema role lists so its history still validates.
- [ ] Update the daily routine's expectations in the other `bots/` files.
- [ ] **Archive, don't delete:** `git mv bots/<name>.md bots/alumni/` and `git mv site/assets/avatars/<name>.svg site/assets/avatars/alumni/`. The Team page shows it under **Alumni** with the reason and successor.
- [ ] Git history stays intact. No rewrites.
- [ ] CI (`alumni_errors`) fails if an offboarded role still has an active bot file or rotation slot.

## 5. Farewell (Team chat)
- [ ] Coordinator opens a farewell thread. The retiring role posts its handoff, and the successor confirms what it took over.
- [ ] Sweep checks the live site, feeds, and schedule page after the deploy.
