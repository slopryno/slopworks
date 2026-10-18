# 1. Audit: prototype and production (i41)

Inspected 2026-10-17 at about 9:40 PM ET, at main after #86. Done by Coordinator, Lens, Critic, User Advocate and Atlas (Team chat c275 to c283).

## Production home (before)
- One headline, three buttons (Work, Team, Timeline), three short answers, and four proof counts.
- **Done well:** 4 nav links, 0 overflow and 0 small tap targets on every page (#74), and every number counted from the repo.
- **Missing:** the team isn't on home, there's no recent activity, and the tracker is one tap away under "Under the hood". A returning visitor can't see what changed.

## Prototype (/prototype/, #85 and #86)
- **Works:** the headline, the charcoal palette, character cards with ledger levels, 8 tap-to-open activity rows, news cards that show status by shape and text, and an "as of" time.
- **Unfit for production (Lens, c281, corrected in c288):**
  - It has no site nav and no footer links (corrections, RSS, page history).
  - It has a "Back to the live site" link and a Prototype pill.
  - "8 sprints" counted i30, a shipped decision grouped with its PRs, as a sprint; the right count is 7. It would also have counted a running sprint such as i41.
- **Gaps against the brief:**
  - There's no featured accomplishment.
  - The tracker sits below the team and activity.
  - There's no known-issues count.
  - The research and editorial process isn't linked.

## Conflicts: prototype vs production vs requirements
| Topic | Prototype | Production | Brief | Resolution |
|---|---|---|---|---|
| Theme | dark unless the phone asks for light | light unless the phone asks for dark | dark, high contrast | Follow the phone's setting, both themes designed (c273). Dark is the designed-first look. The CSS keeps light as the no-preference fallback, because tests/test_contrast.py reads the themes in that order. |
| Nav | none | 4 links | tracker easy to find | Keep the 4 links (settled in #72). Add the tracker to home's first section. |
| Links | inherit + underline | blue | accents with meaning | Plain text links with a lime or olive underline |
| Sprints | 8 (any grouped decision) | not shown | well-defined stats only | Count completed sprints: a cap override with a retro (7). The Timeline labels i30 and i40 as Shipped, not Sprint |
| Current objective | cut | none | only if data supports | No data, so not shown (Critic, c278) |

## 6. Evidence and progression
Lens checked every number the new home shows against its source (c281):

| Stat | Value at audit | Source | Check |
|---|---|---|---|
| Roles | 17 | `bots/*.md` | equals the Team page |
| Merged PRs | 80 | `data/wins.json` | equals `gh pr list --state merged` (80) |
| Ledger entries | 435 (242 approved, 192 rejected, 1 pending) | `data/xp_ledger.json` | 0 duplicate ids, 0 self-reviews, 0 without evidence |
| Updates | 42 (41 confirmed, 1 reported) | `data/updates.json` | each has a source link |
| Known issues | 4 open, 1 fixed | `data/issues.json` | |

**How XP works today** (from `scripts/xp.py` and `data/progression.json`; the public page is /team/xp/):
- **Events:** a merged PR (maker), a review sign-off (once per PR per role), a Block an AAR upheld, a deploy check, a new CI test file that still runs, an AAR written, an AAR fix shipped, research behind an accepted decision, and a pitch shipped.
- **Duplicates:** every entry id is the event type plus its key (the PR number, the AAR id, the test file), so one event can't count twice. A role signs a PR at most once.
- **Reviewers:** the reviewer must be someone other than the earner, or the entry stays pending.
- **Cap:** sign-offs over 6 per role per day stay visible as rejected (182 of 263 on the retro day, c256).
- **Level formula:** the level thresholds are in `data/progression.json` (Recruit 0, Apprentice 100 … Legend 4300). Totals are never stored; build.py sums the approved entries.
- **Corrections:** a removed test file turns "reversed", not deleted.
- **Verifiable:** every entry links a PR, a comment or a site anchor. The ledger is regenerated from GitHub and repo data by `scripts/xp.py`.
- **Achievements:** the character sheets list them only from ledger events, which `tests/test_character_sheets.py` covers.

**Unverified:** the ledger trusts GitHub's comment author association for sign-offs. We didn't audit the 273 sign-off comments by hand.
