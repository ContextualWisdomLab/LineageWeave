# ADR 0023 — Valkey outbox for TEPP envelopes

**Decision status:** Accepted
**Date:** 2026-08-17

## Context

A fail-closed TEPP submit (ADR 0022) is lost if it only lives in the
HTTP response. Period-report IRT rows are the wrong table: they store
LineageWeave's own GRM/GPCM θ, not a TEPP run. An analysis-run
registry (Milestone 2.1 on the stacked branch) is a different
authority and must not be reimplemented here.

Valkey is already the product event queue (`activity:{post_id}`).

## Decision

1. Each TEPP submit `XADD`s onto `outbox:tepp` with outcome, next
   action, and the published request identity (idempotency key,
   snapshot, cutoff). No theta field.
2. `GET /api/tepp/outbox` returns the newest events for `post_read`.
3. `make seed` writes one crate-only fail-closed row so the home
   panel names the next action after a fresh stack.

## Consequences

- The buyer sees the last TEPP attempt above the period-report
  actions without opening a second product.
- A later analysis-run registry can drain this outbox; it must not
  invent a score while doing so.
