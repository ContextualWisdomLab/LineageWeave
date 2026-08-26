"""Real-PostgreSQL contract test for the operations Dashboard projection."""

from __future__ import annotations

import os

import asyncpg
import pytest

from backend.app.operations_dashboard import fetch_operations_dashboard


_POSTGRES_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_DSN",
    "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave",
)


@pytest.mark.anyio
async def test_operations_dashboard_sql_binds_against_postgres() -> None:
    """Execute every Dashboard query through asyncpg's real parser and binder."""
    try:
        connection = await asyncpg.connect(_POSTGRES_DSN, timeout=2)
    except (OSError, asyncpg.PostgresError):
        pytest.skip("requires the migrated local Compose database")
    try:
        required_tables = (
            "operations_case_classification",
            "operations_case_missing_fact",
            "operations_case_milestone",
            "operations_case_missing_milestone",
            "topic_context_membership",
            "topic_activity_interval",
            "topic_post_context_influence",
        )
        for table_name in required_tables:
            if await connection.fetchval(
                "select to_regclass($1)", f"public.{table_name}"
            ) is None:
                pytest.skip(f"requires the migration that creates {table_name}")
        result = await fetch_operations_dashboard(connection, [])
        external_result = await fetch_operations_dashboard(connection, [], external_only=True)
    finally:
        await connection.close()

    assert result["total_post_count"] >= 0
    assert external_result["total_post_count"] == result["total_post_count"]
    assert result["topic_context"]["status_code"] in {"accepted", "unavailable"}


@pytest.fixture
def anyio_backend() -> str:
    """Use the installed asyncio backend for the asyncpg contract test."""
    return "asyncio"
