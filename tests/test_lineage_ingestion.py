"""Unit tests for source_post → Record mapping used by lineage rebuild."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from backend.app.lineage_ingestion import (
    lineage_coverage_summary,
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
    assert focused["isolation_reason"] is None
    assert landing["isolation_reason"] is None
    # ADR 0143: post-c is the sole visible member of "thread-c" -- nothing
    # existed to compare it against, distinct from a checked-and-unrelated post.
    assert isolated == {
        "nodes": [],
        "edges": [],
        "truncated": False,
        "isolation_reason": "no_comparison_group",
    }


def test_isolation_reason_distinguishes_no_relation_from_no_comparison_group() -> None:
    """ADR 0143: a post with real groupmates but zero edges is a different
    fact than a post with no groupmates at all."""

    class FakeConnection:
        posts = [
            {
                "post_id": "post-x",
                "post_title": "X",
                "voc_type_code": "voc",
                "visibility_code": "public",
                "corporate_entity_id": "corp",
                "process_unit_id": "pu",
                "thread_group_key": "thread-shared",
                "created_at": datetime(2026, 1, 1),
            },
            {
                "post_id": "post-y",
                "post_title": "Y",
                "voc_type_code": "voc",
                "visibility_code": "public",
                "corporate_entity_id": "corp",
                "process_unit_id": "pu",
                "thread_group_key": "thread-shared",
                "created_at": datetime(2026, 1, 2),
            },
            {
                "post_id": "post-lonely",
                "post_title": "Lonely",
                "voc_type_code": "voc",
                "visibility_code": "public",
                "corporate_entity_id": "corp",
                "process_unit_id": "pu",
                "thread_group_key": "thread-only-mine",
                "created_at": datetime(2026, 1, 3),
            },
        ]
        edges: list[dict] = []  # reconstruct found no relation between x and y either

        async def fetch(self, query: str):
            return self.edges if "post_lineage_edge" in query else self.posts

    connection = FakeConnection()

    shared_group_result = asyncio.run(
        visible_lineage_graph(connection, lambda row: True, focus_post_id="post-x")
    )
    lonely_result = asyncio.run(
        visible_lineage_graph(connection, lambda row: True, focus_post_id="post-lonely")
    )
    invisible_result = asyncio.run(
        visible_lineage_graph(connection, lambda row: False, focus_post_id="post-x")
    )

    assert shared_group_result["isolation_reason"] == "no_relation_found"
    assert lonely_result["isolation_reason"] == "no_comparison_group"
    # A post outside the account's own visible set reveals no reason -- same
    # fail-closed discipline as its already-empty node/edge lists.
    assert invisible_result["isolation_reason"] is None


def test_lineage_coverage_summary_counts_edges_and_both_isolation_reasons() -> None:
    """ADR 0143's per-post distinction, aggregated corpus-wide for the
    operator who just ran a rebuild -- not just a bare edge count."""
    rows = [
        {"post_id": "post-a", "thread_group_key": "thread-shared",
         "process_unit_id": "pu", "corporate_entity_id": "corp"},
        {"post_id": "post-b", "thread_group_key": "thread-shared",
         "process_unit_id": "pu", "corporate_entity_id": "corp"},
        {"post_id": "post-unrelated", "thread_group_key": "thread-shared",
         "process_unit_id": "pu", "corporate_entity_id": "corp"},
        {"post_id": "post-lonely", "thread_group_key": "thread-only-mine",
         "process_unit_id": "pu", "corporate_entity_id": "corp"},
    ]
    edges = [Edge(parent_id="post-a", child_id="post-b", fused_score=0.9)]

    summary = lineage_coverage_summary(rows, edges)

    assert summary == {
        "total_posts": 4,
        "posts_with_edges": 2,
        "posts_no_relation_found": 1,  # post-unrelated: real groupmates, no edge
        "posts_no_comparison_group": 1,  # post-lonely: sole member of its group
    }


def test_lineage_coverage_summary_on_a_fully_disconnected_corpus() -> None:
    """No edges at all: every post is either a real-groupmate miss or a
    true singleton -- never silently dropped from the totals."""
    rows = [
        {"post_id": "post-1", "thread_group_key": "shared",
         "process_unit_id": "pu", "corporate_entity_id": "corp"},
        {"post_id": "post-2", "thread_group_key": "shared",
         "process_unit_id": "pu", "corporate_entity_id": "corp"},
        {"post_id": "post-3", "thread_group_key": "alone",
         "process_unit_id": "pu", "corporate_entity_id": "corp"},
    ]

    summary = lineage_coverage_summary(rows, edges=[])

    assert summary == {
        "total_posts": 3,
        "posts_with_edges": 0,
        "posts_no_relation_found": 2,
        "posts_no_comparison_group": 1,
    }
