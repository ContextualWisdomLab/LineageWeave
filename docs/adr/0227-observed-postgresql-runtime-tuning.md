# ADR 0227: Observed PostgreSQL runtime tuning

- Status: Accepted
- Date: 2026-08-26

## Context

The canonical PostgreSQL 16 runtime has accumulated substantially more
requested than timed checkpoints and millions of `wal_buffers_full` events.
The currently running full-text index scan is CPU-bound and produces negligible
new WAL, so it is not evidence for changing storage concurrency or maintenance
memory. Historical cumulative counters are also unsafe to combine when their
statistics-reset instants differ.

Static host-size profiles and conventional memory percentages would introduce
unsupported assumptions. PostgreSQL already supplies an automatic
`wal_buffers` calculation, a WAL-segment boundary, a configured checkpoint
interval, and cumulative workload counters. Those are the authoritative inputs
for the smallest measured correction.

## Decision

`scripts/plan_postgres_tuning.py` is the sole LineageWeave procedure for this
runtime tuning boundary. It performs two measurements separated by an
operator-declared observation duration and records:

- PostgreSQL version and statistics-reset instants;
- `pg_stat_wal` and checkpoint deltas;
- current durability and tuning settings;
- the default and current transaction isolation levels;
- `wal_segment_size` and the existing `checkpoint_timeout`;
- container memory limit, data-filesystem free bytes, and current `pg_wal`
  bytes.

The planner rejects counter resets, negative deltas, unsupported PostgreSQL
versions, incomplete durability evidence, or insufficient disk space. It emits
an immutable JSON audit plan and a Compose environment file. It never applies a
setting while PostgreSQL is running.

The planner separately calculates WAL rates for the explicit sample and for
PostgreSQL's own `stats_reset` to snapshot window. The calculated
`max_wal_size` is the larger of its current value and the higher observed rate
projected over one already-configured checkpoint interval, rounded upward to
PostgreSQL's own WAL-segment size. This preserves historical write pressure
when the immediate sample is a CPU-bound, zero-WAL scan and directly targets
the documented condition in which WAL growth starts a checkpoint before
`checkpoint_timeout`; it does not add a private safety multiplier. When neither
window supports a larger value, `max_wal_size` remains unchanged even if the
requested-checkpoint count is high, because that counter does not prove which
request source caused each checkpoint.

If either aligned observation window records at least one `wal_buffers_full` event,
`wal_buffers` becomes one measured WAL segment. PostgreSQL 16 documents one WAL
segment as the normal upper bound of its automatic selection. With no observed
full event, the current value remains unchanged.

The procedure does **not** infer `shared_buffers`, `maintenance_work_mem`,
`effective_io_concurrency`, `maintenance_io_concurrency`, or
`wal_compression`. Their documented trade-offs require workload-specific memory
or storage latency/IOPS evidence that the WAL/checkpoint observation does not
provide. A CPU-bound index scan is explicitly not storage-concurrency evidence.

`fsync`, `full_page_writes`, and `synchronous_commit` must all remain enabled.
Transaction isolation is a correctness invariant, not a WAL-throughput knob.
The planner records both `default_transaction_isolation` and the observation
session's `transaction_isolation`, rejects a mismatch or a change across the
measurement/restart boundary, and never chooses a stronger or weaker level
from WAL statistics. Any isolation-policy change requires a separate approved
decision and concurrency evidence.
The generated environment file is consumed only by the explicit
`docker-compose.postgres-tuned.yml` overlay during a controlled PostgreSQL
restart. The base Compose file remains the rollback path: remove the overlay
and restart PostgreSQL. The JSON plan records both proposed and rollback
values.

Immediately before that controlled restart, the procedure takes a new
PostgreSQL snapshot and new container-resource measurements. It fails closed
unless the server major version, current WAL settings, all three durability
settings, and both isolation settings still match the plan's rollback values;
unless the proposed WAL reservation still fits the measured free space and
the proposed WAL buffers fit the measured cgroup limit when one exists; and
unless PostgreSQL reports zero other active transactions and zero ungranted
locks. These are exact current-state gates, not inferred workload thresholds.
Compose validation alone does not authorize a restart, and an operator must
still provide a maintenance window that prevents new work from entering after
the final snapshot.

## Consequences

- A tuning proposal is reproducible from captured measurements and contains no
  hand-selected weights, ratios, or thresholds.
- A short or unrepresentative observation can retain current settings but
  cannot silently tune them.
- Increased `max_wal_size` can lengthen crash recovery and consume more disk;
  the plan exposes both effects and refuses a proposal whose exact additional
  reservation exceeds observed free space.
- Applying or rolling back requires an intentional service restart and normal
  post-restart health/config verification.
- A plan cannot carry old resource, correctness, or quiescence evidence across
  the restart boundary; any mismatch requires a new observation and approval.

## References

PostgreSQL Global Development Group. (2026a). *PostgreSQL 16 documentation:
20.5. Write ahead log*. https://www.postgresql.org/docs/16/runtime-config-wal.html

PostgreSQL Global Development Group. (2026b). *PostgreSQL 16 documentation:
30.5. WAL configuration*. https://www.postgresql.org/docs/16/wal-configuration.html

PostgreSQL Global Development Group. (2026c). *PostgreSQL 16 documentation:
20.4. Resource consumption*.
https://www.postgresql.org/docs/16/runtime-config-resource.html

PostgreSQL Global Development Group. (2026d). *PostgreSQL 16 documentation:
28.2. The cumulative statistics system*.
https://www.postgresql.org/docs/16/monitoring-stats.html

PostgreSQL Global Development Group. (2026e). *PostgreSQL 16 documentation:
54.12. pg_locks*.
https://www.postgresql.org/docs/16/view-pg-locks.html
