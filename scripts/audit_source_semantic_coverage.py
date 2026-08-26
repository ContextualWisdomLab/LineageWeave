"""Report aggregate-only source-field availability for semantic coverage."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from collections.abc import Mapping

import asyncpg

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PROVENANCE_TABLES = frozenset(
    {
        "provenance_assertion",
        "provenance_class_definition",
        "provenance_class_hierarchy",
        "provenance_inverse_definition",
        "provenance_literal_value",
        "provenance_qualification_definition",
        "provenance_relation_definition",
        "provenance_relation_domain",
        "provenance_relation_hierarchy",
        "provenance_relation_resource_range",
        "provenance_resource",
        "provenance_resource_binding",
        "provenance_resource_type",
    }
)


def _identifier(value: str) -> str:
    """Quote one validated PostgreSQL identifier without accepting SQL syntax."""
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"invalid PostgreSQL identifier: {value!r}")
    return f'"{value}"'


def _table(value: str) -> str:
    """Quote a required schema-qualified PostgreSQL table name."""
    parts = value.split(".")
    if len(parts) != 2:
        raise ValueError("source table must be schema-qualified")
    return ".".join(_identifier(part) for part in parts)


async def audit_source_semantic_coverage(
    dsn: str,
    table: str,
    columns: Mapping[str, str],
    *,
    source_key: str | None = None,
    coverage_table: str | None = None,
    coverage_key: str | None = None,
    assertion_table: str | None = None,
    assertion_status: str | None = None,
    assertion_evidence: str | None = None,
    provenance_schema: str | None = None,
) -> dict[str, object]:
    """Return row and nonblank counts without reading source values."""
    coverage_options = (source_key, coverage_table, coverage_key)
    if any(value is not None for value in coverage_options) and not all(
        value is not None for value in coverage_options
    ):
        raise ValueError("source_key, coverage_table, and coverage_key are all required")
    source_key_column = _identifier(source_key) if source_key else None
    coverage_table_sql = _table(coverage_table) if coverage_table else None
    coverage_key_column = _identifier(coverage_key) if coverage_key else None
    assertion_options = (assertion_table, assertion_status, assertion_evidence)
    if any(value is not None for value in assertion_options) and not all(
        value is not None for value in assertion_options
    ):
        raise ValueError(
            "assertion_table, assertion_status, and assertion_evidence are all required"
        )
    assertion_table_sql = _table(assertion_table) if assertion_table else None
    assertion_status_column = (
        _identifier(assertion_status) if assertion_status else None
    )
    assertion_evidence_column = (
        _identifier(assertion_evidence) if assertion_evidence else None
    )
    provenance_schema_name = (
        _identifier(provenance_schema) if provenance_schema else None
    )
    projections = ["count(*)::bigint as row_count"]
    for role, column in columns.items():
        if not _IDENTIFIER.fullmatch(role):
            raise ValueError(f"invalid semantic role: {role!r}")
        quoted = _identifier(column)
        projections.append(
            f"count(*) filter (where nullif(btrim({quoted}::text), '') is not null)::bigint "
            f'as "{role}_nonblank_count"'
        )
    query = f"select {', '.join(projections)} from {_table(table)}"
    connection = await asyncpg.connect(dsn)
    try:
        # SQL identifiers cannot be bind parameters; every interpolated token
        # passed _identifier/_table's strict ASCII identifier grammar above.
        # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        row = await connection.fetchrow(query)
        result: dict[str, object] = {
            "row_count": row["row_count"],
            "semantic_role_nonblank_counts": {
                role: row[f"{role}_nonblank_count"] for role in columns
            },
        }
        if source_key and coverage_table and coverage_key:
            assert source_key_column and coverage_table_sql and coverage_key_column
            # Same identifier-only boundary as the aggregate query; no source
            # value is interpolated into this statement.
            # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            key_row = await connection.fetchrow(
                f"""
            with source_keys as (
                select distinct {source_key_column}::text as key_value
                  from {_table(table)}
                 where nullif(btrim({source_key_column}::text), '') is not null
            ), coverage_keys as (
                select distinct {coverage_key_column}::text as key_value
                  from {coverage_table_sql}
                 where nullif(btrim({coverage_key_column}::text), '') is not null
            )
            select count(source_keys.key_value)::bigint as source_key_count,
                   count(coverage_keys.key_value)::bigint as coverage_key_count,
                   count(*) filter (
                       where source_keys.key_value is not null
                         and coverage_keys.key_value is not null
                   )::bigint as matched_key_count,
                   count(*) filter (
                       where source_keys.key_value is not null
                         and coverage_keys.key_value is null
                   )::bigint as source_without_coverage_count,
                   count(*) filter (
                       where source_keys.key_value is null
                         and coverage_keys.key_value is not null
                   )::bigint as coverage_without_source_count
              from source_keys
              full join coverage_keys using (key_value)
            """
            )
            result["semantic_key_coverage"] = dict(key_row)
        if assertion_table_sql:
            assert assertion_status_column and assertion_evidence_column
            # All interpolated values are validated identifiers. Status values
            # are fixed governed literals, not caller or source data.
            # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            assertion_row = await connection.fetchrow(
                f"""
                select count(*)::bigint as assertion_count,
                       count(*) filter (where {assertion_status_column} = 'observed')::bigint as observed_count,
                       count(*) filter (where {assertion_status_column} = 'observed' and {assertion_evidence_column} is null)::bigint as observed_without_evidence_count,
                       count(*) filter (where {assertion_status_column} = 'inferred')::bigint as inferred_count,
                       count(*) filter (where {assertion_status_column} = 'inferred' and {assertion_evidence_column} is null)::bigint as inferred_without_direct_evidence_count,
                       count(*) filter (where {assertion_status_column} = 'predicted')::bigint as predicted_count,
                       count(*) filter (where {assertion_status_column} = 'predicted' and {assertion_evidence_column} is null)::bigint as predicted_without_direct_evidence_count,
                       count(*) filter (where {assertion_status_column} not in ('observed', 'inferred', 'predicted') or {assertion_status_column} is null)::bigint as ungoverned_status_count
                  from {assertion_table_sql}
                """
            )
            assertion_counts = dict(assertion_row)
            assertion_counts["source_evidence_boundary_complete"] = (
                assertion_counts["observed_without_evidence_count"] == 0
                and assertion_counts["ungoverned_status_count"] == 0
            )
            result["semantic_assertion_evidence"] = assertion_counts
        if provenance_schema_name:
            table_rows = await connection.fetch(
                """
                select table_name
                  from information_schema.tables
                 where table_schema = $1
                   and table_name = any($2::text[])
                """,
                provenance_schema,
                sorted(_PROVENANCE_TABLES),
            )
            present = {row["table_name"] for row in table_rows}
            result["normalized_provenance_schema"] = {
                "required_table_count": len(_PROVENANCE_TABLES),
                "present_table_count": len(present),
                "complete": present == _PROVENANCE_TABLES,
            }
        return result
    finally:
        await connection.close()


def _parser() -> argparse.ArgumentParser:
    """Build the aggregate-only audit command contract."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", required=True)
    parser.add_argument("--table", required=True)
    parser.add_argument("--source-key")
    parser.add_argument("--coverage-table")
    parser.add_argument("--coverage-key")
    parser.add_argument("--assertion-table")
    parser.add_argument("--assertion-status")
    parser.add_argument("--assertion-evidence")
    parser.add_argument("--provenance-schema")
    parser.add_argument(
        "--column",
        action="append",
        default=[],
        metavar="ROLE=COLUMN",
        help="repeatable semantic role to source-column mapping",
    )
    return parser


def main() -> None:
    """Run the audit and print only aggregate JSON."""
    args = _parser().parse_args()
    columns: dict[str, str] = {}
    for mapping in args.column:
        role, separator, column = mapping.partition("=")
        if not separator or not role or not column:
            raise SystemExit("--column must use ROLE=COLUMN")
        columns[role] = column
    print(
        json.dumps(
            asyncio.run(
                audit_source_semantic_coverage(
                    args.dsn,
                    args.table,
                    columns,
                    source_key=args.source_key,
                    coverage_table=args.coverage_table,
                    coverage_key=args.coverage_key,
                    assertion_table=args.assertion_table,
                    assertion_status=args.assertion_status,
                    assertion_evidence=args.assertion_evidence,
                    provenance_schema=args.provenance_schema,
                )
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
