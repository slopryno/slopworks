# 8. Post-deploy report (Sweep, Trial, Coordinator; i41)

Released 2026-10-17. #88 was merged at 10:01 PM ET, and Pages deployed commit 6642e9d. Team chat c289 to c292.

## PRs
- **#87:** kickoff. i41 logged, 13 role reviews and Coordinator's consolidation (c274 to c287), plus the audit, plan and spec. No code.
- **#88:** implementation (deliverable 4). New home, site-wide tokens and type, sprint labels fixed, /prototype/ retired, validation and review docs.
- **#89:** this report, the retro, i41 shipped, and the cap restored.

## Live check (Trial, c289)
- Home, Team, What's new, Known issues, Timeline, a character sheet, Lessons, Work and Under the hood all return 200. /prototype/ returns 404, as intended.
- Every internal link on home resolves to a real page and anchor.
- The live home shows 17 roles, 81 merged PRs and 7 completed sprints, counted when it was built. The served `style.css` has the new tokens.
- CI, Review screenshots and Pages are green on #88.

## Health and reversibility (Sweep, c290)
- **Budgets:** CSS is 15.5 KB, and home is about 31 KB of a 100 KB budget. The tracked tree is under its budget.
- **No screenshots in git:** the review sets for #88 live only in the review-shots-88 artifact and on the box.
- **Revert:** `git revert` on #88 restores the old home and tokens in one PR. It wasn't needed.

## Done
- Home with the hero, status line, featured sprint, tracker panel, team cards and activity rows, all from data.
- Charcoal and ice-white themes that follow the phone's setting.
- 0 issues on every audit check at 7 widths, in light and dark, on 42 pages.
- 6 new tests.

## Recommended, not built
- **A weekly recap:** wait until there are 7 days of history (Analyst, c285).
- **A current objective on cards:** it needs a data field, or the Week 2 quest board, first (Critic, c278).
- **A shorter featured title:** the sprint title comes from the decision record and runs 4 lines on phones. Comms could add a short title field.

## Unverified
- A screen reader pass and a 200% zoom pass.
- A real-device check. All width checks ran in headless Chrome.
- A hand audit of all 273 sign-off comments behind the ledger (see audit.md).
