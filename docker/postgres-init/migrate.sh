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

    # 0248 is a one-time candidate seed whose rows become editable review data
    # after creation. Once its ownership record is committed, replaying the
    # historical seed would no longer be idempotent: it could overwrite reviewed
    # draft copy or reject a reviewed immutable publication. An ordinary product
    # delete retires the seed receipt rather than restoring historical seed
    # authority, so both owned and retired states are purpose-complete. Pending
    # or blocked ownership must still execute 0248 so incomplete first-run state
    # and unowned collisions fail closed.
    if [ "$migration_name" = "0248_customer_master_translation_draft.sql" ]; then
        customer_master_seed_state=$(
            psql -X -v ON_ERROR_STOP=1 -At \
                -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
                -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
                -c "select ownership_state from public.ui_translation_seed_ownership where migration_key = '0248_customer_master_translation_draft' and product_key = 'lineageweave' and screen_key = 'customer-master' and resource_version = 1"
        )
        case "$customer_master_seed_state" in
            owned|retired)
                printf 'Skipping %s: one-time candidate seed is %s; preserve review lifecycle\n' "$migration_name" "$customer_master_seed_state"
                continue
                ;;
        esac
    fi

    printf 'Applying %s\n' "$migration_name"
    migration_pgoptions="-c lineageweave.migration_file=$migration_name"
    if [ -n "${PGOPTIONS:-}" ]; then
        migration_pgoptions="$PGOPTIONS $migration_pgoptions"
    fi
    PGOPTIONS="$migration_pgoptions" \
        psql -X -v ON_ERROR_STOP=1 \
        -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        -f "$migration"
done
