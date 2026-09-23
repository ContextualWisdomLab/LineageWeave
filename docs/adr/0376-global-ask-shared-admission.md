# ADR 0376: Global Ask admission is shared and capacity-bound

## Status

Proposed (2026-09-23).

## Context

`POST /api/ask` and authenticated MCP submit the same durable Global Ask work,
but only MCP consumed the shared Valkey quota. REST could therefore enqueue
unbounded provider-backed work. A separate process-local limiter would diverge
across replicas, and a count followed by an insert would overshoot under
parallel requests.

The repository has no authoritative universal request size, rate, window, or
active-job capacity. Those values depend on an authenticated k6 workload and a
named deployment's PostgreSQL, worker, Valkey, and gateway saturation evidence.

## Decision

1. The shared application service enforces a UTF-8 question-byte ceiling, an
   atomic Valkey per-principal submission window, and a per-principal active
   durable-job ceiling before accepting work.
2. Operators supply all four positive capacity values. Missing values make
   submission unavailable; LineageWeave does not invent defaults.
3. MCP keeps its transport admission charge and marks that charge when calling
   the shared service, so one accepted MCP submission is never charged twice.
   REST consumes the same principal quota inside the service.
4. Active-job admission takes a transaction-scoped PostgreSQL advisory lock
   derived from the normalized account identity, counts only queued/running
   jobs, and inserts within that transaction. No database transaction remains
   open during Valkey, worker, or contextual-orchestrator work.
5. Rejections expose bounded retry metadata and customer-actionable copy while
   never echoing question content or another principal's counts.

## Consequences

- REST can no longer bypass the distributed cost boundary.
- Parallel submissions for one account cannot overshoot the configured active
  work ceiling.
- An unmeasured deployment remains explicitly unavailable until it records
  capacity evidence.
- The advisory lock can conservatively serialize colliding hash keys; it does
  not weaken authorization or reveal account identity.

## Alternatives considered

- A process-local semaphore was rejected because replicas would disagree.
- A naked `count(*)` check was rejected because concurrent transactions could
  all pass before inserting.
- Fixed repository defaults were rejected because they would be unsupported
  rules of thumb rather than observed capacity.
