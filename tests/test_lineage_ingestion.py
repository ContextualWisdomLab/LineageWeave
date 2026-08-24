"""Unit tests for source_post → Record mapping used by lineage rebuild."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import asyncpg

import pytest

from backend.app.lineage_ingestion import (
    ChannelWeightsNotEstimated,
    load_estimated_channel_weights,
    rebuild_lineage,
    reconstruct_group_key,
    records_from_source_posts,
    visible_lineage_graph,
)
from lineageweave.fixtures import sample_records
from lineageweave.lineage_persistence import lineage_edge_specs


def test_missing_weight_table_rolls_back_before_fallback() -> None:
    class _MissingTableConnection:
        aborted = False

        class Savepoint:
            def __init__(self, connection: _MissingTableConnection) -> None:
                self.connection = connection

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback) -> bool:
                self.connection.aborted = False
                return False

        def transaction(self):
            return self.Savepoint(self)

        async def fetch(self, query: str):
            if "lineage_channel_weight" in query:
                self.aborted = True
                raise asyncpg.UndefinedTableError("synthetic missing table")
            if self.aborted:
                raise asyncpg.InFailedSQLTransactionError("transaction is aborted")
            return []

    connection = _MissingTableConnection()
    weights = asyncio.run(
        load_estimated_channel_weights(
            connection, {"temporal", "secondary_key", "text"}
        )
    )
    asyncio.run(connection.fetch("select 1"))

    assert weights is None


def test_weight_loader_picks_the_set_matching_the_active_channels() -> None:
    """Migration 0136: one persisted set per active channel combination.

    A 3-channel rebuild and a 4-channel (llm-inclusive) analysis run each
    get exactly their own estimated set; an active combination with no
    matching set falls back (None), never a partial mix.
    """

    class _SetsConnection:
        def transaction(self):
            class _Tx:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, exc_type, exc, traceback) -> bool:
                    return False

            return _Tx()

        async def fetch(self, query: str):
            return [
                {"channel_set_code": "channel_set_deterministic", "channel_code": "temporal", "weight_value": 0.8},
                {"channel_set_code": "channel_set_deterministic", "channel_code": "secondary_key", "weight_value": 0.15},
                {"channel_set_code": "channel_set_deterministic", "channel_code": "text", "weight_value": 0.05},
                {"channel_set_code": "channel_set_with_llm", "channel_code": "temporal", "weight_value": 0.5},
                {"channel_set_code": "channel_set_with_llm", "channel_code": "secondary_key", "weight_value": 0.1},
                {"channel_set_code": "channel_set_with_llm", "channel_code": "text", "weight_value": 0.05},
                {"channel_set_code": "channel_set_with_llm", "channel_code": "llm", "weight_value": 0.35},
            ]

    connection = _SetsConnection()
    deterministic = asyncio.run(
        load_estimated_channel_weights(connection, {"temporal", "secondary_key", "text"})
    )
    assert deterministic == {"temporal": 0.8, "secondary_key": 0.15, "text": 0.05}
    with_llm = asyncio.run(
        load_estimated_channel_weights(
            connection, {"temporal", "secondary_key", "text", "llm"}
        )
    )
    assert with_llm is not None and with_llm["llm"] == 0.35
    unmatched = asyncio.run(
        load_estimated_channel_weights(connection, {"temporal", "text"})
    )
    assert unmatched is None


def test_rebuild_fails_closed_without_an_estimated_weight_set() -> None:
    """ADR 0145 (amended): no estimate -> no reconstruction on constants.

    The raised message must name the next action (run the estimation
    script) so the operator is never left guessing.
    """

    class _NoWeightsConnection:
        def transaction(self):
            class _Tx:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, exc_type, exc, traceback) -> bool:
                    return False

            return _Tx()

        async def fetch(self, query: str):
            if "lineage_channel_weight" in query:
                raise asyncpg.UndefinedTableError("synthetic missing table")
            return []

    with pytest.raises(ChannelWeightsNotEstimated) as raised:
        asyncio.run(rebuild_lineage(_NoWeightsConnection()))
    assert "estimate_channel_weights" in str(raised.value)


def test_records_use_persisted_thread_keys_not_process_unit_or_voc_type() -> None:
    rows = [
        {
            "post_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "process_unit_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "corporate_entity_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "post_title": "Pricing renegotiation follow-up",
            "voc_type_code": "voc",
            "thread_group_key": "A-100",
            "secondary_grouping_key": "proj-alpha",
            "created_at": datetime(2026, 1, 6, tzinfo=timezone.utc),
        }
    ]
    records = records_from_source_posts(rows)
    assert records[0].group_key == "A-100"
    assert records[0].secondary_key == "proj-alpha"
    assert records[0].occurred_at.tzinfo is None


def test_records_fall_back_to_corporate_entity_when_thread_keys_are_empty() -> None:
    rows = [
        {
            "post_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "process_unit_id": None,
            "corporate_entity_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "post_title": "Corp-only post",
            "voc_type_code": "vom",
            "thread_group_key": "",
            "secondary_grouping_key": "",
            "created_at": datetime(2026, 2, 1),
        }
    ]
    records = records_from_source_posts(rows)
    assert records[0].group_key == "cccccccc-cccc-cccc-cccc-cccccccccccc"
    assert records[0].secondary_key == ""
    assert records[0].label == "Corp-only post"


def test_display_group_matches_reconstruct_group_key() -> None:
    """The DAG's group field is reconstruct's key, not voc type or PU."""
    a100 = {
        "process_unit_id": "shared-pu",
        "corporate_entity_id": "shared-corp",
        "thread_group_key": "A-100",
    }
    ungrouped = {
        "process_unit_id": "shared-pu",
        "corporate_entity_id": "shared-corp",
        "thread_group_key": "",
    }
    assert reconstruct_group_key(a100) == "A-100"
    assert reconstruct_group_key(ungrouped) == "shared-pu"


def test_seed_shaped_rows_rebuild_to_the_designed_a100_fork() -> None:
    """The mapping rebuild uses: fixture group/secondary + occurred_at.

    This is the same column set seed writes. If voc_type or process_unit
    were used instead, A-100/B-200 collapse and the rec-002 fork is lost.
    """
    rows = []
    for rec in sample_records():
        rows.append(
            {
                "post_id": rec.record_id,
                "process_unit_id": "shared-pu",
                "corporate_entity_id": "shared-corp",
                "post_title": rec.label,
                "voc_type_code": "voc" if rec.secondary_key else "vom",
                "thread_group_key": rec.group_key,
                "secondary_grouping_key": rec.secondary_key,
                "created_at": rec.occurred_at,
            }
        )
    edges = lineage_edge_specs(records_from_source_posts(rows))
    pairs = {(edge.parent_id, edge.child_id) for edge in edges}
    assert ("rec-002", "rec-003") in pairs
    assert ("rec-002", "rec-004") in pairs
    assert "rec-006" not in {edge.child_id for edge in edges}


def test_focused_lineage_graph_includes_a_post_outside_landing_limit() -> None:
    class FakeConnection:
        posts = [
            {
                "post_id": "post-a",
                "post_title": "A",
                "voc_type_code": "voc",
                "visibility_code": "public",
                "corporate_entity_id": "corp",
                "process_unit_id": "pu",
                "thread_group_key": "thread-a",
                "created_at": datetime(2026, 1, 1),
            },
            {
                "post_id": "post-b",
                "post_title": "B",
                "voc_type_code": "voc",
                "visibility_code": "public",
                "corporate_entity_id": "corp",
                "process_unit_id": "pu",
                "thread_group_key": "thread-a",
                "created_at": datetime(2026, 1, 2),
            },
            {
                "post_id": "post-c",
                "post_title": "C",
                "voc_type_code": "voc",
                "visibility_code": "public",
                "corporate_entity_id": "corp",
                "process_unit_id": "pu",
                "thread_group_key": "thread-c",
                "created_at": datetime(2026, 1, 3),
            },
        ]
        edges = [
            {"parent_post_id": "post-a", "child_post_id": "post-b", "fused_score": 0.8}
        ]

        async def fetch(self, query: str):
            return self.edges if "post_lineage_edge" in query else self.posts

    connection = FakeConnection()
    landing = asyncio.run(visible_lineage_graph(connection, lambda row: True, limit=1))
    focused = asyncio.run(
        visible_lineage_graph(connection, lambda row: True, limit=1, focus_post_id="post-a")
    )
    isolated = asyncio.run(
        visible_lineage_graph(connection, lambda row: True, limit=1, focus_post_id="post-c")
    )

    assert [node["id"] for node in landing["nodes"]] == ["post-c"]
    assert {node["id"] for node in focused["nodes"]} == {"post-a", "post-b"}
    assert len(focused["edges"]) == 1
    assert focused["truncated"] is False
    assert isolated == {"nodes": [], "edges": [], "truncated": False}
