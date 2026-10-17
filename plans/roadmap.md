# Roadmap

Owned by Coordinator. Ordered by priority; `plans/direction.md` wins on conflicts. Engineering ships at most one feature PR a week, Polish at most one design PR a week.

## Sprint 2026-W42 (CEO-approved, set up the team for success)
- [x] Draft-first PR flow so review-gate re-runs after sign-offs, with no manual CI reruns (#9)
- [x] Dependabot #1-#4 replaced by one reviewed ops PR; action updates come monthly, grouped (#10)
- [x] Source expansion: official changelog and RSS, docs, status page, and an X rate-limit fallback (this PR)
- [x] CEO-approved: checkout v7 in ci.yml (#13)
- [x] CEO-approved: @xai added to the handle allowlist (#14)

## Now (first two weeks)
- [ ] Daily run live, with Behind the scenes and Team chat updated from real handoffs
- [ ] Post-deploy check by Trial, with automatic revert by Sweep
- [ ] Monday CEO brief, weekly release tag, Friday retro

## Slopworks RPG (Ryno's pitch i34, huddle c163 to c179; rules owned by Game Master)
- [x] Week 1: progression rules (`data/progression.json`), XP ledger backfilled from real records (`scripts/xp.py`), character sheets and How XP works (#67, #68)
- [ ] Week 2: daily, weekly, and level-up quests ('no meaningful opportunity found' counts), reviewer quality grades, recorded preventions (Lens +75, Trial +40)
- [ ] Week 3: the first team raid, picked from Reliability Raid, Bug Hunt, Trust Protocol, Experience Upgrade, Efficiency Challenge, Research Expedition
- [ ] Week 4: audit and rebalance, then skill trees (three branches, four milestones per role) and optional level-up animations that respect reduced motion
- Each week starts on evidence, not the calendar. Rule changes go through Team chat with the affected roles and Critic first.

## Next
- [ ] Filter updates and issues by area (design backlog d1)
- [ ] Weekly digest pages under `site/weekly/` (d3)
- [ ] README badges generated from repo data (d6) and a social preview image (d2)
- [ ] Automated contrast check in CI (d4)
- [ ] Before and after screenshots for design PRs (d5)
- [ ] Monthly State of Slopworks page

## Later
- [ ] Shareable Grok Bot template that follows the feed
- [ ] Split roles into separate bots once the loop is stable (the bot earns its place)

## Done
- [x] v1 site, feeds, CI gates, 30-day backfill (2026-10-15)
