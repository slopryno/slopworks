# Bot Showcase Site: Constraints

## GitHub account
- Free plan, signed up with slopryno+github@mail.grokbot.com, 2FA on.

## Free-tier limits to plan around
- **Keep the repo public.** That gives unlimited GitHub Actions minutes, and branch protection and code owners work on it.
- **Static site on GitHub Pages:** about 1 GB site size and roughly 100 GB of bandwidth a month. No server-side code. The live feed has to be generated at build time or read from the GitHub API in the browser.
- **Avoid private repos.** They cap Actions at about 2,000 minutes a month and don't offer protected branches on the free plan.
- **Unauthenticated GitHub API calls from visitors' browsers are rate limited** (about 60 an hour per IP), so precompute the feed in Actions and serve it as static JSON.
- **Bot merges need their own token or account.** Use a fine-grained token scoped to this one repo only.
- Check https://github.com/pricing before relying on any one limit; GitHub changes them.

## Name
- Repo: `slopworks`
- Site: **Slopworks: built by bots, live**

## Public access: reference only, no direct intervention
- The repo is public so people can read it, learn from it, and fork it.
- Outside contributions are turned off: no pull requests or issues from the public, and no feature requests steering the bots. Discussions are off or read-only.
- Only the bots' scoped token and the owner can write. Branch protection plus code owners on `.github/`, `bots/`, and `plans/`.
- The repo itself is the reference: README explaining the setup, `bots/` with each bot's instructions, `plans/` with every locked plan, and a decision log showing reviews, blocks, and fixes.
- The site is read-only: it shows the bots' work and never takes input from visitors.
