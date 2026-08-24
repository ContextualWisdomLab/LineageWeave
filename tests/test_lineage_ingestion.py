"""Unit tests for source_post → Record mapping used by lineage rebuild."""

from __future__ import annotations

import asyncio
import math
from datetime import UTC, datetime, timezone

import backend.app.lineage_ingestion as ingestion
from backend.app.lineage_ingestion import lineage_graphs_for_posts
from lineageweave.fixtures import sample_records
from lineageweave.lineage_persistence import lineage_edge_specs


def test_missing_weight_table_is_detected_without_an_aborting_query() -> None:
    class MissingTableConnection:
        async def fetchval(self, query: str):
            assert "to_regclass('public.lineage_channel_weight')" in query
            return False

        async def fetch(self, _query: str):
            raise AssertionError(
                "missing tables must not be queried inside the outer transaction"
            )

    assert asyncio.run(
        ingestion.load_estimated_channel_weights(
            MissingTableConnection(), {"temporal", "secondary_key", "text"}
        )
    ) is None


def test_unapproved_weight_provenance_is_never_activated() -> None:
    class StoredWeightConnection:
        async def fetchval(self, _query: str):
            return True

        async def fetch(self, _query: str):
            provenance = {
                "estimation_run_id": "00000000-0000-0000-0000-000000000001",
                "estimation_method_code": "mls2plm_discrimination",
                "estimator_version": "5006c382",
                "anchor_method_code": "unanchored_channel_covariance",
                "source_snapshot_sha256": "a" * 64,
                "sample_pair_count": 600,
                "knowledge_cutoff": datetime(2026, 1, 1, tzinfo=UTC),
            }
            return [
                {**provenance, "channel_code": "temporal", "weight_value": 0.2},
                {**provenance, "channel_code": "secondary_key", "weight_value": 0.3},
                {**provenance, "channel_code": "text", "weight_value": 0.5},
            ]

    assert asyncio.run(
        ingestion.load_estimated_channel_weights(
            StoredWeightConnection(), {"temporal", "secondary_key", "text"}
        )
    ) is None


def test_incomplete_persisted_weight_vector_is_unavailable() -> None:
    """A partial vector must not silently reweight only some channels."""

    class IncompleteWeightConnection:
        async def fetchval(self, _query: str):
            return True

        async def fetch(self, _query: str):
            return [{"channel_code": "temporal", "weight_value": 1.0}]

    assert asyncio.run(
        ingestion.load_estimated_channel_weights(
            IncompleteWeightConnection(), {"temporal", "secondary_key", "text"}
        )
    ) is None


def test_mixed_weight_provenance_is_never_activated(monkeypatch) -> None:
    """A numerically complete vector cannot combine two estimation runs."""
    monkeypatch.setattr(ingestion, "_SUPPORTED_ANCHOR_METHOD_CODES", {"test_anchor"})

    class MixedProvenanceConnection:
        async def fetchval(self, _query: str):
            return True

        async def fetch(self, _query: str):
            base = {
                "estimation_method_code": "test_method",
                "estimator_version": "1.0.0",
                "anchor_method_code": "test_anchor",
                "source_snapshot_sha256": "a" * 64,
                "sample_pair_count": 600,
                "knowledge_cutoff": datetime(2026, 1, 1, tzinfo=UTC),
            }
            return [
                {
                    **base,
                    "estimation_run_id": f"00000000-0000-0000-0000-00000000000{index}",
                    "channel_code": channel,
                    "weight_value": weight,
                }
                for index, (channel, weight) in enumerate(
                    (("temporal", 0.2), ("secondary_key", 0.3), ("text", 0.5)),
                    start=1,
                )
            ]

    assert asyncio.run(
        ingestion.load_estimated_channel_weights(
            MixedProvenanceConnection(), {"temporal", "secondary_key", "text"}
        )
    ) is None


def test_supported_vectors_still_require_numeric_and_provenance_integrity(
    monkeypatch,
) -> None:
    monkeypatch.setattr(ingestion, "_SUPPORTED_ANCHOR_METHOD_CODES", {"test_anchor"})

    class StoredWeightConnection:
        def __init__(self, weights: tuple[float, float, float]) -> None:
            self.weights = weights

        async def fetchval(self, _query: str):
            return True

        async def fetch(self, _query: str):
            provenance = {
                "estimation_run_id": "00000000-0000-0000-0000-000000000001",
                "estimation_method_code": "test_method",
                "estimator_version": "1.0.0",
                "anchor_method_code": "test_anchor",
                "source_snapshot_sha256": "a" * 64,
                "sample_pair_count": 600,
                "knowledge_cutoff": datetime(2026, 1, 1, tzinfo=UTC),
            }
            return [
                {**provenance, "channel_code": channel, "weight_value": weight}
                for channel, weight in zip(
                    ("temporal", "secondary_key", "text"), self.weights
                )
            ]

    active = {"temporal", "secondary_key", "text"}
    assert asyncio.run(
        ingestion.load_estimated_channel_weights(
            StoredWeightConnection((0.2, 0.3, 0.5)), active
        )
    ) == {"temporal": 0.2, "secondary_key": 0.3, "text": 0.5}
    for invalid in ((0.2, 0.3, 0.6), (0.2, 0.8, math.nan), (0.2, 0.8, 0.0)):
        assert (
            asyncio.run(
                ingestion.load_estimated_channel_weights(
                    StoredWeightConnection(invalid), active
                )
            )
            is None
        )


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
    records = ingestion.records_from_source_posts(rows)
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
    records = ingestion.records_from_source_posts(rows)
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
    assert ingestion.reconstruct_group_key(a100) == "A-100"
    assert ingestion.reconstruct_group_key(ungrouped) == "shared-pu"


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
    edges = lineage_edge_specs(ingestion.records_from_source_posts(rows))
    pairs = {(edge.parent_id, edge.child_id) for edge in edges}
    assert ("rec-002", "rec-003") in pairs
    assert ("rec-002", "rec-004") in pairs
    assert "rec-006" not in {edge.child_id for edge in edges}


