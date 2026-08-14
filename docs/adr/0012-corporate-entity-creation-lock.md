# ADR 0012 — corporate-entity creation is serialized with a Postgres advisory transaction lock, not split into separate read/write databases

**Decision status:** Accepted  
**Date:** 2026-08-14

## Context

ADR 0010's `get_or_create_corporate_entity` introduced concurrent writes on the organization-creation path. A deterministic synthetic regression fixture reproduced a `DeadlockDetectedError`: two transactions created different `corporate_entity` rows in opposite order, so each transaction waited for a row-level lock held by the other.

This repository records the reproducible concurrency shape rather than customer, organization, batch, or production-log details. The architectural defect is independent of any particular dataset: multi-worker extraction can encounter child and parent organizations in different orders.

## Decision

Serialize only the *creation* write path with one named Postgres advisory transaction lock:

```sql
pg_advisory_xact_lock(
    hashtext('lineageweave:corporate_entity_creation')
)
```

The transaction-scoped lock is acquired immediately before persistence and is released automatically by the enclosing transaction's commit or rollback (PostgreSQL Global Development Group, 2024).

1. The lock is acquired only after inference and verification complete. Holding it across network I/O would unnecessarily serialize unrelated workers.
2. Under the lock, candidates are reloaded and similarity matching is repeated. Another transaction may have committed the same entity after the caller's original snapshot was read.
3. The key is one fixed creation-path key rather than a per-name key. Per-name locking still permits the opposite-order multi-entity deadlock shape `A: [X, Y]` versus `B: [Y, X]`.
4. The already-cataloged resolution path remains lock-free.

Splitting the system into separate read and write databases was considered and rejected. Replica separation does not resolve a write-write lock-ordering defect, while a transaction-scoped advisory lock directly enforces one global creation order.

## Consequences

- New entity creation is serialized cluster-wide. This is accepted because creation is the uncommon branch and correctness dominates throughput for this path.
- Resolution of existing entities remains concurrent and does not acquire the advisory lock.
- The lock is re-entrant within the same PostgreSQL session and transaction, so bounded parent-chain recursion does not self-deadlock.
- No schema split or additional service is required.
- The regression suite must retain concurrent opposite-order creation coverage.

## Related

This decision extends [ADR 0010](0010-corporate-hierarchy-auto-creation.md) with an explicit concurrency-safety property.

## References — APA 7th

PostgreSQL Global Development Group. (2024). *PostgreSQL 17 documentation: Advisory lock functions*. https://www.postgresql.org/docs/current/functions-admin.html#FUNCTIONS-ADVISORY-LOCKS
