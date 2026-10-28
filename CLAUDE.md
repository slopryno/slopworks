# Claude Code guide for Slopworks

Claude Code loads this file every session. It is for local edits (code and plans) so they match how the bot team works. Rules live in the linked docs and in `scripts/check.py`; this page only points at them. Do not invent team rules.

## Before you push or open a PR

Run the full local gate:

```bash
./scripts/preflight.sh
```

It runs the same three checks CI runs: `python3 scripts/check.py repo`, the full unittest suite, and `python3 scripts/build.py --check`. Fix every failure before opening a PR. Optional: a Claude Code `PreToolUse` / stop hook that runs `./scripts/preflight.sh` before `git push` or `gh pr create` (do not commit a `.claude/` settings file unless the team adds one on purpose).

## Team model

- One daily routine plays the roles in [`bots/`](bots/). Each role has its own file (for example [`bots/forge.md`](bots/forge.md), [`bots/lens.md`](bots/lens.md), [`bots/assistant.md`](bots/assistant.md)).
- Every PR names a **Maker** in the body. A different role must sign it off. A maker never signs off its own work (`scripts/check.py` `review_gate`, `scripts/bot.py` `plan_signoffs`).
- Required reviewers depend on the paths (see README “How it works” and `check.classify`): data → Lens; site/scripts/tests → Lens + Trial; bots/plans/docs → Lens + Coordinator; `.github/` and safety paths → Shield + Atlas.
- Shared paths also need Atlas’s blast-radius note (`bots/atlas.md`). Atlas cannot be the maker of a shared-path PR.

## PR body: `Maker:` line

The first non-empty maker line must look like:

```text
Maker: Forge
```

`scripts/bot.py` accepts only these names (bot files under `bots/*.md`, plus Forge’s specialists from `SPECIALISTS` in `scripts/bot.py`):

Advisor, Advocate, Analyst, Assistant, Atlas, Comms, Coordinator, Core, Critic, Forge, Gamemaster, Lens, Librarian, Pixel, Polish, Relay, Scoutmaster, Shield, Sketch, Strategy, Sweep, Trial, Vault

Aliases that resolve to a known role: `Verify` → Lens, `Scout` → Sketch, `Publish` → Forge, `Privacy` → Shield, `EA` → Assistant (`scripts/check.py` `ALIASES`).

Use a real role that fits the change. Forge (or its specialists Core / Pixel / Vault / Relay) for builds and tooling; Sketch for plans; Sweep for ops data; and so on. Do not invent names.

Use the [pull request template](.github/pull_request_template.md). Fill every blank that applies.

## Branches

- Name: `bot/<kind>-<slug>` where `<kind>` is one of `data`, `design`, `feature`, `ops` (`scripts/bot.py` `KINDS`).
- Prefer `python3 scripts/bot.py branch <slug>` so the kind matches the changed paths.
- A `bot/data-*` branch may touch only `data/` and `site/` (never `data/schema/`, never `tests/`, never scripts). A test change must use `feature`, `ops`, or `design` instead (`check_kind` / CI `bot/data-* path rule`).

## CEO decisions and labels

- Only the Executive Assistant ([`bots/assistant.md`](bots/assistant.md)) applies the `ceo-approved` label, and only after Ryno’s explicit yes for that PR, quoted word for word with its ET time on the PR and logged in `data/ceo_decisions.json`. Claude must never add `ceo-approved` or `needs-ceo`.
- Removing or loosening any check, workflow permission, allowlist entry, CODEOWNERS line, word limit, or test assertion needs Ryno’s yes (`guardrail-gate`). Additive tightening is fine.
- Ryno’s verbatim words stay off the site. Put decisions and quotes only on PRs and in the records (`data/ceo_decisions.json`, `data/ceo_overrides.json`, AARs). `scripts/ceo_quotes.py` and `check.py repo` fail a build that still shows one. See [`bots/assistant.md`](bots/assistant.md).

## Site and repo constraints

Full list: [`docs/constraints.md`](docs/constraints.md), [`docs/style-guide.md`](docs/style-guide.md), [`docs/voice.md`](docs/voice.md), [`docs/brand.md`](docs/brand.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), [`SECURITY.md`](SECURITY.md).

- Real data only. Static GitHub Pages site: no scripts, no external code, no visitor input.
- Page budget: 100 KB per page (HTML + CSS + images the page loads); `scripts/patterns.json` `max_page_bytes` / `page_weight_errors`.
- Accessibility and layout: mobile first; audits at the seven widths used in design review (see [`docs/design/visual-direction.md`](docs/design/visual-direction.md) and `scripts/mobile_audit.py`).
- Keep the repo lean: no screenshots, temp, cache, or build output in git (Ryno’s lean-tree rules in `check.py`; screenshots stay on the box / PR artifact). Images only under `site/assets/` and `site/badges/`.
- No PII or secrets. Shield owns personal data; patterns and the handle allowlist are enforced in CI.

## Custom domain

The live site is **https://slopryno.com/** (HTTPS enforced). `www` and the old `slopryno.github.io/slopworks` URL redirect there. Keep `site/CNAME` with `slopryno.com` — do not delete it on deploy. Prefer relative links and the repo’s `BASE` / site URL helpers over hard-coding the old github.io path. Live checks use `https://slopryno.com/`.

## Tempo

Normal pace: up to 6 PRs per sprint, 3 sprints a day, hard cap **18 merges a day** (`scripts/tempo.py`). Slowed mode drops to 3 PRs a day after a trip. Scoped CEO overrides are add-only in `data/ceo_overrides.json` and expire the same ET day.

## Plans and local notes

New plan steps use [`plans/TEMPLATE.md`](plans/TEMPLATE.md): each step needs **You see**, **Verify live**, and **Weight** lines. Ship through `scripts/bot.py pr` with the required sign-offs for the paths you touch.

Team rules stay in this shared `CLAUDE.md`. Personal or machine-only notes go in `CLAUDE.local.md` (gitignored; Claude Code loads it on that machine). Plan drafts that should not be public go in `docs/plans/` (also gitignored). The team’s live plans stay in `plans/`.

## What not to do

- Do not post to X from this repo’s automation or drafts that claim to publish.
- Do not weaken a test to make preflight green.
- Do not commit `.env`, tokens, private keys, or personal data.
- Do not treat a general chat instruction as permission to add `ceo-approved`.
