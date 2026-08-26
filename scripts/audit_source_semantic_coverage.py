"""Report aggregate-only source-field availability for semantic coverage."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from collections.abc import Mapping

import asyncpg

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


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
) -> dict[str, object]:
    """Return row and nonblank counts without reading source values."""
    coverage_options = (source_key, coverage_table, coverage_key)
    if any(value is not None for value in coverage_options) and not all(
        value is not None for value in coverage_options
    ):
        raise ValueError("source_key, coverage_table, and coverage_key are all required")
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
        row = await connection.fetchrow(query)
        result: dict[str, object] = {
            "row_count": row["row_count"],
            "semantic_role_nonblank_counts": {
                role: row[f"{role}_nonblank_count"] for role in columns
            },
        }
        if source_key and coverage_table and coverage_key:
            source_key_column = _identifier(source_key)
            coverage_key_column = _identifier(coverage_key)
            key_row = await connection.fetchrow(
                f"""
            with source_keys as (
                select distinct {source_key_column}::text as key_value
                  from {_table(table)}
                 where nullif(btrim({source_key_column}::text), '') is not null
            ), coverage_keys as (
                select distinct {coverage_key_column}::text as key_value
                  from {_table(coverage_table)}
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
                )
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
