#!/usr/bin/env bash
set -euo pipefail

: "${LINEAGEWEAVE_DSN:?[LINEAGEWEAVE_DSN] required: set to your authorized PostgreSQL DSN}"
: "${LINEAGE_SOURCE_TABLE:?[LINEAGE_SOURCE_TABLE] required: set to your authorized PostgreSQL source table}"

export LINEAGEWEAVE_DSN
export LINEAGE_SOURCE_TABLE

export LINEAGEWEAVE_LIMIT="${LINEAGEWEAVE_LIMIT:-0}"
export LINEAGEWEAVE_WRITE_REPORTS="${LINEAGEWEAVE_WRITE_REPORTS:-1}"
export LINEAGEWEAVE_SWEEP_CONTENT_INSPECTIONS="${LINEAGEWEAVE_SWEEP_CONTENT_INSPECTIONS:-0}"
export LINEAGEWEAVE_INSPECTION_DOCUMENT_LIMIT="${LINEAGEWEAVE_INSPECTION_DOCUMENT_LIMIT:-0}"

json_out="${LINEAGEWEAVE_JSON_OUT:-}"
analytics_out="${LINEAGEWEAVE_ANALYTICS_OUT:-}"
sweep_args=()
export_args=()
if [[ -n "$json_out" ]]; then
  export_args+=(--json-out "$json_out")
fi
if [[ -n "$analytics_out" ]]; then
  export_args+=(--analytics-out "$analytics_out")
fi
if [[ "$LINEAGEWEAVE_SWEEP_CONTENT_INSPECTIONS" == "1" ]]; then
  sweep_args+=(--sweep-content-inspections)
  if [[ "$LINEAGEWEAVE_INSPECTION_DOCUMENT_LIMIT" != "0" ]]; then
    if [[ ! "$LINEAGEWEAVE_INSPECTION_DOCUMENT_LIMIT" =~ ^[0-9]+$ ]]; then
      echo "invalid LINEAGEWEAVE_INSPECTION_DOCUMENT_LIMIT: must be a non-negative integer"
      exit 1
    fi
    sweep_args+=(--inspection-document-limit "$LINEAGEWEAVE_INSPECTION_DOCUMENT_LIMIT")
  fi
fi
python_cmd="python"
if command -v uv >/dev/null 2>&1; then
  python_cmd="uv run python"
fi

${python_cmd} - <<'PY'
import os
import psycopg
from psycopg import sql

dsn = os.environ["LINEAGEWEAVE_DSN"]
table = os.environ["LINEAGE_SOURCE_TABLE"]
if "." in table:
    schema, name = table.split(".", 1)
else:
    schema, name = "public", table

with psycopg.connect(dsn) as connection:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema=%s AND table_name=%s
            )
            """,
            (schema, name),
        )
        table_found = bool(cursor.fetchone()[0])
        if not table_found:
            raise SystemExit(f"source table not found: {table}")

        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema=%s AND table_name=%s
            ORDER BY ordinal_position
            """,
            (schema, name),
        )
        columns = {row[0] for row in cursor.fetchall()}

        required = {"guid_field", "docnosub_field", "acthguid_field", "voccts_field"}
        missing = sorted(required - columns)
        if missing:
            raise SystemExit(
                f"source table {table} missing required columns: {', '.join(missing)}"
            )

        quoted_table = sql.Identifier(schema, name)
        cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(quoted_table))
        count = cursor.fetchone()[0]
        print(f"source_table={table} row_count={count}")
PY

echo "lineageweave_contract_source=${LINEAGE_SOURCE_TABLE}"
if [[ "$LINEAGEWEAVE_WRITE_REPORTS" == "0" ]]; then
  uv run python lineageweave.py \
    --dsn "$LINEAGEWEAVE_DSN" \
    --table "$LINEAGE_SOURCE_TABLE" \
    "${export_args[@]}" \
    "${sweep_args[@]}" \
    ${LINEAGEWEAVE_LIMIT:+--limit "$LINEAGEWEAVE_LIMIT"}
else
  uv run python lineageweave.py \
    --dsn "$LINEAGEWEAVE_DSN" \
    --table "$LINEAGE_SOURCE_TABLE" \
    --write-reports \
    "${export_args[@]}" \
    "${sweep_args[@]}" \
    ${LINEAGEWEAVE_LIMIT:+--limit "$LINEAGEWEAVE_LIMIT"}
fi

printf 'lineageweave_contract_run_complete=%s json=%s analytics=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${json_out:-disabled}" "${analytics_out:-disabled}"
