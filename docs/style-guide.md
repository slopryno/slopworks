# Slopworks style guide

Owned by Comms (Head of Comms, i28). Comms has the final say on wording after consulting the roles a change touches (i29). Facts stay with Lens, personal data with Shield, and the guardrails with CI. Proposal and comments: Team chat c111–c117.

Voice, tone and word limits: [docs/voice.md](voice.md) (Comms, 2026-10-19), enforced by `data/word_limits.json`, `data/voice.json` and `scripts/check.py`.

## Voice
- **Honest.** Say only what a public source or a merged change shows. If it's a guess, label it Hypothesis. If it's a demo, label it Demo.
- **Plain.** Short sentences and everyday words. Lead with what the reader can do or learn.
- **No hype.** No superlatives, no "revolutionary", no "best". Let the linked record do the talking.
- **Calm about mistakes.** Mistakes are shown, not hidden, and AARs are blameless: name the cause and the gap, not a culprit.

## Credit and self-description
- Footer credit (unchanged): "Built and designed by Grok Bots. Reviewed and merged by bots; steered by a human CEO (Ryno)."
- Short form: "built and run by Grok Bots".
- Disclaimer (unchanged, on every page): "Unofficial, fan-built project. Not affiliated with or endorsed by Grok Bot, SpaceX, or X."
- Frame the site as a showcase of the team's work. Keep any commercial note soft, in line with GitHub's Pages terms.
- Any change to how Slopworks describes itself, or to what it claims for clients, goes to Ryno as `needs-ceo` (i29).

## Terms
- **Roles, not bots-as-people.** "Roles played by one daily routine." Never imply separate live agents or that anything is "live" or "real-time".
- **Role names:** use the names on the Team page: Coordinator, Scoutmaster, Comms, Sketch (plays Scout), User Advocate (`Advocate` in data), Research Librarian (`Librarian`), Atlas, Forge (with Pixel and Core), Polish, Lens (plays Verify), Trial, Shield (plays Privacy), Critic, Advisor, Sweep, Analyst, Game Master (`Gamemaster` in data), Director of Strategy (`Strategy` in data). In the daily-run context, Scout, Verify, Privacy, and Publish are fine.
- **Grok Bot**, always two words and capitalized. A user's bot is "a Bot" when quoting the official changelog, and "a Grok Bot" otherwise.
- **Statuses:** confirmed (official account or docs), reported (community post). Labels: Verified, Hypothesis, Recommendation, Demo, as of.
- **Times:** Eastern Time with "ET", from the clock when written.

## Numbers and claims
- Every number is counted from the repo at build time or links to its record.
- Never claim rankings, traffic, visitors, conversions, or speedups we don't measure.

## Metadata (SEO and AEO)
- Each page has a unique title ("Page · Slopworks") and one plain description of 160 characters or less that matches the page.
- Canonical URLs, Open Graph, and Twitter text reuse the title and description. There's no social image until d2 is unblocked.
- Structured data uses schema.org microdata (WebSite and Organization on Home; CollectionPage or WebPage elsewhere). JSON-LD would need a `<script>` tag, which CI bans, and that check stays.
- `sitemap.xml`, `robots.txt`, and `llms.txt` are generated from the same page list in `scripts/build.py`.

## Banned hype (CI fails only on these clear cases)
revolutionary, game-changing, game changer, world-class, best-in-class, industry-leading, cutting-edge, state-of-the-art, unparalleled, unmatched, guaranteed, 10x, "#1", "number one", blazing fast, next-gen, groundbreaking.
Official changelog wording is quoted as written, and the check skips quoted text.
