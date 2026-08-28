# ADR 0115: Explicit terminal post-content retry

- Status: Accepted
- Date: 2026-08-20
- Figma: N/A; this is an operator-only control and adds no buyer-facing UI.

## Context

ADR 0098 limits automatic post-content retries and makes a terminal failure
durable. A worker/runtime repair can leave a historical job terminal even
after the underlying cause is fixed. Requeueing such a row from a normal read
would silently weaken the retry limit and could create an endless loop.

## Decision

Keep automatic retry and read-time behavior unchanged. Provide an explicit,
single-post operator command that may requeue only a `failed` job, resets its
attempt counter, recomputes the current source-body digest, appends an audit
status event, and publishes one Valkey wake-up. The command is not exposed as
a public HTTP route and does not reset a queued, running, or succeeded job.

The command must use the existing queue function and must not call a provider
directly. It is an operational recovery action, not a buyer-visible status
override; the worker still performs the normal VISION, structure, and
embedding completeness checks.

The synchronous operator backfill is a separate repair path. After it
persists derived evidence, it must call the queue module's ledger-finalization
function in a database transaction. It must never leave a previously failed
job marked failed while presenting newly persisted content as a successful
backfill.

## Consequences

- Historical terminal jobs can be recovered after a verified root-cause fix.
- Ordinary reads remain bounded and cannot silently retry failed jobs.
- The audit event distinguishes an explicit operator retry from automatic
  recovery.

## References

- [ADR 0098: Durable post-content ingestion](0098-valkey-backed-post-content-ingestion.md)
