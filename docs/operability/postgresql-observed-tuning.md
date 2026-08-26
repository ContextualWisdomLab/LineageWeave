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
the procedure rejects a changed plan or a different approval value.

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
