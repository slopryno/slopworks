# 5. Test results and mobile validation (Trial, i41)

Measured on the implementation branch (PR 2, #88) before merge, with `scripts/mobile_audit.py` (headless Chrome, every built page) and the unit tests. Screenshots: 656 files in the PR's `review-shots-88` CI artifact and on the box at `/workspace/slopworks-review/88/`. None are in git.

## Every page (42), light and dark
| Width | Pages | Overflowing | Tap targets under 44px | Text under 12px | Low contrast | Visual defects* | Longest line (est. chars) |
|---|---|---|---|---|---|---|---|
| 320 | 42 | 0 | 0 | 0 | 0 | 0 | 45 |
| 360 | 42 | 0 | 0 | 0 | 0 | 0 | 51 |
| 390 | 42 | 0 | 0 | 0 | 0 | 0 | 56 |
| 430 | 42 | 0 | 0 | 0 | 0 | 0 | 62 |
| 768 | 42 | 0 | 0 | 0 | 0 | 0 | 101 |
| 1024 | 42 | 0 | 0 | 0 | 0 | 0 | 110 |
| 1440 | 42 | 0 | 0 | 0 | 0 | 0 | 110 |

\*Words broken mid-word, boxes overflowing, anything past the right edge, or squeezed text. Light and dark give the same counts.

**Home, words in the first screen:** 69 at 320, 94 at 390, 186 at 768. That's the headline, the explanation, the status line and the three buttons.

## Tests (189, all pass)
- **New, `tests/test_home.py`, 6 tests:**
  - the headline and status come from data (17 roles, merged PRs from `data/wins.json`, the latest PR);
  - completed sprints match the Timeline's Sprint items with a retro, and a running sprint or a shipped decision isn't counted;
  - the tracker comes before the team;
  - there's no "current objective" or live wording, no script, and no form;
  - /prototype/ is retired and nothing links it;
  - home with the CSS is under half the page budget.
- **Unchanged and passing:**
  - `test_contrast` (the lowest pair is dark warn on card, 5.54:1);
  - `test_mobile` (min-width-only queries, clamp type, 360 overflow and tap targets, visual checks at 320, 360 and 390 plus a fallback font);
  - the Timeline, character sheet, feed and lean tests.

## Interactions and keyboard
- The only interaction is the activity rows, which use `details` and `summary`. They work with Enter and Space, and the first row starts open.
- Focus is a visible 3px outline. Nothing depends on hover. With reduced motion, every animation is off.
- **Unverified:** no test with a real screen reader. Semantic markup only: landmarks, one h1, labelled sections, lists.
