"""PostgreSQL regression for the final Global Ask cutoff boundary."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime

import asyncpg
import pytest

from backend.app.post_chat_ingestion import gather_global_chat_sources


CUTOFF = datetime(2026, 8, 20, 12, 0, tzinfo=UTC)
POSTGRES_DSN = os.environ.get("LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN")


@pytest.mark.skipif(not POSTGRES_DSN, reason="requires PostgreSQL integration DSN")
def test_final_global_source_query_binds_the_cutoff_in_real_postgresql() -> None:
    """The final authorized-source SQL binds every positional parameter."""

    async def scenario() -> None:
        connection = await asyncpg.connect(POSTGRES_DSN)
        try:
            await connection.execute(
                """
                create temporary table source_post (
                    post_id uuid primary key,
                    post_title text,
                    post_body text,
                    visibility_code text,
                    corporate_entity_id uuid,
                    created_at timestamptz,
                    source_system_code text,
                    source_record_key text,
                    source_author_code text,
                    source_author_name text,
                    source_company_code text,
                    source_company_name text,
                    source_process_unit_code text,
                    source_process_unit_name text,
                    source_sales_pool_code text,
                    source_sales_pool_name text,
                    source_customer_code text,
                    source_customer_name text,
                    source_project_code text,
                    source_project_name text,
                    source_draft_code text,
                    source_deleted_flag text
                )
                """
            )

            class PostgresBoundary:
                """Execute only the final source query against PostgreSQL."""

                def __init__(self) -> None:
                    self.final_args: tuple[object, ...] | None = None

                async def fetch(self, query: str, *args: object):
                    if "array_position($2::uuid[], post_id)" in query:
                        self.final_args = args
                        return await connection.fetch(query, *args)
                    return []

            boundary = PostgresBoundary()
            result = await gather_global_chat_sources(
                boundary,
                lambda _row: True,
                ["00000000-0000-4000-8000-000000000001"],
                question="synthetic project",
                limit=2,
                knowledge_cutoff=CUTOFF,
            )
            assert result == []
            assert boundary.final_args is not None
            assert len(boundary.final_args) == 4
            assert list(boundary.final_args[0]) == [
                "00000000-0000-4000-8000-000000000001"
            ]
            assert boundary.final_args[3] == CUTOFF
        finally:
            await connection.close()

    asyncio.run(scenario())
