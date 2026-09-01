# ADR 0279: Select durable worker ownership by consumer

- Status: Accepted
- Date: 2026-09-01
- Related: [0098](0098-valkey-backed-post-content-ingestion.md),
  [0204](0204-analysis-run-short-transaction-delivery.md),
  [0218](0218-current-contract-mcp-global-ask.md), and
  [0224](0224-canonical-compose-project.md)

This decision supersedes only ADR 0224's single-process ownership of all
durable consumers; its canonical-project and API/worker separation decisions
remain in force.

## Context

The canonical worker owns every durable consumer under one process-wide
PostgreSQL advisory lease. That is safe against duplicate stream cursors, but
it couples unrelated availability. An operator who intentionally stops the
long-running post-content backfill also stops Global Ask, leaving accepted Ask
jobs queued even though Ask does not depend on post-content consumption.

Starting a second copy of the broad worker is unsafe: it duplicates every
consumer and conflicts with ADR 0098's single cursor owner. Moving Ask into the
HTTP process would reverse ADR 0218 and ADR 0224's durable asynchronous
boundary. A guessed lease duration or polling ratio is unnecessary because
PostgreSQL session advisory locks already provide crash cleanup.

## Decision

1. The worker accepts an explicit comma-separated
   `LINEAGEWEAVE_WORKER_CONSUMERS` set from the closed vocabulary
   `analysis_run`, `post_content`, `global_ask`, `voice_taxonomy`, and
   `topic_influence`. Missing or blank configuration preserves the historical
   behavior and starts every configured consumer. An unknown name fails
   startup; it is never ignored. If an explicit selection contains only an
   optional consumer whose transport is unavailable or invalid, startup fails
   before the heartbeat begins instead of reporting a healthy no-op worker.
2. Each active consumer has a distinct PostgreSQL session advisory-lock name.
   One worker process acquires all of its selected locks on one held session
   before starting any consumer. Failure to acquire any lock releases the
   already-acquired locks and fails the process before queue reads. PostgreSQL
   session cleanup remains the crash-release mechanism; no timeout or
   heartbeat lease is introduced.
3. The canonical Compose project runs two non-overlapping worker services.
   `backend-worker` owns analysis-run, post-content, Voice transition, and the
   configured topic-influence consumer. `backend-ask-worker` owns only Global
   Ask. Both use the same worker image, progress health contract, PostgreSQL,
   Valkey, and contextual-orchestrator boundary. The backend depends on and
   health-gates only `backend-ask-worker`; a targeted `docker compose up
   backend` therefore never starts post-content. A full `docker compose up`
   still starts the independent broad worker as a top-level canonical service.
4. Stopping `backend-worker` therefore cannot start, retry, recover, or consume
   post-content work through the Ask service. Global Ask remains durable and
   asynchronous through its own existing ledger and wake-up consumer.
5. Exact-revision runtime acceptance verifies both worker images. This
   decision does not authorize starting either worker against an existing
   queue, changing retry timing, increasing concurrency, or requeuing failed
   work.
6. The legacy process-wide lease and the new per-consumer leases are different
   lock identities. Deployment must therefore stop the legacy worker before
   starting either selected worker; a rolling overlap is prohibited. The
   canonical Compose upgrade procedure performs that stop first and verifies
   the old container is absent before either replacement starts.

## Considered alternatives

- Keep one broad worker: rejected because unrelated post-content operations
  continue to suspend Global Ask.
- Start a second broad worker: rejected because duplicate stream owners race
  cursor advancement and violate ADR 0098.
- Run Ask in the API process: rejected because API restarts would again own
  durable work and blur the ADR 0218 asynchronous boundary.

## Consequences

- Ask can progress while post-content consumption is intentionally stopped.
- Consumer overlap fails closed even when deployment configuration is wrong.
- The canonical project has one additional worker container and health gate.
- Each worker process holds one pooled PostgreSQL connection for its selected
  advisory locks for its lifetime, matching the previous single-worker lease
  cost per process.

## References

PostgreSQL Global Development Group. (2026). *PostgreSQL 18.6 documentation:
9.28 system administration functions*.
https://www.postgresql.org/docs/18/functions-admin.html
