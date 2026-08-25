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
        result = await fetch_operations_dashboard(connection, [])
    finally:
        await connection.close()

    assert result["total_post_count"] >= 0
    assert result["topic_context"]["status_code"] in {"accepted", "unavailable"}


@pytest.fixture
def anyio_backend() -> str:
    """Use the installed asyncio backend for the asyncpg contract test."""
    return "asyncio"
