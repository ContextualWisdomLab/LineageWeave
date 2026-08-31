# PostgreSQL observed tuning procedure

This procedure produces a plan before it changes a service. Run it only after
the canonical migration and other controlled database work have completed.
The observation duration is required rather than defaulted: select a window
that contains the workload being tuned and record that choice with the plan.

```bash
uv run python scripts/plan_postgres_tuning.py plan \
  --sample-seconds "$OBSERVATION_SECONDS" \
  --output /tmp/lineageweave-postgres-tuning-plan.json

uv run python scripts/plan_postgres_tuning.py validate \
  --plan /tmp/lineageweave-postgres-tuning-plan.json \
  --env-output /tmp/lineageweave-postgres-tuning.env
```

Review the JSON evidence, proposed settings, exact disk reservation, retained
settings, and rollback values. Validation renders the Compose configuration but
does not touch a container.

Apply only in an approved restart window. Copy the printed `plan_id` exactly;
the procedure rejects a changed plan or a different approval value. Immediately
before recreation it also re-reads the PostgreSQL major version, WAL,
durability and isolation settings, active-transaction and waiting-lock totals,
cgroup memory limit, data-filesystem free bytes, and current `pg_wal` bytes.
Any mismatch, non-zero transaction/lock total, or insufficient current resource
measurement aborts without restarting PostgreSQL. Keep the maintenance window
closed to new work after that final snapshot.

```bash
uv run python scripts/plan_postgres_tuning.py apply \
  --plan /tmp/lineageweave-postgres-tuning-plan.json \
  --env-output /tmp/lineageweave-postgres-tuning.env \
  --approve-plan-id "$APPROVED_PLAN_ID"
```

After PostgreSQL becomes healthy, compare `SHOW max_wal_size`,
`SHOW wal_buffers`, all three durability settings, `pg_stat_wal`, and
checkpoint counters with the plan. Do not attribute the CPU time of an active
GIN scan to WAL or storage concurrency when its sampled WAL delta is zero.

Rollback uses the plan's captured pre-change values and the same controlled
restart gate:

```bash
uv run python scripts/plan_postgres_tuning.py rollback \
  --plan /tmp/lineageweave-postgres-tuning-plan.json \
  --env-output /tmp/lineageweave-postgres-rollback.env \
  --approve-plan-id "$APPROVED_PLAN_ID"
```

The base `docker-compose.yml` contains no tuned command. Removing the tuning
overlay and recreating PostgreSQL is the secondary rollback path.

## Non-identifying canonical observation — 2026-08-27

Since the 2026-08-24 statistics reset, the canonical PostgreSQL 16 instance
reported 25,308 requested checkpoints versus 382 timed checkpoints, 336.7 GB
of WAL, 7,598,680 `wal_buffers_full` events, 81,194,401 backend buffer writes,
and no lock waiter at capture. The running configuration retained
`wal_level=replica`, `max_wal_size=1GB`, and `shared_buffers=128MB` under read
committed isolation.

This snapshot confirms severe cumulative pressure, not an apply value.
PostgreSQL documents that `max_wal_size` pressure can start a checkpoint before
`checkpoint_timeout`, that high WAL output can require more WAL buffers, and
that its own WAL recycling estimate adapts to prior checkpoint cycles. Run the
aligned planner across the representative write workload before applying its
segment-aligned proposal. The snapshot supplies no evidence for changing
`shared_buffers`, durability, isolation, or storage concurrency.

The canonical capture did not expose `pg_stat_statements`, so historical
per-query aggregates remain unverified. Do not install or preload the extension
as part of WAL tuning: that requires its own restart approval and a decision for
query-text retention. Use the repository's bounded, rollback-only `EXPLAIN`
procedure when a named operation needs plan evidence.
