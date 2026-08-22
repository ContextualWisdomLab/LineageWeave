"""Unit tests for source_post → Record mapping used by lineage rebuild."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from backend.app.lineage_ingestion import (
    reconstruct_group_key,
    records_from_source_posts,
    rebuild_lineage,
    visible_lineage_graph,
)
from lineageweave.fixtures import sample_records
from lineageweave.lineage_persistence import lineage_edge_specs


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


def test_rebuild_lineage_passes_the_adjudication_client_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """Live bug (2026-08-22): rebuild_lineage() called lineage_edge_specs()
    without llm=, so the corpus-wide rebuild (POST /api/lineage/rebuild and
    scripts/import_postgresql_posts.py) silently ran reconstruct() on the
    weaker 3-channel fallback -- the highest-weighted channel
    (DEFAULT_CHANNEL_WEIGHTS, ADR 0064) never actually reasoned about any
    real corpus. Assert the caller-supplied client reaches
    lineage_edge_specs unchanged, without depending on reconstruct()'s own
    decision about when to actually invoke it.
    """
    captured: dict[str, object] = {}

    def fake_lineage_edge_specs(records, *, llm=None):
        captured["llm"] = llm
        return []

    monkeypatch.setattr(
        "backend.app.lineage_ingestion.lineage_edge_specs", fake_lineage_edge_specs
    )

    class FakeConnection:
        async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
            return []

        async def execute(self, query: str, *args: object) -> str:
            return "OK"

    sentinel_client = object()
    asyncio.run(rebuild_lineage(FakeConnection(), adjudication_client=sentinel_client))
    assert captured["llm"] is sentinel_client


def test_rebuild_lineage_defaults_to_no_adjudication_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """The default stays None (lineage_edge_specs/reconstruct's own
    documented fallback) -- this only guards that rebuild_lineage's new
    keyword argument doesn't silently require a client everywhere.
    """
    captured: dict[str, object] = {"llm": "unset"}

    def fake_lineage_edge_specs(records, *, llm=None):
        captured["llm"] = llm
        return []

    monkeypatch.setattr(
        "backend.app.lineage_ingestion.lineage_edge_specs", fake_lineage_edge_specs
    )

    class FakeConnection:
        async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
            return []

        async def execute(self, query: str, *args: object) -> str:
            return "OK"

    asyncio.run(rebuild_lineage(FakeConnection()))
    assert captured["llm"] is None
