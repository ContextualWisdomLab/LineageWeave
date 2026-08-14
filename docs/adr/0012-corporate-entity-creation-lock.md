# ADR 0012 — corporate-entity creation is serialized with a Postgres advisory transaction lock, not split into separate read/write databases

**Decision status:** Accepted
**Date:** 2026-08-14

## Context

ADR 0010's `get_or_create_corporate_entity` made real writes on a real
concurrent path for the first time: many workers extract many posts in
parallel, and each worker independently resolves-or-creates the
organizations it encounters. A real Milestone 2 batch run under real
concurrency surfaced a genuine `DeadlockDetectedError`: two concurrent
transactions, each creating a different new `corporate_entity` row
(one a plant, the other that plant's own parent company, mentioned in
the opposite creation order by a different post processed at the same
time), took row-level locks on `corporate_entity` in opposite order
and deadlocked. This is not a hypothetical -- it was observed once in
the live batch log before this fix.

## Decision

Serialize only the *creation* write path with a single named Postgres
advisory transaction lock, `pg_advisory_xact_lock(hashtext('lineageweave:corporate_entity_creation'))`
(PostgreSQL Global Development Group, 2024, Table 9.94), taken
immediately before the insert and automatically released at the
enclosing transaction's commit or rollback:

1. The lock is acquired only after inference and Searxng verification
   complete -- both are slow network round trips, and holding an
   advisory lock across an HTTP call would serialize every concurrent
   worker's network I/O for no reason. The lock protects only the
   write itself.
2. Under the lock, candidates are re-read fresh
   (`_reload_candidates`) and re-checked with the existing similarity
   match before inserting -- a concurrent transaction may have
   committed the exact same entity between this call's own
   verification step and the lock acquisition; the caller's
   in-memory `candidates` snapshot cannot see that.
3. The lock key is a single fixed string, not derived per-entity-name.
   Per-name locking would still deadlock across concurrent
   *multi*-entity creates (transaction A creates `[X, Y]` while B
   concurrently creates `[Y, X]` is the identical opposite-order
   deadlock shape one level down). One coarse lock correctly
   serializes the whole creation path, which is acceptable because
   creation is the rare branch -- the overwhelming majority of
   organization mentions resolve through the lock-free,
   fully-concurrent similarity-matching fast path ADR 0010 already
   established.

Splitting into separate read and write databases (the standing
project brief's own stated fallback, "관리가 불가능하다면 Read DB와
Write DB를 나눌 것") was considered and rejected: this data shape has
no read-replica lag concern to solve, and a single named advisory lock
is a complete, standard fix for the actual observed failure (write-write
lock-ordering deadlock on a rare creation path), not a symptom the
architecture itself is unable to manage.

## Consequences

- Entity creation throughput is now serialized to one at a time
  cluster-wide. Accepted because creation is rare (most mentions hit
  the lock-free resolution fast path) and correctness (no deadlock
  aborts, no duplicate rows for one organization) matters more than
  throughput on this specific, infrequent branch.
- The lock is re-entrant across this function's own bounded parent-chain
  recursion (ADR 0010's `_MAX_HIERARCHY_DEPTH`) because Postgres
  advisory transaction locks are re-entrant within the same session/
  transaction -- a child call taking the same lock inside a parent
  call's already-open transaction does not self-deadlock.
- No new dependency, no schema change, and no read/write database split
  was required -- the fix is scoped entirely to the creation call path
  already introduced in ADR 0010.

## Related

Extends [ADR 0010](0010-corporate-hierarchy-auto-creation.md)'s
creation path with the concurrency-safety property it did not yet have
under real multi-worker load.

## References (APA 7th)

PostgreSQL Global Development Group. (2024). *PostgreSQL 17 documentation: Chapter 9.94, advisory lock functions*. https://www.postgresql.org/docs/current/functions-admin.html#FUNCTIONS-ADVISORY-LOCKS
