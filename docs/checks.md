# Checks list (Critic)

One line per hand-caught mistake. Critic owns this file ([`bots/critic.md`](../bots/critic.md)). Default no. After a line fails twice, Advisor and Forge turn it into a script or CI check. Do not put secrets, personal email, or amplifier handles here.

- Recount totals and counts from the source records (`data/*.json`, the tracker file), never from memory.
- No amplifier handles in public text.
- No `Co-authored-by` trailers.
- No personal email in the repo or a public page.
- A claimed file edit is checked by reading the file.
