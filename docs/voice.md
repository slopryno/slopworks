# Voice and tone

Owned by Comms, which has the final say on wording (docs/style-guide.md). Slopworks describes a professional team: roles own work, decide, and ship with receipts. This guide covers new copy. Chat, the archives, and quotes are verbatim records and are never rewritten.

## Rules
1. **Describe the team as an engineering org.** Roles own things, decide and ship. Do: "Shield owns security and privacy." Don't: "Shield guards the doors."
2. **Be confident and exact.** Lead with the fact or number. No hedging, no self-deprecation. Do: "6 of 12 entries." Don't: "we tried our best."
3. **Own mistakes plainly and blamelessly.** Say what happened, why, and what changed. Do: "Four design sign-offs were given without a visual review." Don't: "oops, we goofed."
4. **Keep game words inside the XP system.** XP, levels and quests live on character sheets and the XP page, never in descriptions of the team. Do: "Level 3 · Specialist." Don't: "keep the dice fair."
5. **One sentence per card.** Detail goes behind a tap to expand, one tap from the card. Do: "I check every fact against a public source." Don't: a 74-word bio.
6. **Use the role's display name everywhere.** Do: "Lens verifies it." Don't: "I'm Verify."
7. **Slopworks is the brand, not a put-down.** Don't use "slop", "sloppy", "mess" or "goof" about the work.
8. **No hype or cutesy closers.** Don't: "Bring your best and let's have fun with it!", "awesome", "epic". The banned hype list in docs/style-guide.md still applies.

## Word limits
Comms set these from the measured counts in the 2026-10-19 visual review. The numbers live in `data/word_limits.json`, and `scripts/check.py` enforces them on every PR.

| Area | Limit (words) |
| --- | --- |
| Page title | 8 |
| Page lede | 25 |
| First phone screen (390×844, closed details excluded) | 110 |
| Section intro (the paragraph after a heading) | 25 |
| Hub card blurb | 20 |
| Home role card | 30 |
| Team role card, open text | 60 |
| Role bio | 25 |
| Tracker entry summary | 30 |
| Case or challenge card, open text | 80 |
| Lesson (AAR) card, open text | 60 |
| Activity item | 25 |
| Metric card | 15 |
| Table caption or sub-note | 25 |
| Definition or how-it-works step | 25 |
| Any paragraph | 45 |
| Footer | 30 |
| Text behind one tap to expand | 250 |

Records are exempt: Team chat and its archives, the timeline archives, quoted records in blockquotes, and the required disclaimer.

## How it's enforced (code first, then CI, then this page)
- `data/word_limits.json` lists each area's selector and limit. A page joins `enforced_pages` in the PR that trims it, so CI never goes red on a page nobody has trimmed yet. Page titles hold on every page now.
- `data/voice.json` lists banned phrases (rules 4, 6, 7 and 8). They fail on enforced pages, outside records and quotes, and in role bios once bios are enforced.
- New tracker summaries (added from 2026-10-21) are held to 30 words at the source, in `data/updates.json`.
- The first-screen budget needs a browser, so `tests/test_words.py` measures it with `scripts/mobile_audit.py` at 390×844.
- Both files are add-only. Removing a page, an area or a phrase, raising a limit, or adding an exemption is loosening: the guardrail gate labels the PR `needs-ceo`.
- Rules 1 to 3 need judgment. Comms adds a `Voice checked:` line to its sign-off on copy PRs.
