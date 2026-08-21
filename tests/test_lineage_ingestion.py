"""Unit tests for source_post → Record mapping used by lineage rebuild."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from backend.app.lineage_ingestion import (
    rebuild_lineage,
    persist_lineage_edges,
    reconstruct_group_key,
    records_from_source_posts,
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


def test_rebuild_passes_the_configured_adjudication_client(monkeypatch) -> None:
    class FakeConnection:
        async def fetch(self, _query: str, *_args):
            return []

    client = object()
    captured: dict[str, object] = {}

    def fake_lineage_edge_specs(_records, *, llm=None):
        captured["llm"] = llm
        return []

    async def fake_persist_lineage_edges(_conn, _edges):
        return None

    import backend.app.lineage_ingestion as ingestion

    monkeypatch.setattr(ingestion, "lineage_edge_specs", fake_lineage_edge_specs)
    monkeypatch.setattr(ingestion, "persist_lineage_edges", fake_persist_lineage_edges)
    asyncio.run(rebuild_lineage(FakeConnection(), llm=client))

    assert captured["llm"] is client


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

        async def fetch(self, query: str, *_args):
            if "post_lineage_edge_signal" in query:
                return getattr(self, "signals", [])
            if "event_lineage_rebuild_channel" in query:
                return getattr(self, "rebuild_channels", [])
            if "event_lineage_rebuild" in query:
                return getattr(self, "rebuilds", [])
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
    assert isolated["nodes"] == []
    assert isolated["edges"] == []
    assert isolated["truncated"] is False
    assert isolated["reconstruction"] is None
    assert focused["edges"][0]["channel_evidence"] == []


class _RecordingConnection:
    def __init__(self) -> None:
        self.statements: list[tuple[str, tuple]] = []

    async def execute(self, query: str, *args):
        self.statements.append((query, args))

    async def fetch(self, query: str, *_args):
        return []


def test_visible_graph_attaches_ranked_channel_evidence() -> None:
    class FakeConnection:
        def __init__(self) -> None:
            self.queries: list[str] = []

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
        ]
        edges = [{"parent_post_id": "post-a", "child_post_id": "post-b", "fused_score": 0.7}]
        signals = [
            {
                "parent_post_id": "post-a",
                "child_post_id": "post-b",
                "signal_code": "lineage_signal_text",
                "signal_score": 0.5,
                "signal_weight": 0.5,
                "signal_contribution": 0.25,
            },
            {
                "parent_post_id": "post-a",
                "child_post_id": "post-b",
                "signal_code": "lineage_signal_temporal",
                "signal_score": 0.8,
                "signal_weight": 0.25,
                "signal_contribution": 0.2,
            },
            {
                "parent_post_id": "post-a",
                "child_post_id": "post-b",
                "signal_code": "lineage_signal_secondary_key",
                "signal_score": 1.0,
                "signal_weight": 0.25,
                "signal_contribution": 0.25,
            },
        ]
        rebuilds = [
            {
                "reconstruction_version": "lineageweave.reconstruct/2.14.0",
                "generated_at": datetime(2026, 8, 21, 12, 0, 0),
                "min_fused_score": 0.3,
                "candidate_window": 50,
            }
        ]
        rebuild_channels = [
            {"signal_code": "lineage_signal_temporal", "signal_weight": 0.25},
            {"signal_code": "lineage_signal_text", "signal_weight": 0.5},
        ]

        async def fetch(self, query: str, *_args):
            self.queries.append(query)
            if "post_lineage_edge_signal" in query:
                return self.signals
            if "event_lineage_rebuild_channel" in query:
                return self.rebuild_channels
            if "event_lineage_rebuild" in query:
                return self.rebuilds
            return self.edges if "post_lineage_edge" in query else self.posts

    connection = FakeConnection()
    graph = asyncio.run(visible_lineage_graph(connection, lambda row: True))
    evidence = graph["edges"][0]["channel_evidence"]
    assert [item["signal_code"] for item in evidence] == ["secondary_key", "text", "temporal"]
    assert [item["rank"] for item in evidence] == [1, 2, 3]
    assert "llm" not in {item["signal_code"] for item in evidence}
    assert graph["reconstruction"]["reconstruction_version"] == "lineageweave.reconstruct/2.14.0"
    assert graph["reconstruction"]["active_weights"][0]["signal_code"] == "temporal"
    weight_query = next(query for query in connection.queries if "event_lineage_rebuild_channel" in query)
    assert "join common_lookup_value as lookup" in weight_query
    assert "order by lookup.display_order, channel.signal_code" in weight_query


def test_abac_never_reveals_channel_evidence_for_an_invisible_endpoint() -> None:
    class FakeConnection:
        posts = [
            {
                "post_id": "post-public",
                "post_title": "Public",
                "voc_type_code": "voc",
                "visibility_code": "public",
                "corporate_entity_id": "corp",
                "process_unit_id": "pu",
                "thread_group_key": "thread-a",
                "created_at": datetime(2026, 1, 1),
            },
            {
                "post_id": "post-secret",
                "post_title": "Secret",
                "voc_type_code": "voc",
                "visibility_code": "restricted",
                "corporate_entity_id": "corp",
                "process_unit_id": "pu",
                "thread_group_key": "thread-a",
                "created_at": datetime(2026, 1, 2),
            },
        ]
        edges = [
            {"parent_post_id": "post-public", "child_post_id": "post-secret", "fused_score": 0.8}
        ]
        signals = [
            {
                "parent_post_id": "post-public",
                "child_post_id": "post-secret",
                "signal_code": "lineage_signal_text",
                "signal_score": 0.9,
                "signal_weight": 0.5,
                "signal_contribution": 0.45,
            }
        ]
        rebuilds = []
        rebuild_channels = []

        async def fetch(self, query: str, *_args):
            if "post_lineage_edge_signal" in query:
                return self.signals
            if "event_lineage_rebuild_channel" in query:
                return self.rebuild_channels
            if "event_lineage_rebuild" in query:
                return self.rebuilds
            return self.edges if "post_lineage_edge" in query else self.posts

    graph = asyncio.run(
        visible_lineage_graph(FakeConnection(), lambda row: row["post_id"] == "post-public")
    )
    assert [node["id"] for node in graph["nodes"]] == ["post-public"]
    assert graph["edges"] == []
    serialized = str(graph)
    assert "post-secret" not in serialized
    assert "0.45" not in serialized
    assert "lineage_signal_text" not in serialized


def test_persist_lineage_edges_replaces_signals_atomically_without_llm() -> None:
    from lineageweave.lineage_persistence import lineage_rebuild_spec
    from lineageweave.models import Edge

    scores = {"temporal": 0.8, "secondary_key": 1.0, "text": 0.5}
    weights = {"temporal": 0.25, "secondary_key": 0.25, "text": 0.5}
    fused = sum(weights[name] * scores[name] for name in scores)
    edge = Edge(
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        fused,
        scores,
    )
    connection = _RecordingConnection()
    asyncio.run(persist_lineage_edges(connection, [edge]))
    statements = [sql.casefold() for sql, _args in connection.statements]
    assert statements[0].startswith("delete from post_lineage_edge")
    assert any("delete from event_lineage_rebuild" in sql for sql in statements)
    assert any("insert into post_lineage_edge_signal" in sql for sql in statements)
    inserted_codes = [
        args[2]
        for sql, args in connection.statements
        if "insert into post_lineage_edge_signal" in sql.casefold()
    ]
    assert inserted_codes == [
        "lineage_signal_temporal",
        "lineage_signal_secondary_key",
        "lineage_signal_text",
    ]
    spec = lineage_rebuild_spec([edge], package_version="2.14.0")
    assert spec.reconstruction_version == "lineageweave.reconstruct/2.14.0"


def test_duplicate_rebuild_replays_the_same_delete_insert_sequence() -> None:
    from lineageweave.models import Edge

    scores = {"temporal": 0.8, "secondary_key": 1.0, "text": 0.5}
    weights = {"temporal": 0.25, "secondary_key": 0.25, "text": 0.5}
    fused = sum(weights[name] * scores[name] for name in scores)
    edge = Edge(
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        fused,
        scores,
    )
    first = _RecordingConnection()
    second = _RecordingConnection()
    asyncio.run(persist_lineage_edges(first, [edge]))
    asyncio.run(persist_lineage_edges(second, [edge]))
    assert [sql for sql, _args in first.statements] == [sql for sql, _args in second.statements]
    assert [args for _sql, args in first.statements] == [args for _sql, args in second.statements]
