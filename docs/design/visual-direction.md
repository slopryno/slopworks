# Visual direction (i40, prototype only)

Owned by Polish. It comes from Ryno's pitch i40, an outside Mobile Readiness and Visual Redesign Audit, and the huddle in Team chat (c260 to c266). The audit reviewed the old site: a 7-link nav, home shown as an updates list, and no phone-width testing. Most of its mobile checklist shipped in #72 to #74. What's new here is the palette, the type, and a team-first home.

**Status:** one prototype page at [/prototype/](https://slopryno.github.io/slopworks/prototype/). The live site and `site/style.css` are unchanged until Ryno decides on a rollout.

## Palette

Dark first. Accents carry meaning and are used sparingly: lime means done, orange means blocked or a lesson, violet means research. Color is never the only cue: every chip has a word, and status also changes shape (filled, square, dashed).

| Token | Dark | Light | Use |
|---|---|---|---|
| bg | Charcoal #131317 | Ice white #F4F4F0 | page |
| card | #1F1F25 | #FFFFFF | cards |
| fg | Ice white #F4F4F0 | Obsidian #0B0B0D | text |
| muted | #96969F | #55555E | meta, times |
| done | Electric lime #C6FF3D | #3B6000 | shipped, progress, focus ring |
| block | Signal orange #FF6338 | #B2360F | blockers, lessons |
| research | Violet #9B8CFF | #5A48D0 | research |
| line | #3A3A43 | #D6D6D0 | borders only, never text |

Lime and orange fail as text on a light background (lime on ice white is 1.07:1), so light mode uses darker inks of the same hues. Steel gray fails on light too (3.31:1), so light mode uses #55555E.

**Too dark? (Ryno, 9:32 PM ET, Team chat c267 to c273).** The page follows the phone's setting: light unless the system asks for dark. In dark, the first version was 88.5% near-black at 390 px, and its cards stood apart from the page by only 1.10:1 (border 1.46:1). The page is now charcoal #131317 instead of Obsidian #0B0B0D, cards are #1F1F25 with a #3A3A43 border (1.65:1 against the page), and muted text lifts from Steel gray #85858F (4.49:1 on the new card, a fail) to #96969F. Light mode and the accents are unchanged.

## Contrast (WCAG 2.x, normal text needs 4.5:1)

| Text | on bg | on card |
|---|---|---|
| Ice white, dark | 16.81 | 14.87 |
| #96969F, dark | 6.32 | 5.59 |
| Electric lime, dark | 15.68 | 13.87 |
| Signal orange, dark | 6.26 | 5.54 |
| Violet, dark | 6.70 | 5.92 |
| Obsidian on a lime chip | 16.64 | |
| Obsidian, light | 17.83 | 19.66 |
| #55555E, light | 6.69 | 7.38 |
| #3B6000, light | 6.66 | 7.34 |
| #B2360F, light | 5.56 | 6.13 |
| #5A48D0, light | 5.82 | 6.42 |

Lowest pair: signal orange on a dark card, 5.54:1. `tests/test_prototype.py` checks every pair, so a token change that drops one below 4.5:1 fails CI.

## Type

System fonts only, so there are no font files and no extra bytes (Critic cut the self-hosted subset).

- **Display:** the system sans at weight 850, tight tracking (-0.035em), `clamp(2.1rem, 1.4rem + 3.6vw, 3.4rem)`. Only the one hero headline.
- **Body:** `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`, 17px, line height 1.55, lines up to about 62 characters.
- **Mono:** `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`, for PR numbers, XP, and times. Never under 12px.

## Spacing and shape

- 4px base: .25, .5, .75, 1, 1.5, 2.75rem. Sections are 2.75rem apart.
- Cards: 14px radius, 1px line border, 1rem padding. Chips: pill for kinds, square for blockers, dashed for research and reported.
- Every tap target is at least 44px tall. The focus ring is a 3px lime outline.

## Components on the prototype

1. **Hero:** "The bots are building. The receipts are public." Three counts from the repo, with an honest "as of" time: the last merged PR, not a live clock.
2. **Character cards:** the six roles with the most recent merged work. Each shows the avatar, role, the real level and XP from the ledger, a progress bar, and the latest merged PR. There's no quest slot until quests exist in Week 2 (Game Master, c264).
3. **Activity:** the latest 8 Timeline records. Tap a row to open who did it, what it was, and the evidence link (`details` and `summary`, no script). The first row starts open, so the pattern is visible.
4. **What's new:** 3 editorial cards. Confirmed is a filled chip with a check mark; reported is a dashed chip with a question mark. It also shows the real totals.

## Cut by Critic (c263)

Web fonts, glow and gradients, live dots and pulsing indicators, a "current quest" slot, more than one interaction pattern, a wall of news cards, accent colors without a meaning, and a design mission per role (it stays out of the role files until a rollout is decided). Wireframes were skipped, per Ryno.

## Checked (Trial, c265)

The prototype was measured with `scripts/mobile_audit.py` at 320, 360, 390, 430, 768, 1024 and 1440, plus 844 (phone landscape), in light and dark. Results: 0 overflow, 0 tap targets under 44px, 0 text under 12px, 0 low-contrast text. Reduced motion is honored, and the page has no animation. The page is about 17 KB of HTML, including its inline CSS. Screenshots are in the PR's CI artifact, never in git.

## Not decided

A site-wide rollout, a light-or-dark default, and whether Team chat, Lessons, and the other pages adopt the cards. Ryno decides after looking at the prototype on his phone.
