# Direction (owned by the CEO, Ryno)

Edit this file any time, or tell Slopbot in chat and it will open a PR. Coordinator reads it before every run and planning cycle. It outranks everything except the guardrails.

## Goals (starting set)
1. **Be the most trustworthy Grok Bot tracker.** Accuracy beats speed and volume. Every item sourced, labeled confirmed or reported.
2. **Show the team at work.** Behind the scenes and Team chat should make it obvious how bots built, checked, and shipped each change.
3. **Get more polished every week.** The Monday design score should trend up.
4. **Stay cheap and calm.** Free tier, one run a day, quiet days stay quiet.
5. **Ping the CEO only for disagreements and safety cases.**
6. **Be a showcase of the team's work (Ryno, 2026-10-17).** Visitors may be potential clients for AI automation work. The site should answer what the team can do, why its approach is different, and what working with it is like, and strive to impress. Design around: "What can I make this team do, and what can it prove it accomplished?" Use real traces, label every demo or simulation, and leave out metrics that don't exist. Keep the pitch soft: it's a showcase, not a storefront (GitHub Pages terms). Visitors give no input or feedback for now; the static, no-script rules and CI guardrails stay.
7. **UX first: mobile first, simple and elegant (Ryno, 2026-10-17, i36).** Design for what makes the site best for visitors to view and navigate, starting with phones: base styles for small screens, then min-width steps up to tablet and desktop. Every page works at 360px wide with no sideways scrolling and tap targets of at least 44px, measured, not guessed. Keep it simple: a few top-level sections, one clear path and title per page, one type scale, a restrained palette, generous whitespace, and the same components everywhere. Cut clutter, keep every URL working, and don't make desktop worse.
8. **Repo to remain lean, clean and organized (Ryno, 2026-10-17, 8:51 PM ET; owner: Sweep).** A clear top-level layout (see the README's Repo layout), consistent names, and no stray, duplicate, dead, temp or build files. Check budgets in CI: a tracked-tree size, a per-file size, and no files that `.gitignore` excludes. Sweep runs a monthly repo hygiene pass. History is never rewritten.
9. **Never save screenshots or other temp files to the repo (Ryno, 2026-10-17, 8:49 PM ET).** Not even small ones. Review screenshots live only in the PR's CI artifact or on the box under `/workspace`, outside the checkout. The only images in git are real site assets in `site/assets/` and `site/badges/`.

## Priorities this month
- Showcase v1 (CEO pitch i21, plan i22): label set, Research Arena, case files, outcome-led landing, Living Team, and labeled demo challenges. Impact Ledger and Build Observatory later, once real measurements and artifacts exist.
- Ship daily runs reliably for 14 days.
- Area filters and weekly digest pages.
- README showcase polish.

## Stop doing
- (nothing yet)
