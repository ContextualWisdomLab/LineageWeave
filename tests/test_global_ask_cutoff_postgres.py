"""PostgreSQL regression for the final Global Ask cutoff boundary."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime

import asyncpg
import pytest

from backend.app.ask_project_history import read_authorized_ask_evidence_batch
from backend.app.post_chat_ingestion import (
    fetch_persisted_chats,
    gather_global_chat_sources,
)


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
                    updated_at timestamptz,
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

            await connection.execute(
                """
                create temporary table post_project_mention (
                    post_id uuid not null,
                    project_key text,
                    project_name text
                );
                create temporary table post_chat_result (
                    post_id uuid not null,
                    question_norm text not null,
                    question_text text not null,
                    answer_text text not null,
                    computed_at timestamptz not null,
                    knowledge_cutoff timestamptz not null,
                    primary key (post_id, question_norm)
                );
                create temporary table post_chat_citation (
                    post_id uuid not null,
                    question_norm text not null,
                    citation_ordinal integer not null,
                    cited_post_id uuid not null
                );
                insert into source_post (
                    post_id,
                    post_title,
                    visibility_code,
                    corporate_entity_id,
                    created_at,
                    source_project_code,
                    source_project_name
                ) values
                    (
                        '00000000-0000-4000-8000-000000000010',
                        'Synthetic future evidence',
                        'public',
                        null,
                        '2026-08-20T13:00:00Z',
                        'P-10',
                        'Synthetic project ten'
                    ),
                    (
                        '00000000-0000-4000-8000-000000000020',
                        'Synthetic tenant evidence',
                        'private',
                        '00000000-0000-4000-8000-000000000030',
                        '2026-08-20T11:00:00Z',
                        'P-20',
                        'Synthetic project twenty'
                    ),
                    (
                        '00000000-0000-4000-8000-000000000040',
                        'Synthetic Ask root',
                        'public',
                        null,
                        '2026-08-20T10:00:00Z',
                        'P-40',
                        'Synthetic project forty'
                    )
                """
            )
            await connection.execute(
                """
                insert into post_chat_result values
                    (
                        '00000000-0000-4000-8000-000000000040',
                        'first',
                        'First question',
                        'First answer',
                        '2026-08-20T11:00:00Z',
                        '2026-08-20T11:00:00Z'
                    ),
                    (
                        '00000000-0000-4000-8000-000000000040',
                        'second',
                        'Second question',
                        'Second answer',
                        '2026-08-20T12:00:00Z',
                        '2026-08-20T12:00:00Z'
                    );
                insert into post_chat_citation values
                    (
                        '00000000-0000-4000-8000-000000000040',
                        'first',
                        0,
                        '00000000-0000-4000-8000-000000000020'
                    ),
                    (
                        '00000000-0000-4000-8000-000000000040',
                        'second',
                        0,
                        '00000000-0000-4000-8000-000000000010'
                    )
                """
            )
            history = await fetch_persisted_chats(
                connection,
                "00000000-0000-4000-8000-000000000040",
            )
            assert [item["question_text"] for item in history] == [
                "First question",
                "Second question",
            ]
            future_id = "00000000-0000-4000-8000-000000000010"
            private_id = "00000000-0000-4000-8000-000000000020"
            later_cutoff = datetime(2026, 8, 20, 14, 0, tzinfo=UTC)
            projections = await read_authorized_ask_evidence_batch(
                connection,
                exchanges=[
                    ([future_id], CUTOFF),
                    ([future_id], later_cutoff),
                    ([private_id], later_cutoff),
                ],
                corporate_entity_ids=[
                    "00000000-0000-4000-8000-000000000099"
                ],
            )
            assert [item.all_citations_visible for item in projections] == [
                False,
                True,
                False,
            ]
            assert projections[1].cited_posts[0]["post_title"] == (
                "Synthetic future evidence"
            )
        finally:
            await connection.close()

    asyncio.run(scenario())