def test_rebuild_persists_the_synthetic_fork_without_estimated_weights() -> None:
    """A missing weight table keeps deterministic reconstruction operational."""
    rows = [
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
        for rec in sample_records()
    ]

    class FakeConnection:
        def __init__(self) -> None:
            self.executions: list[tuple[str, tuple[object, ...]]] = []

        async def fetch(self, query: str):
            assert "from source_post" in query
            return rows

        async def fetchval(self, query: str):
            assert "to_regclass('public.lineage_channel_weight')" in query
            return False

        async def execute(self, query: str, *args: object) -> None:
            self.executions.append((query, args))

    connection = FakeConnection()
    edges = asyncio.run(ingestion.rebuild_lineage(connection))

    pairs = {(edge.parent_id, edge.child_id) for edge in edges}
    assert {("rec-002", "rec-003"), ("rec-002", "rec-004")} <= pairs
    assert connection.executions[0] == ("delete from post_lineage_edge", ())
    assert len(connection.executions) == len(edges) + 1


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
    landing = asyncio.run(
        ingestion.visible_lineage_graph(connection, lambda row: True, limit=1)
    )
    focused = asyncio.run(
        ingestion.visible_lineage_graph(
            connection, lambda row: True, limit=1, focus_post_id="post-a"
        )
    )
    isolated = asyncio.run(
        ingestion.visible_lineage_graph(
            connection, lambda row: True, limit=1, focus_post_id="post-c"
        )
    )

    assert [node["id"] for node in landing["nodes"]] == ["post-c"]
    assert {node["id"] for node in focused["nodes"]} == {"post-a", "post-b"}
    assert len(focused["edges"]) == 1
    assert focused["truncated"] is False
    assert isolated == {"nodes": [], "edges": [], "truncated": False}


def test_lineage_graphs_for_posts_merges_distinct_threads_without_duplicates() -> None:
    """Global Ask can cite posts from unrelated threads; the merged graph
    must carry every cited thread (for LineageDag's per-thread git-branch
    rendering) without duplicating a node/edge shared by two focus posts.
    """

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
            {
                "post_id": "post-d",
                "post_title": "D",
                "voc_type_code": "voc",
                "visibility_code": "public",
                "corporate_entity_id": "corp",
                "process_unit_id": "pu",
                "thread_group_key": "thread-c",
                "created_at": datetime(2026, 1, 4),
            },
            {
                "post_id": "post-isolated",
                "post_title": "Isolated",
                "voc_type_code": "voc",
                "visibility_code": "public",
                "corporate_entity_id": "corp",
                "process_unit_id": "pu",
                "thread_group_key": "thread-isolated",
                "created_at": datetime(2026, 1, 5),
            },
        ]
        edges = [
            {"parent_post_id": "post-a", "child_post_id": "post-b", "fused_score": 0.8},
            {"parent_post_id": "post-c", "child_post_id": "post-d", "fused_score": 0.6},
        ]

        async def fetch(self, query: str):
            return self.edges if "post_lineage_edge" in query else self.posts

    connection = FakeConnection()
    merged = asyncio.run(
        lineage_graphs_for_posts(
            connection,
            lambda row: True,
            # "post-b" is cited alongside its own thread's root -- must not
            # duplicate post-a/post-b/their edge in the merged output.
            ["post-a", "post-b", "post-d", "post-isolated"],
        )
    )

    assert {node["id"] for node in merged["nodes"]} == {
        "post-a",
        "post-b",
        "post-c",
        "post-d",
        "post-isolated",
    }
    assert {node["group"] for node in merged["nodes"]} == {
        "thread-a",
        "thread-c",
        "thread-isolated",
    }
    assert len(merged["edges"]) == 2
    assert merged["truncated"] is False


def test_lineage_graphs_for_posts_with_no_citations_is_empty() -> None:
    class FakeConnection:
        async def fetch(self, query: str):
            return []

    merged = asyncio.run(lineage_graphs_for_posts(FakeConnection(), lambda row: True, []))
    assert merged == {"nodes": [], "edges": [], "truncated": False}
