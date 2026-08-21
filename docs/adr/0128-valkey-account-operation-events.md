# ADR 0128: Register account operation events in Valkey

- Status: Accepted
- Date: 2026-08-20
- Related: [0023](0023-analysis-run-outbox.md), [0098](0098-valkey-backed-post-content-ingestion.md)

## Context

Valkey already carries post activity and durable worker wake-ups, but several
successful account-scoped mutations had no operation event. That makes the
operation stream incomplete even though PostgreSQL remains the source of
truth.

## Decision

1. Successful account-scoped mutations without one owning post publish a
   bounded event to `operation:{account_id}` through
   `publish_operation_event`.
2. Post-scoped bookmark changes publish through the existing post activity
   stream. Existing ticket, chat, extraction, evaluation, and verification
   events keep their current event types.
3. Events contain only an operation type, actor account id, and short generic
   summary. They do not carry source bodies, model output, credentials, or
   unbounded identifiers.
4. PostgreSQL remains the durable source of truth; a Valkey write is a
   notification and does not replace the database mutation or its recovery
   path.

## Consequences

Operation consumers can account for preference, catalog, lineage, report,
bookmark, and analysis-run actions consistently. Valkey failure has the same
runtime behavior as the existing activity stream: the durable database write
must be recovered or retried by the caller rather than silently presented as
an observed event.
