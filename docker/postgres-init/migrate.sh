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

# ponytail: gate at the existing 0012 boundary; replace with a migration ledger
# when a new non-idempotent migration family is introduced.
for migration in /opt/lineageweave/migrations/*.sql; do
    migration_name=${migration##*/}
    case "$migration_name" in
        0012_*|0013_*|0014_*|0015_*|0016_*|0017_*|0018_*|0019_*|0020_*|0021_*|0022_*|0023_*|0024_*|0025_*|0026_*|0027_*|0028_*|0029_*|0030_*|0031_*|0032_*|0033_*|0034_*|0035_*|0036_*|0037_*|0038_*|0039_*|0040_*|0041_*|0042_*|0043_*|0044_*|0045_*) ;;
        *) continue ;;
    esac
    printf 'Applying %s\n' "$migration_name"
    psql -X -v ON_ERROR_STOP=1 \
        -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        -f "$migration"
done
