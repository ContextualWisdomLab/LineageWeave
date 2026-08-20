# ADR 0086: Load Backfill Post Bodies Per Row

- Status: Accepted
- Date: 2026-08-20

## Context

Post bodies can contain large embedded-image payloads. Selecting every eligible
post with `post_body` in one `asyncpg.fetch()` makes the resumable `--all`
backfill depend on the aggregate size of the remaining corpus and can terminate
the worker for excessive memory use.

## Decision

The backfill first selects only eligible `post_id` values with its existing
limit and ordering. It then fetches the complete source row for one post at a
time immediately before normalization and persistence. The `--all` option keeps
its existing resumable semantics; it must not materialize the remaining post
bodies in memory.

## Consequences

- Large image-bearing bodies remain available for processing without an
  aggregate body-memory spike.
- The source body remains unchanged and is still normalized through the
  contextual-orchestrator boundary.
- Backfill performs one additional source-row query per selected post, which is
  an intentional tradeoff for bounded memory.
