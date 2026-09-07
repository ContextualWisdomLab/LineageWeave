# ADR 0370 — Global Ask claim-generation liveness

**Decision status:** Proposed
**Date:** 2026-09-08

Amends the Global Ask worker settlement path. Independent of leftover-map
ADRs 0272+ on other stacks and of the versioned translation ledger
([ADR 0362](0362-versioned-ui-translation-ledger.md)).

## Context

Issue #975: a live Ask job could be terminated or reclaimed from elapsed
wall time (600 s compute deadline, 570 s invented socket hang-up) while
a provider `TimeoutError` and a worker deadline meant different things.
Orphan recovery flipped `running` → `queued` by `updated_at` age, and
the original worker could still settle by job id alone.

## Decision

- Claim `queued` → `running` returns a generation (`updated_at`).
- Settlement is compare-and-set on that generation; PostgreSQL
  `UPDATE 0` is an unapplied settle, not a buyer-visible failure.
- While computing, the owner renews `updated_at` on the recovery
  interval. A failed renew aborts without settling as failed.
- Cancelling the owner task cancels the inner compute task.
- LineageWeave does not invent an Ask socket hang-up when
  `ORCHESTRATOR_ANSWER_TIMEOUT_SECONDS` is omitted. An explicit finite
  value must stay below 600 s.
- Live compute is not cancelled when 600 s elapse. Age-based orphan
  recovery uses three missed heartbeats, not the old 660 s reaper.
- Provider `TimeoutError` stays an unavailable Ask failure.

## Consequences

Positive: a renewing owner can outlive the former hard deadline; a
reclaimed job cannot be overwritten by the previous owner.

Negative: crashed workers wait three heartbeat intervals to reclaim.
PostgreSQL-backed claim/settlement evidence for the race remains a
follow-up; current REDs use deterministic fake pools plus exact SQL
contracts.

## Alternatives considered

Keep the 600 s `asyncio.timeout` around compute: rejected because it
cancels a live heartbeat owner. The elapsed-deadline RED proves that
path.
