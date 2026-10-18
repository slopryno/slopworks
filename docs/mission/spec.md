# 3. Visual and responsive spec (Polish, i41)

It extends [the visual direction](../design/visual-direction.md) with the "too dark?" result (c273). Sketch set the composition: one loud headline, a quiet mono status line, one featured card, receipts as the visual unit (c279).

## Tokens (site/style.css)
| Token | Light | Dark | Use |
|---|---|---|---|
| bg | #F4F4F0 | #131317 | page |
| card | #FFFFFF | #1F1F25 | cards, hero panels |
| fg | #0B0B0D | #F4F4F0 | text, link text |
| muted | #57606a | #96969F | meta |
| line | #D6D6D0 | #3A3A43 | borders |
| link | #0B0B0D | #F4F4F0 | link text (underlined) |
| ok | #3B6000 | #C6FF3D | done, shipped, progress, link underline |
| warn | #B2360F | #FF6338 | reported, blocked, lessons |
| bad | #B2360F | #FF6338 | vetoed, errors |
| accent | #5A48D0 | #9B8CFF | research, focus ring |

Every text token is at least 4.5:1 on bg and card in both themes (`tests/test_contrast.py`).

## Type
- **Sans:** the system stack, 16px body.
- **Headline:** weight 800, letter spacing -.035em, `clamp(2.1rem, 1.4rem + 3.6vw, 3.4rem)` on home and the standard clamp elsewhere.
- **Mono:** `ui-monospace` for times, PR numbers and XP, never under 12.8px.

## Spacing, surfaces, components
- Cards have a 12px radius and a 1px line border. Panels on home use the card color.
- **Buttons:** at least 44px tall, 8px radius. Primary is filled with fg on bg; secondary is outlined.
- **Nav:** unchanged, 4 links, a 44px row height, the current page underlined.
- **Role card:** avatar 48px, name, specialization, level and XP in mono, a lime progress bar, and the latest merged PR with its number and date. No current-objective slot.
- **Activity row (`details`):**
  - The chip shape and word carry the type: Shipped and Sprint are filled lime; Decision, Case file and Team are outlined; Lesson is a square orange; Research is dashed violet; Demo keeps its label.
  - The summary is at least 44px tall. The first row starts open.
- **Tracker panel:** counts (updates, confirmed vs reported, open known issues, entries dropped by Verify), the 3 newest updates with ✓ Confirmed (filled) or ? Reported (dashed), and links to all updates, known issues, Behind the scenes and the Research Arena.
- **States:** focus is a 3px accent outline; hover only underlines (nothing depends on it); active has no change; reduced motion turns off every animation, including the avatar hop.

## Responsive
- **Phones:** one column, base styles for 320 px and up.
- **From 40rem (640px):** team cards in 2 columns, the CTA buttons inline.
- **From 64rem (1024px):** team cards in 3 columns. The text width stays at 52rem, so lines stay readable at 1440.
- Every width query is min-width (`tests/test_mobile.py`).
