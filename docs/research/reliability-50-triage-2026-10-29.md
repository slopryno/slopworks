# Reliability 50 triage (2026-10-29)

Source: [SCR01111, "Are vibe coders even aware of these 50 things?"](https://x.com/SCR01111/status/2115699154337026229) (full list via `note_tweet`). Ryno, 10:37 PM ET Oct 29: "Have the review and be trained on anything here that makes sense for them."

Slopworks is a static GitHub Pages site with no backend, visitor input, analytics, database or message bus. Bot personas run as box routines using Python (`scripts/bot.py`, `check.py`) and `gh`. Most of the 50 do not apply. Training is the short **Reliability checklist** blocks in the role files below — no new role, no skills track.

## Applies (trained into role files)

| Item | Why it hits us | Owner |
| --- | --- | --- |
| Race conditions | Shared `bot-pr.lock` and box `run.lock`; reclaim races | Forge, Trial, Sweep |
| Pessimistic locking | `run.lock` / `bot-pr.lock` are exclusive claims | Forge, Sweep |
| Optimistic locking (reclaim) | Re-read holder before renaming a "stale" lock (S1) | Forge, Trial |
| API rate limiting | GitHub `gh` API; X read budget on Scout/Sketch | Sweep, Sketch, Forge |
| Exponential backoff + Jitter + Retry mechanisms | 429/5xx only; fixed sleeps are not enough | Forge, Sweep |
| Idempotency | `bot.py resume`, chat ids, deduped drafts | Forge, Trial, Sketch |
| Health checks | Trial post-deploy live check; Sweep uptime/feeds | Trial, Sweep |
| Graceful shutdown | Always release the run lock you hold | Sweep |
| Circuit breakers (+ recovery) | Skip + log a blocked/5xx external host; don't loop | Sweep, Sketch |
| Backpressure | Tempo 6/sprint and 18/day; page/repo budgets | Coordinator, Sweep |
| Cache invalidation / eventual consistency | Pages CDN lag after deploy | Sweep |
| Zero-downtime migrations (analogue) | Add-only JSON/schema changes | Atlas |
| Unique constraints (analogue) | Unique chat/AAR/idea/update ids under concurrency | Atlas |
| Webhook verification | N/A today; rule parked on Shield if one is ever added | Shield |
| Job scheduling | Existing routines/calendar — already owned; no new checklist line | (Coordinator / Sweep) |

## Does not apply (static site, no DB, no queue)

Database Indexes, Database Transactions, Connection Pooling, ACID Properties, Database Sharding, Isolation Levels, N+1 Queries, Query Optimization, EXPLAIN ANALYZE, Foreign Key Constraints, Read Replicas, Replication Lag, Database Partitioning, Database Migrations (SQL), Redis Eviction Policies, Distributed Caching, Distributed Tracing, Distributed Transactions, Message Queues, Dead Letter Queues, Outbox Pattern, Event-Driven Architecture, CQRS, Event Sourcing, Load Balancing, Horizontal vs Vertical Scaling, Reverse Proxies, Webhook Retries, Cache Stampedes (no thundering-herd cache layer we own), Background Workers as a product concern (routines already covered by scheduling).

## Real gaps found (code), queued as backlog

1. **Box-only `runlock.py` reclaim race** — `/workspace/tmp/n1/runlock.py` lines 17–20 rename a "stale" lock from mtime alone and unlink the aside with no re-check that a live run claimed it. Same bug class as #168 (fixed in `scripts/bot.py`). Box-only today; port the S1 pattern, then consider wiring it into the routines.
2. **`gh` calls without 429 backoff** — `scripts/bot.py` wraps `gh` with plain `subprocess.run` (around the `gh()` helper) and uses fixed `time.sleep(15)` / `time.sleep(6)`. No exponential backoff or jitter on 429/5xx.

## Full list of 50 (for the record)

Database Indexes; Race Conditions; API Rate Limiting; Database Transactions; Cache Stampedes; Connection Pooling; Dead Letter Queues; ACID Properties; Webhook Verification; Distributed Tracing; N+1 Queries; Circuit Breakers; Database Sharding; Optimistic Locking; Exponential Backoff; Zero-Downtime Migrations; Message Queues; Isolation Levels; Idempotency; Load Balancing; Query Optimization; Graceful Shutdown; Redis Eviction Policies; Foreign Key Constraints; Replication Lag; Background Workers; Deadlocks; Eventual Consistency; Read Replicas; Retry Mechanisms; Database Migrations; Backpressure; Pessimistic Locking; Horizontal vs Vertical Scaling; Webhook Retries; EXPLAIN ANALYZE; Distributed Caching; Unique Constraints; Outbox Pattern; Health Checks; Database Partitioning; Job Scheduling; Reverse Proxies; Distributed Transactions; Cache Invalidation; Event-Driven Architecture; Jitter; CQRS; Event Sourcing; Circuit Breaker Recovery Strategies.
