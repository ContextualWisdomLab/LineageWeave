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
) -> dict[str, object]:
    """Return row and nonblank counts without reading source values."""
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
    finally:
        await connection.close()
    return {
        "row_count": row["row_count"],
        "semantic_role_nonblank_counts": {
            role: row[f"{role}_nonblank_count"] for role in columns
        },
    }


def _parser() -> argparse.ArgumentParser:
    """Build the aggregate-only audit command contract."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", required=True)
    parser.add_argument("--table", required=True)
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
            asyncio.run(audit_source_semantic_coverage(args.dsn, args.table, columns)),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
