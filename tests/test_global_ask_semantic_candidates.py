"""Focused checks for persisted semantic candidate nomination."""

from __future__ import annotations

import asyncio
from pathlib import Path

from backend.app.global_ask_semantic_candidates import semantic_candidate_post_ids


_MIGRATION = Path(__file__).parents[1] / "migrations" / "0225_global_ask_semantic_candidate_search.sql"


def test_semantic_candidates_use_bounded_native_full_text_search() -> None:
    """Persisted semantic and graph evidence nominate IDs without local weights."""
    calls: list[tuple[str, tuple[object, ...]]] = []

    class FakeConnection:
        async def fetch(self, query: str, *args: object):
            calls.append((query, args))
            return [{"post_id": "semantic-post"}]

    assert asyncio.run(
        semantic_candidate_post_ids(
            FakeConnection(),
            "risk owner",
            maximum_candidates=4,
            authorized_corporate_entity_ids=["entity-one"],
            authorized_process_unit_ids=["unit-one"],
            date_from=None,
            date_to=None,
        )
    ) == ["semantic-post"]

    query, args = calls[0]
    assert "websearch_to_tsquery('simple', $1)" in query
    assert "from post_project_mention" in query
    assert "from post_summary_role" in query
    assert "from post_person_mention" in query
    assert "from post_organization_mention" in query
    assert "from post_team_mention" in query
    assert "from knowledge_graph_edge" in query
    assert "post.corporate_entity_id::text = any($3::text[])" in query
    assert "post.process_unit_id::text = any($4::text[])" in query
    assert "post.source_draft_code" in query
    assert "post.source_deleted_flag" in query
    assert "limit $2" in query
    assert "ts_rank" not in query
    assert args == ("risk owner", 4, ["entity-one"], ["unit-one"], None, None)


def test_semantic_candidates_skip_empty_or_zero_budget_queries() -> None:
    """Invalid candidate requests do not touch PostgreSQL."""

    class FakeConnection:
        async def fetch(self, _query: str, *_args: object):
            raise AssertionError("no query expected")

    assert asyncio.run(
        semantic_candidate_post_ids(
            FakeConnection(),
            "  ",
            maximum_candidates=4,
            authorized_corporate_entity_ids=[],
            authorized_process_unit_ids=[],
            date_from=None,
            date_to=None,
        )
    ) == []
    assert asyncio.run(
        semantic_candidate_post_ids(
            FakeConnection(),
            "risk",
            maximum_candidates=0,
            authorized_corporate_entity_ids=[],
            authorized_process_unit_ids=[],
            date_from=None,
            date_to=None,
        )
    ) == []


def test_semantic_candidate_indexes_match_query_evidence_families() -> None:
    """The replay-safe migration indexes every persisted nomination family."""
    sql = _MIGRATION.read_text(encoding="utf-8")

    assert "not index_state.indisvalid" in sql
    assert sql.index("\\gexec") < sql.index("create index concurrently if not exists")
    assert sql.count("create index concurrently if not exists") == 7
    for table_name in (
        "post_project_mention",
        "post_summary_role",
        "cataloged_person",
        "post_person_mention",
        "corporate_entity",
        "cataloged_team",
        "knowledge_graph_edge",
    ):
        assert f"on {table_name} using gin" in sql
    assert "to_tsvector('simple'" in sql
