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
   Recovery walks the ready ledger with the deterministic
   `(queued_at, post_id)` keyset and wraps only after reaching the end. It must
   not repeatedly publish only the first bounded page while later rows starve.
   The worker trims the Valkey stream through its consumed cursor; producers
   never trim unread wake-ups by an approximate length limit.
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
   continuing to show the source post.

## Consequences

- Slow VISION and region embedding work no longer blocks summary or post-open.
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

On worker startup, the stream cursor begins at the current Valkey stream tail,
not at `0-0`. Historical wake-ups are not authoritative work state; the
normalized PostgreSQL ledger is scanned and queued/stale rows are republished
after the cursor is established. This prevents a restart from replaying an
unbounded historical stream before processing current work.

Within one worker lifetime, the recovery keyset cursor advances across every
ready queued or stale-running lease and wraps at the end. This is publication
reachability, not a change to retry order, attempt budgets, or provider
admission. Wake-up retention is consumption-bound: a successful batch advances
the consumer cursor and then removes entries through that cursor. A producer
cannot erase an unread later-page wake-up merely because the stream exceeded a
fixed approximate length.

Lease recovery also fences completion by `attempt_count`. A worker whose
15-minute lease was reclaimed may finish after the replacement worker has
started; its success, retry, or terminal failure transition is accepted only
when the PostgreSQL row is still `running` for that exact attempt. A stale
worker therefore cannot overwrite the newer attempt or append a false status
event.

## Corpus backfill (2026-08-20)

Operational backfill MUST use `scripts/queue_post_content_backfill.py` or
`POST /api/post-content/backfill`; both call the same producer. The HTTP
entry point requires `post_admin`, accepts only a 1--200 row page, and returns
HTTP 202 after committing the ledger and attempting wake-ups; it never runs a
provider in the request. Each worker recovery cycle also persists one bounded
page before republishing queued wake-ups. Active and terminal jobs remain
excluded, so successive cycles make durable corpus progress without duplicate
work or an unbounded HTTP request. Candidate selection and broker recovery are
independent: either failure is recorded and retried on the next cycle without
stopping the worker.

The bounded candidate scan uses the partial
`source_post_content_backfill_candidate_idx` on the candidate query's event-time
fallback and deterministic tie-breakers. Its partial predicate excludes drafts
and deleted rows; the query retains the shared source-context predicate. This
lets PostgreSQL stop after the requested ordered page instead of evaluating
content completeness across the whole source corpus. It does not change
eligibility or completeness semantics.

The CLI retains the same per-query bound. `--all-pages` repeats that governed
producer until the current candidate set is empty; progress remains visible in
the normalized job ledger after every page. Terminal failures are never reset
implicitly. An operator may combine `--retry-failed --all-pages` only after the
failed dependency has been restored; each failed page uses the existing
explicit retry transition and commits before its wake-ups.
The producer applies `SOURCE_POST_ELIGIBILITY_SQL`, locks source rows with
`SKIP LOCKED`, selects only new or incomplete-succeeded jobs, rechecks the
shared completeness predicate, and records the existing job state in
PostgreSQL. Repeated calls therefore do not reset active or terminal work.
When contextual-orchestrator evidence is required, an otherwise complete
successful job with no `operations_case_analysis` row is also incomplete and
eligible for the same bounded requeue. This lets records completed before the
operations extractor was deployed enter that extractor without a synchronous
provider call or a second queue.
If Valkey is unavailable, the response reports `recovery_pending` and the
committed queued rows are republished by the existing recovery sweep. Direct
provider calls are not a substitute for the worker queue.

## Provider admission deferral (2026-08-26)

Contextual-orchestrator may return its typed `no_viable_agent` response before
any provider inference is admitted. It supplies the same positive delay in the
standard `Retry-After` header and its bounded error contract. This outcome is
queue admission evidence, not a provider attempt or a negative analysis.

The owning worker therefore uses a fenced PostgreSQL transition from the exact
running lease back to queued, reverses only that lease's claim increment, and
stores `next_attempt_at` from the orchestrator's exact delay. The post identity,
body digest, post-scoped session, and existing evidence remain unchanged. A
stale worker cannot defer a newer lease. Recovery publishes the row only after
`next_attempt_at`; other transport, provider, validation, and persistence
failures retain the existing three-attempt accounting. Raw upstream error text,
agent identity, prompt, and response are neither stored nor shown to a reader.

Operations-case analysis is the Dashboard acceptance channel and runs before
optional product extraction inside a claimed job. Each channel commits through
its own existing persistence transaction while retaining the same post-scoped
session and exact body digest. A later product extraction failure therefore
cannot erase an already committed operations case, and product latency cannot
delay admission of the case request. This is execution isolation, not a new
queue or a change to either channel's evidence contract.

Every failed attempt persists bounded diagnostic provenance on the normalized
job ledger: the channel stage, bounded exception class, HTTP status, orchestrator error code, explicit
retryability when supplied by the upstream contract, and the existing
post-scoped session correlation id. These fields support aggregate operations
and exact-session tracing without retaining a response body, error message,
prompt, provider identity, credential, or source text. The buyer-facing status
continues to state the next action; these implementation diagnostics remain an
authorized operational boundary.
Operations-case validation failures additionally retain only the closed
`operations_case_evidence_contract` code and `$.cases` JSON path; returned
content is never copied into the ledger.

### Operational timeout for structure adjudication

The contextual-orchestrator structure adjudication request uses a 600-second client timeout by default. Structure inference is an accuracy-critical, structured multi-agent operation rather than a user-facing synchronous request; the longer bound prevents a slow but valid workflow from being downgraded to `unresolved` merely because the client abandoned the response. The durable job remains queued until all non-image units have complete structure evidence.
