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
# This used to be an explicit allowlist of every file number from 0012 up.
# It silently fell behind at 0103. Keep one fixed lower-bound pattern instead;
# shell arithmetic would treat leading zeroes as octal, and base#value is not
# portable under this script's POSIX /bin/sh contract (ADR 0166).
for migration in /opt/lineageweave/migrations/*.sql; do
    [ -f "$migration" ] || continue
    migration_name=${migration##*/}
    case "$migration_name" in
        000[0-9]_*|001[01]_*) continue ;;
        [0-9][0-9][0-9][0-9]_*) ;;
        *) continue ;;
    esac
    printf 'Applying %s\n' "$migration_name"
    psql -X -v ON_ERROR_STOP=1 \
        -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        -f "$migration"
done
