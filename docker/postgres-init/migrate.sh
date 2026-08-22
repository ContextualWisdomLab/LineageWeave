#!/bin/sh
set -eu

: "${POSTGRES_HOST:=postgres}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
export PGPASSWORD="$POSTGRES_PASSWORD"

until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
    sleep 1
done

# ponytail: gate at the existing 0012 boundary; replace with a migration
# ledger when a new non-idempotent migration family is introduced.
#
# This used to be an explicit case-pattern whitelist of every file number
# from 0012 up. It silently fell behind as new migrations were added past
# the last-updated number (0103_tenant_settings.sql shipped with no entry
# here, so a fresh deployment never got it) -- a numeric boundary check
# can't go stale the same way. $((10#...)) forces base-10 arithmetic so a
# leading-zero number like "0103" isn't misread as octal.
for migration in /opt/lineageweave/migrations/*.sql; do
    migration_name=${migration##*/}
    migration_number=$((10#${migration_name%%_*}))
    # 0001-0011 are baked into the postgres image's
    # docker-entrypoint-initdb.d (docker/postgres-init/Dockerfile) at
    # container creation and must not be re-applied here.
    if [ "$migration_number" -lt 12 ]; then
        continue
    fi
    printf 'Applying %s\n' "$migration_name"
    psql -X -v ON_ERROR_STOP=1 \
        -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        -f "$migration"
done
