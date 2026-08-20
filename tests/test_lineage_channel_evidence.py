"""Regression tests for explainable Event Lineage edge evidence."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from backend.app.lineage_ingestion import persist_lineage_edges, visible_lineage_graph
from lineageweave.models import Edge


class _PersistConnection:
    """Capture database writes without pretending they succeeded elsewhere."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def execute(self, query: str, *arguments: Any) -> str:
        self.calls.append((query, arguments))
        return "OK"


def test_persist_lineage_edges_writes_each_channel_as_a_normalized_child_row() -> None:
    connection = _PersistConnection()
    edge = Edge(
        parent_id="11111111-1111-1111-1111-111111111111",
        child_id="22222222-2222-2222-2222-222222222222",
        fused_score=0.73,
        channel_scores={
            "temporal": 0.8,
            "secondary_key": 1.0,
            "text": 0.4,
            "llm": 0.7,
        },
    )

    asyncio.run(persist_lineage_edges(connection, [edge]))

    channel_writes = [
        arguments
        for query, arguments in connection.calls
        if "insert into lineage_edge_channel_score" in query
    ]
    assert channel_writes == [
        (
            edge.parent_id,
            edge.child_id,
            "lineage_channel_llm",
            0.7,
        ),
        (
            edge.parent_id,
            edge.child_id,
            "lineage_channel_secondary_key",
            1.0,
        ),
        (
            edge.parent_id,
            edge.child_id,
            "lineage_channel_temporal",
            0.8,
        ),
        (
            edge.parent_id,
            edge.child_id,
            "lineage_channel_text",
            0.4,
        ),
    ]


def test_persist_lineage_edges_rejects_unknown_or_out_of_range_channel_evidence() -> None:
    unknown = Edge("parent", "child", 0.5, {"mystery": 0.5})
    invalid = Edge("parent", "child", 0.5, {"text": 1.01})

    with pytest.raises(ValueError, match="unsupported lineage channel"):
        asyncio.run(persist_lineage_edges(_PersistConnection(), [unknown]))
    with pytest.raises(ValueError, match="between 0 and 1"):
        asyncio.run(persist_lineage_edges(_PersistConnection(), [invalid]))


class _ReadConnection:
    """Return one visible edge and record the bounded channel query."""

    def __init__(self) -> None:
        self.channel_arguments: tuple[Any, ...] | None = None

    async def fetch(self, query: str, *arguments: Any) -> list[dict[str, Any]]:
        if "from source_post" in query:
            return [
                {
                    "post_id": "post-a",
                    "post_title": "Initial event",
                    "voc_type_code": "voc",
                    "visibility_code": "public",
                    "corporate_entity_id": "corp",
                    "process_unit_id": "pu",
                    "thread_group_key": "thread-a",
                    "created_at": datetime(2026, 1, 1),
                },
                {
                    "post_id": "post-b",
                    "post_title": "Follow-up event",
                    "voc_type_code": "voc",
                    "visibility_code": "public",
                    "corporate_entity_id": "corp",
                    "process_unit_id": "pu",
                    "thread_group_key": "thread-a",
                    "created_at": datetime(2026, 1, 2),
                },
            ]
        if "from lineage_edge_channel_score" in query:
            self.channel_arguments = arguments
            return [
                {
                    "parent_post_id": "post-a",
                    "child_post_id": "post-b",
                    "channel_code": "lineage_channel_temporal",
                    "channel_score": 0.9,
                },
                {
                    "parent_post_id": "post-a",
                    "child_post_id": "post-b",
                    "channel_code": "lineage_channel_secondary_key",
                    "channel_score": 1.0,
                },
                {
                    "parent_post_id": "post-a",
                    "child_post_id": "post-b",
                    "channel_code": "lineage_channel_text",
                    "channel_score": 0.42,
                },
            ]
        if "from post_lineage_edge" in query:
            return [
                {
                    "parent_post_id": "post-a",
                    "child_post_id": "post-b",
                    "fused_score": 0.78,
                }
            ]
        raise AssertionError(f"unexpected query: {query}")


def test_visible_lineage_graph_exposes_exact_channel_scores_without_inventing_llm() -> None:
    connection = _ReadConnection()
    graph = asyncio.run(visible_lineage_graph(connection, lambda row: True))

    assert graph["edges"] == [
        {
            "source": "post-a",
            "target": "post-b",
            "fused_score": 0.78,
            "channel_scores": {
                "temporal": 0.9,
                "secondary_key": 1.0,
                "text": 0.42,
            },
        }
    ]
    assert "llm" not in graph["edges"][0]["channel_scores"]
    assert connection.channel_arguments == (["post-a", "post-b"],)


def test_channel_score_migration_is_normalized_bounded_and_reversible() -> None:
    migration = Path("migrations/0053_lineage_edge_channel_score.sql").read_text(
        encoding="utf-8"
    )
    rollback = Path(
        "migrations/rollback/0053_lineage_edge_channel_score.sql"
    ).read_text(encoding="utf-8")
    docker_migrate = Path("docker/postgres-init/migrate.sh").read_text(
        encoding="utf-8"
    )

    assert "create table if not exists lineage_edge_channel_score" in migration
    assert "create index if not exists lineage_edge_channel_score_channel_idx" in migration
    assert "primary key (parent_post_id, child_post_id, channel_code)" in migration
    assert "references post_lineage_edge" in migration
    assert "on delete cascade" in migration
    assert "channel_code in (" in migration
    for channel_code in (
        "lineage_channel_temporal",
        "lineage_channel_secondary_key",
        "lineage_channel_text",
        "lineage_channel_llm",
    ):
        assert channel_code in migration
    assert "channel_score >= 0" in migration
    assert "channel_score <= 1" in migration
    assert "drop table if exists lineage_edge_channel_score" in rollback
    assert "0053_*" in docker_migrate
