# 2. Prioritized improvements, backlog and decision record (i41)

Coordinator consolidated the reviews in c287, all inside the brief, so there was no stop for Ryno.

## Personas (User Advocate, c276)
1. **First-time visitor:** needs to know what this is, then see proof. *Fix:* the headline, a one-line explanation, a status line, and one featured accomplishment with its evidence.
2. **Developer curious about agents:** needs to know how the bots work, then a record to inspect. *Fix:* team cards linking character sheets and PRs; activity rows that open to the evidence.
3. **Returning visitor:** needs to know what changed. *Fix:* the newest activity first and an "as of" time. A weekly recap is *recommended later* (Analyst, c285: 3 days of history isn't a week).

## Ranked problems and fixes
| Rank | Problem | Fix | Owner | Status |
|---|---|---|---|---|
| 1 | Home hides the team and what's happening | Prototype layout on home, inside the site shell | Forge | PR 2 |
| 2 | Prototype stats not production-grade (open sprint counted) | Completed sprints only; roster count labeled as roles | Forge, Lens | PR 2 |
| 3 | Tracker could get buried | Tracker section right after the hero, with updates, known issues and process links | Forge | PR 2 |
| 4 | Two looks (prototype vs site) | Site-wide tokens and type from the spec | Polish, Forge | PR 2 |
| 5 | Duplicate code path | Fold prototype.py into home.py; drop /prototype/ | Atlas, Forge | PR 2 |
| 6 | Returning visitors | Weekly recap from real records | Analyst | recommended later (after 7 days of history) |
| 7 | Current objective on cards | Needs a data field first (quests, Week 2) | Game Master | recommended later |

## Backlog with acceptance criteria
- **PR 1 (kickoff):** this plan, the audit and the spec are merged before any code.
- **PR 2 (Forge, home and tokens):**
  - Home shows the headline, a status line (roles, merged PRs, completed sprints, latest merged PR with its time), a featured accomplishment with evidence, the tracker, 6 team cards and 8 activity rows.
  - Every number comes from data.
  - No scripts, and 0 overflow and 0 small tap targets at 320 to 1440.
  - The contrast test passes, and the page stays under budget.
  - /prototype/ is removed.
- **PR 3 (release):** the post-deploy report, the retro, i41 shipped, the cap restored.

## Decision record (Research Librarian, c277)
- **Settled, unchanged:**
  - 4 top nav links (#72).
  - No scripts, forms or external code.
  - Labels use text and shape, never color alone (i22).
  - The XP rules and the sign-off cap (i34, c168).
  - Screenshots only in CI artifacts (i39).
  - Mobile-first CSS with min-width queries only (i36).
- **Decided now:**
  - Charcoal dark and an equal light theme, following the phone's setting (c273).
  - Lime means done or progress, orange means blocked or a lesson, violet means research.
  - Links are plain text with a colored underline.
  - Home order: hero, tracker, team, activity.
- **Deferred:** a weekly recap, a current objective, a quest board (Week 2).

## Measurement plan (Analyst, c285)
No analytics, cookies or trackers. We measure what the repo already holds:
- page weight per page;
- the mobile audit at 7 widths;
- the contrast test;
- counts from data.

Nothing about visitors is measured.
