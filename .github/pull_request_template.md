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

**Trailers:** Do not add `Co-authored-by:` lines. Keep Claude Code `includeCoAuthoredBy: false`.
