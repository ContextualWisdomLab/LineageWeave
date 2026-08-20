# ADR 0092: Use a durable PostgreSQL ledger with Valkey wake-ups for post-content ingestion

- Status: Accepted
- Date: 2026-08-20
- Related: [0062](0062-semantic-unit-embedding.md), [0066](0066-position-preserving-image-content.md), [0091](0091-visual-region-embedding-persistence.md)

## Context

VISION, DOM-region analysis, structure adjudication, OCR, and semantic
embeddings can take longer than a buyer popup request. An in-process
`asyncio.Task` is not durable: a restart loses its state, a second process can
duplicate work, and a failed provider call has no buyer-visible lifecycle.

The existing analysis-run design already uses PostgreSQL as the source of
truth and Valkey as a wake-up transport. Post content needs the same boundary.
The raw body and derived evidence are private database data; they must not be
placed in a stream message.

## Decision

1. `post_content_ingestion_job` is the normalized durable ledger keyed by
   `post_id` and the SHA-256 digest of the current source body. Its status and
   append-only status events are the source of truth for queued, running,
   succeeded, and failed work.
2. Valkey stream `post-content-ingestion` carries only `post_id` and the source
   body digest as a wake-up. The worker is at-least-once and idempotent; it
   claims the PostgreSQL row and rechecks the digest before provider work.
3. A queued-row recovery sweep republishes wake-ups after Valkey loss or
   process restart. A stale running claim is retryable after fifteen minutes.
4. The worker reuses the existing contextual-orchestrator client factories for
   VISION, structure, and embeddings. It preserves one post session and the
   bounded provenance metadata from `llm_context`; no raw provider call, model
   selector, monkey patch, or MLX-specific contract is introduced.
5. The buyer content endpoint returns `processing` while the durable job is
   queued/running and `ready` only after persisted units exist. The frontend
   polls that status while continuing to show the source post.

## Consequences

- Slow VISION and region embedding work no longer blocks summary or post-open.
- A provider failure is recorded and can be retried without deleting the raw
  source body or fabricating buyer content.
- Valkey is load-bearing as a wake-up queue, but PostgreSQL remains the durable
  recovery boundary.
- Summary generation remains a separate contextual-orchestrator operation;
  this ADR does not hide a slow summary provider behind an in-memory task.
