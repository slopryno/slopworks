# Slopworks: built by bots, live

Slopworks is a public website planned, built, tested, and reviewed by a small team of AI bots. The site is the product, and it's also a window into how it gets made. This repo is the full record: bot instructions, locked plans, reviews, and code.

**Live site:** https://slopryno.github.io/slopworks/

## Read-only public reference
- Read, learn from, and fork freely.
- Outside pull requests are not merged. Issues, discussions, and the wiki are off.
- Only the owner and the bots' repo-scoped token can change this repo. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## The team
| Bot | Role |
| --- | --- |
| [Sketch](bots/sketch.md) | Planner |
| [Lens](bots/lens.md) | Reviewer (plans and code) |
| [Trial](bots/trial.md) | Quality: acceptance tests first |
| [Forge](bots/forge.md) | Builder |
| [Shield](bots/shield.md) | Security and privacy auditor |

## How work flows
1. **Sketch** writes a plan from the [template](plans/TEMPLATE.md).
2. **Lens** reviews the plan (max 2 rounds).
3. **Owner approves**; the plan is committed to [`plans/`](plans/), which locks it.
4. **Trial** writes acceptance tests that fail first.
5. **Forge** builds on its own branch until the tests pass.
6. **CI** runs checks (size, secret scan, guarded paths).
7. **Lens** (code review) and **Shield** (security audit) review in parallel.
8. **Merge** into `main`, which deploys to GitHub Pages.

## Layout
```
bots/      one instruction file per bot
plans/     locked plans + TEMPLATE.md
docs/      vision.md (plan) and constraints.md
site/      the static website (deployed by GitHub Pages)
.github/   CI, Pages deploy, CODEOWNERS, Dependabot
```

## More
- [Vision and proof of concept](docs/vision.md)
- [Constraints](docs/constraints.md)
- [Plans](plans/)

License: [MIT](LICENSE)
