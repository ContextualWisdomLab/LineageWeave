"""Unit tests for source_post → Record mapping used by lineage rebuild."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from backend.app.lineage_ingestion import (
    interval_relations_for_post,
    persist_lineage_edges,
    reconstruct_group_key,
    records_from_source_posts,
    visible_lineage_graph,
)
from lineageweave.fixtures import sample_records
from lineageweave.lineage_persistence import lineage_edge_specs
from lineageweave.models import Edge


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


def test_persist_requires_observed_points_before_replacing_edges() -> None:
    class FakeConnection:
        calls: list[str] = []

        async def execute(self, query: str, *_args):
            self.calls.append(query)

    connection = FakeConnection()
    edge = Edge("parent", "child", 0.8, {})

    with pytest.raises(ValueError, match="child"):
        asyncio.run(
            persist_lineage_edges(
                connection,
                [edge],
                {"parent": {"created_at": datetime(2026, 1, 1)}},
            )
        )
    assert connection.calls == []


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

        async def fetch(self, query: str, *_args):
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


def test_visible_lineage_graph_attaches_allen_labels() -> None:
    class FakeConnection:
        posts = [
            {
                "post_id": "rec-002",
                "post_title": "Pricing renegotiation follow-up",
                "voc_type_code": "voc",
                "visibility_code": "public",
                "corporate_entity_id": "corp",
                "process_unit_id": "pu",
                "thread_group_key": "A-100",
                "created_at": datetime(2026, 1, 6),
            },
            {
                "post_id": "rec-003",
                "post_title": "Pricing renegotiation: revised quote sent",
                "voc_type_code": "voc",
                "visibility_code": "public",
                "corporate_entity_id": "corp",
                "process_unit_id": "pu",
                "thread_group_key": "A-100",
                "created_at": datetime(2026, 1, 10),
            },
        ]
        edges = [
            {
                "parent_post_id": "rec-002",
                "child_post_id": "rec-003",
                "fused_score": 0.9,
                "interval_relation_code": "interval_contains",
            }
        ]

        async def fetch(self, query: str, *_args):
            return self.edges if "post_lineage_edge" in query else self.posts

    graph = asyncio.run(
        visible_lineage_graph(FakeConnection(), lambda row: True, focus_post_id="rec-002")
    )
    assert graph["edges"][0]["interval_relation_code"] == "interval_contains"
    assert graph["edges"][0]["interval_relation_label"] == "Contains"


def test_interval_relations_for_post_orient_from_the_opened_child() -> None:
    class FakeConnection:
        edges = [
            {
                "parent_post_id": "rec-002",
                "child_post_id": "rec-003",
                "interval_relation_code": "interval_contains",
            }
        ]

        async def fetch(self, query: str, *_args):
            return self.edges

    from_parent = asyncio.run(interval_relations_for_post(FakeConnection(), "rec-002"))
    from_child = asyncio.run(interval_relations_for_post(FakeConnection(), "rec-003"))
    assert from_parent["rec-003"]["interval_relation_code"] == "interval_contains"
    assert from_parent["rec-003"]["interval_is_parent"] is True
    assert from_child["rec-002"]["interval_relation_code"] == "interval_during"
    assert from_child["rec-002"]["interval_relation_label"] == "During"
    assert from_child["rec-002"]["interval_is_parent"] is False
