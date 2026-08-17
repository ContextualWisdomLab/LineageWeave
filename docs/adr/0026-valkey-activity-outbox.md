# ADR 0026 — Fail-closed Valkey transactional activity outbox

**Decision status:** Accepted
**Date:** 2026-08-17

## Context

Ticket create/status-change already `XADD`s onto `activity:{post_id}`
(Phase 5b). That is a dual-write: Postgres commits the ticket, then
Valkey receives the event. If the stream write fails after the
ticket row exists, Activity is empty and there is no durable retry
evidence (Hohpe & Woolf, 2003, Transactional Outbox; Kleppmann,
2017). Milestone 2 (#79 / #87) requires outbox delivery and
idempotency evidence without a second application.

TEPP's own outbox lives on #214 (ADR 0023). This ADR is the
activity-queue outbox on protected `main`. It does not invent a
fused score or a theta.

## Decision

1. Persist `activity_outbox_event` (3NF, two-or-more-word
   `snake_case`) as `outbox_pending` before any `XADD`.
2. After a successful stream write, store the Valkey entry id and
   flip the row to `outbox_delivered`. A missing stream id is not a
   delivery.
3. `GET /api/outbox` (`post_read`) fail-closes when
   `VALKEY_DISABLED=1` or Valkey does not answer. Unavailable copy
   is **Outbox · Valkey not available**. Accepted rows list the
   event summary; click opens that `source_post`. Hidden posts are
   omitted.
4. Idempotency is `(post_id, event_type_code, event_summary)`.
   Re-seed does not invent a second delivery.

## Consequences

`make seed` writes the pending row, `XADD`s, then marks delivered
so home Outbox is not empty after a fresh stack. Activity still
reads the stream. RankWeave stays on ADR 0024. Leftover pairs stay
on ADR 0017 / 0018. TEPP stays on #214.

## References

Hohpe, G., & Woolf, B. (2003). *Enterprise integration patterns:
Designing, building, and deploying messaging solutions*.
Addison-Wesley.

Kleppmann, M. (2017). *Designing data-intensive applications*.
O'Reilly Media.
