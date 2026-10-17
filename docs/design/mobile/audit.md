# Mobile and UX audit (i36, i37)

Owned by Polish and User Advocate. Measured on 2026-10-17 with `scripts/mobile_audit.py`: headless Chrome loads every built page (37) in a frame of the exact width and counts what breaks. Raw numbers: [before.json](before.json). The site itself stays script-free; the harness lives in `scripts/` and runs outside `site/`.

## How it counts
- **Overflow:** the page is wider than the screen (`scrollWidth > clientWidth`), so it scrolls sideways.
- **Tap targets:** every visible link, summary, button, and label smaller than 44 x 44 CSS px. Links inside a sentence or a block of text are exempt, as WCAG 2.5.5 allows, and counted separately as inline links. List rows, nav links, chips, and summaries are not exempt.
- **Words above the fold:** visible words in the first screen (390 x 844).
- **Line length:** an estimate (paragraph width divided by half the font size), so read it as a rough guide.
- **Contrast:** text-color against background ratios under 4.5:1, outside links, in light mode and in forced dark mode at 390. CI's contrast test checks the theme colors too.
- **Taps from home, nav items, page weight:** counted from the built HTML.

## Before (commit 49d4137, #70)

| Width | Pages overflowing | Undersized tap targets | Pages with any | Inline links (exempt) | Wide tables without their own scroll |
|---|---|---|---|---|---|
| 360 | 3 (challenges 79 px, updates 50 px, issues 15 px) | 622 | 37 of 37 | 927 | 0 |
| 390 | 2 (challenges 49 px, updates 20 px) | 626 | 37 | 927 | 0 |
| 414 | 1 (challenges 25 px) | 629 | 37 | 927 | 0 |
| 768 | 0 | 626 | 37 | 927 | 0 |
| 1280 | 0 | 613 | 37 | 927 | 0 |

- **Where the small targets are (390):** 481 in the header nav (13 links per page, each 34 px tall) and 145 in page content. The content ones are thread "replies" toggles, "How to read the labels", filter chips, jump links, source links, and archive older/newer links.
- **Navigation:** 13 nav items in two rows (8 showcase, 5 tracker and ops), plus the brand link. The header is 211 px tall on phones (360 to 414) and 148 px from 768 up, so a phone loses about a quarter of its first screen before the page title.
- **Taps from home:** 1 to every top page (all are in the nav), 2 to a character sheet or How XP works.
- **Words above the fold at 390:** home 137, Timeline 160, Team 166, Team chat 144, Case files 167, Research Arena 177, a character sheet 130.
- **Type:** smallest text 12 px, and no text under 12 px. Estimated longest line: about 56 characters at 390 and about 113 at 1280, so desktop lines run long.
- **Contrast:** 0 text elements under 4.5:1 in light mode or forced dark mode.
- **Tables:** 25 in all. 3 are wider than a 360 screen (2 in the Research Arena, 1 on How XP works), and all 3 already scroll inside their own container.
- **CSS:** 10,700 bytes. 3 `max-width` media queries, 0 `min-width`, so it's desktop-first. 4 animations, with reduced-motion rules in CSS, and all 20 avatar SVGs carry their own reduced-motion rule.
- **Weight:** the heaviest page is the Research Arena, 83,000 bytes with CSS and avatars, under the 102,400 budget. Avatars add up to 24,330 bytes on the Team page (17 SVGs).

## What we'll change (proposal in Team chat)
1. A simpler nav with 4 to 5 top items, so the header fits on one row on phones, and every nav link is at least 44 px tall.
2. Hub pages for Work and Under the hood, so deeper pages are one tap from a hub, plus a back link on deep pages. Every existing URL keeps working.
3. A landing page with one headline, three short answers, and two or three entry points.
4. Mobile-first CSS: base styles for phones, `min-width` steps up, `clamp()` type and spacing, and tables that scroll in their own box. Fix the 3 overflowing pages.
5. Bigger toggles and chips (44 px), and less repeated chrome (the header credit line, the label legend on every page).
6. Add-only CI: a 360 px test for overflow and tap targets on every page, plus a lint for min-width-first CSS.
