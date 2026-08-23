# ADR 0144: Skip superseded search indexes during migration replay

- Status: Accepted
- Date: 2026-08-23

## Context

The Compose migration runner deliberately replays an idempotent migration
window on every existing volume. Migration 0035 creates two large legacy body
search indexes; migration 0036 replaces them with normalized rendered-text
indexes and drops the legacy pair. Replaying both files therefore rebuilt and
discarded hundreds of megabytes of indexes on every service restart.

## Decision

Migration 0035 checks for each corresponding 0036 successor index before
running its `CREATE INDEX CONCURRENTLY`. If the successor exists, the legacy
build is skipped. A fresh database still follows the original ordered path:
0035 creates its indexes, 0036 creates the normalized successors, then removes
the legacy pair. Existing volumes retain the replay safety of the current
migration runner without repeating superseded work.

The condition uses PostgreSQL `to_regclass` through psql's native `\gset` and
`\if` commands. No application-side migration ledger or second migration tool
is introduced.

## Consequences

- Existing-volume restarts no longer rebuild indexes that the next migration
  immediately deletes.
- Fresh initialization remains compatible with the historical migration
  order.
- A future non-idempotent migration family still requires the migration ledger
  already identified by `docker/postgres-init/migrate.sh`; this decision does
  not silently broaden that scope.

## Verification

- A static replay contract test requires both successor guards.
- Compose replay must exit successfully with only the normalized indexes
  present, then a second replay must not enter `pg_stat_progress_create_index`
  for the legacy names.
