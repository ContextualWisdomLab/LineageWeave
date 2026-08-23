# ADR 0098: Use a durable PostgreSQL ledger with Valkey wake-ups for post-content ingestion

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
   process restart. The first attempt is immediate; retries become eligible
   five minutes after `queued_at`, and `queued_at` is refreshed when a retry
   is scheduled so older due jobs remain ahead of newer work. The worker
   permits three attempts, then records terminal
   `post_content_ingestion_attempt_limit`; duplicate wake-ups cannot reopen a
   terminal failure. A changed source digest starts a new budget.
4. The worker reuses the existing contextual-orchestrator client factories for
   VISION, structure, and embeddings. It preserves one post session and the
   bounded provenance metadata from `llm_context`; no raw provider call, model
   selector, monkey patch, or MLX-specific contract is introduced.
5. The buyer content endpoint returns `processing` while the durable job is
   queued/running and `ready` only after persisted units exist and, when an
   embedding model is configured, every unit and every described visual region
   has the corresponding persisted vector. A previous `succeeded` row with
   incomplete derived evidence is requeued through Valkey instead of being
   treated as complete. The worker verifies that persisted units contain no
   unresolved structure decisions when structure adjudication is configured.
   Incomplete provider output is retried with an explicit failure code rather
   than being reported as succeeded. The frontend polls that status while
   continuing to show the source post. Persisted units, images, and regions are
   exposed only when the job is `succeeded` for the exact current raw-body
   SHA-256. Otherwise those derived arrays are withheld and the independently
   loaded current raw source body remains the rendering fallback.

## Consequences

- Slow VISION and region embedding work never blocks source-post open or source
  rendering. Region embeddings do not block summary. For an image-bearing
  post, persisted parent-image and region descriptions are source evidence and
  therefore block only the current summary projection until they are complete.
- A provider failure is recorded and can be retried without deleting the raw
  source body or fabricating buyer content.
- Valkey is load-bearing as a wake-up queue, but PostgreSQL remains the durable
  recovery boundary.
- Summary generation remains a separate contextual-orchestrator operation;
  this ADR does not hide a slow summary provider behind an in-memory task.

## Completeness invariant (2026-08-20)

The worker claim path MUST use the same `post_content_is_complete` predicate as
the API enqueue path. A successful job that has units but lacks the configured
unit or described-region embeddings is still eligible for Valkey requeue and
MUST NOT be silently skipped by checking only for unit presence.

The same predicate MUST reject an image unit when its persisted parent image
is missing or its VISION status is not `described`, and MUST reject it when
any persisted visual region is not `described`. The operator selector uses
the same image/region condition, so an unavailable image cannot become a
permanent false-ready result merely because its text-unit embeddings exist.
The existing bounded automatic retry limit and the explicit terminal retry
operation in ADR 0115 remain unchanged.

The narrower `post_content_summary_is_ready` predicate checks only the
persisted VISION evidence required by an image-bearing summary; embeddings and
non-image structure decisions remain outside that predicate. Readiness also
requires the durable job row to match the current raw-body SHA-256 and have
status `post_content_ingestion_succeeded`; described units from an earlier
body cannot make a newly queued, running, or failed revision ready. The
summary read path may enqueue or observe the durable job. It MUST NOT call VISION directly
or summarize an unavailable image placeholder. Queued and running jobs remain
processing. A terminal failed job remains unavailable until ADR 0115's explicit
operator retry.

When contextual-orchestrator is configured, the same predicate also requires
every persisted unit to have a non-`unresolved` structure decision. Without an
available structure channel, `unresolved` remains an explicit unavailable
signal rather than a fabricated hierarchy; enabling the channel makes those
posts eligible for Valkey requeue.

The worker treats a `running` lease older than 15 minutes as stale. Recovery
does not reset the row or create a second body record; it republishes the
existing `(post_id, source_body_sha256)` wake-up to Valkey, and `_claim_job`
reclaims it under the same lease predicate. This keeps a process restart or
lost consumer from leaving a job permanently running while retaining
at-least-once persistence semantics.
Duplicate wake-ups for a fresh `running` lease are ignored before applying the
attempt-limit rule. A final permitted attempt becomes terminal only when that
lease is stale; a duplicate wake-up cannot fail work that is still active.

On worker startup, the stream cursor begins at the current Valkey stream tail,
not at `0-0`. Historical wake-ups are not authoritative work state; the
normalized PostgreSQL ledger is scanned and queued/stale rows are republished
after the cursor is established. This prevents a restart from replaying an
unbounded historical stream before processing current work.

Lease recovery fences persistence and completion with the claimed source-body
SHA-256 plus `attempt_count` as a monotonic claim identity. `attempt_count` is
incremented on every claim and is never reset by a changed digest or explicit
retry, so an A-to-B-to-A body sequence cannot recreate an old claim identity.
The bounded automatic-retry count is derived from the existing status-event
ledger after the latest non-failure queued boundary. Before replacing artifacts
or completing/failing work, the worker locks the job and source row and
requires the job to remain `running` for that exact attempt and digest and the
source body to still hash to that digest. A stale worker therefore cannot
overwrite newer artifacts, complete a requeued attempt, or append a false
status event.

A missing ledger row is always inserted as `queued`, even if pre-ledger
artifacts happen to satisfy the structural completeness predicate. Those
artifacts have no binding to the current raw-body digest; only a fenced worker
or the explicit ADR 0115 backfill finalization may register success.

The synchronous operator backfill performs provider work before its short
database transaction. Inside that transaction it locks and rechecks the
current source body and non-active ledger row, records the bound ledger
success, and replaces all derived artifacts atomically. It cannot overwrite an
active worker's artifacts or commit success for a body that changed during
provider work. The synchronous source-import adapter uses the same finalization
fence so every production artifact writer participates in that serialization.

## Corpus backfill (2026-08-20)

Operational backfill MUST use `scripts/queue_post_content_backfill.py`. It
selects only non-draft, non-deleted rows with real source context, records the
same completeness-aware job state in PostgreSQL, and publishes wake-ups through
Valkey. Direct provider calls are not a substitute for the worker queue.

### Operational timeout for structure adjudication

The contextual-orchestrator structure adjudication request uses a 600-second client timeout by default. Structure inference is an accuracy-critical, structured multi-agent operation rather than a user-facing synchronous request; the longer bound prevents a slow but valid workflow from being downgraded to `unresolved` merely because the client abandoned the response. The durable job remains queued until all non-image units have complete structure evidence.
