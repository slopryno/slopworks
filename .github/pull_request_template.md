<!--
Valid Maker names (scripts/bot.py): Advisor, Advocate, Analyst, Assistant, Atlas,
Comms, Coordinator, Core, Critic, Forge, Gamemaster, Lens, Librarian, Pixel, Polish,
Relay, Scoutmaster, Shield, Sketch, Strategy, Sweep, Trial, Vault.
Aliases: Verify→Lens, Scout→Sketch, Publish→Forge, Privacy→Shield, EA→Assistant.
The maker must not be a required reviewer for the paths this PR touches.
-->
Maker: <!-- role name, e.g. Forge -->

**What:** <!-- one short paragraph -->

**Why / source:** <!-- record, CEO decision paraphrase (no verbatim CEO quotes on the site), or team pitch -->

<!-- For plan-shaped steps (plans/TEMPLATE.md). Leave N/A if this PR is not a plan step. -->
- **You see:** <!-- what changes on the live site, or "nothing visible" -->
- **Verify live:** <!-- page, one of the audit widths, pass condition Trial checks after deploy -->
- **Weight:** <!-- bytes added or removed vs the 100 KB page budget, or "no page change" -->

**Checks (this run):** <!-- preflight / check.py repo, unittest, build.py --check -->

**Sign-offs needed:** <!-- from scripts/bot.py roles for these paths; maker cannot sign off -->

**Whole-team screenshot review (visible PRs):** If this PR changes how a page looks (CSS, deck/sheet/card layout, avatars, `bot/design-*`, or other paint/template sources), every roster role except the maker must open the full-page before/after screenshots at 1280, 1440, 1920 and 390 and post a one-line `Whole-screen verdict: <role>` that states the viewport share and ends with `Flag: none` or `Flag: large empty space`, `broken layout`, or `missing tap cue`. A blocking flag holds the merge. After deploy, the same roles post the same form of verdict again on the PR (Ryno, Fri Nov 27 3:44 PM ET: "Get the whole team to review screenshots every time"). Leave N/A if nothing visible changed.

**Trailers:** Do not add `Co-authored-by:` lines. Keep Claude Code `includeCoAuthoredBy: false`.
