# ADR 0204 — Analysis-run delivery releases pooled connections during provider work

**Decision status:** Accepted
**Date:** 2026-08-25
**Related:** [0023](0023-analysis-run-outbox.md), issue [#566](https://github.com/ContextualWisdomLab/LineageWeave/issues/566)

## Context

Analysis-run delivery currently locks `analysis_run_outbox` inside a database
transaction and retains that transaction and its pooled connection while
ThreadWeave adjudication or TEPP transport waits on an external provider. A
large frozen snapshot can therefore occupy a row lock and scarce pool slot for
minutes. Moving the synchronous provider work to another thread frees the event
loop but does not release either database resource.

The claim must remain exclusive across the HTTP start path and the background
worker. A time-based application lease would require an unsupported expiry
constant and could admit a second writer while a valid deep provider run is
still executing.

## Decision

1. A delivery owns a PostgreSQL **session-level advisory lock** derived by
   PostgreSQL from the immutable analysis-run UUID. `pg_try_advisory_lock`
   fails immediately when another delivery owns the run. PostgreSQL releases
   the lock automatically if the dedicated lock session disconnects, including
   an ungraceful worker failure. No guessed lease duration or heartbeat ratio
   is introduced.
2. The advisory-lock session is opened outside the application pool and does
   not run the product reads or writes. It carries no open transaction while a
   provider executes. One active analysis run therefore consumes no pooled
   connection during provider latency.
3. A first short pooled transaction validates visibility, locks the outbox row,
   appends the immutable claim event, and materializes the frozen provider
   input. It commits before any adjudication or TEPP call.
4. Provider computation runs with no pooled connection and no open database
   transaction. Lineage uses only fast-mlsirm-estimated active-channel weights;
   TEPP remains the sole calibrated-measurement transport. No weight, theta,
   retry interval, or lease duration is invented locally.
5. A second short pooled transaction locks the outbox row again and atomically
   persists the complete result, terminal status, and delivered event. A
   provider failure leaves Running plus the durable claimed outbox item for an
   explicit retry; it cannot leave a partial graph or calibrated result.
6. If the advisory lock is already held, delivery returns a conflict that tells
   the caller to open the running analysis. It does not wait while retaining an
   HTTP request or pool slot.

## Consequences

- Provider latency no longer expands a database transaction or starves the
  application pool.
- PostgreSQL session cleanup supplies crash recovery without a rule-of-thumb
  timeout.
- The dedicated advisory-lock session is bounded to one per concurrently
  executing analysis run and is visible in `pg_locks` for operations audit.
- Result persistence remains all-or-nothing in one short transaction.

## References

PostgreSQL Global Development Group. (2026a). *PostgreSQL 18.6 documentation:
13.3 explicit locking*. https://www.postgresql.org/docs/18/explicit-locking.html

PostgreSQL Global Development Group. (2026b). *PostgreSQL 18.6 documentation:
9.28 system administration functions*.
https://www.postgresql.org/docs/18/functions-admin.html
