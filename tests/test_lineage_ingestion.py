"""Unit tests for source_post → Record mapping used by lineage rebuild."""

from __future__ import annotations

import asyncio
import math
from datetime import UTC, datetime, timezone
from functools import lru_cache

import pytest

import backend.app.lineage_ingestion as ingestion
from backend.app.lineage_ingestion import (
    _budgeted_llm,
    interval_relations_for_post,
    lineage_graphs_for_posts,
    persist_lineage_edges,
    rebuild_lineage,
    rebuild_lineage_from_pool,
    reconstruct_group_key,
    records_from_source_posts,
    visible_lineage_graph,
)
from lineageweave.channel_weight_estimation import estimate_fixture_channel_weights
from lineageweave.fixtures import sample_records
from lineageweave.lineage_persistence import lineage_edge_specs, quantize_signal_value
from lineageweave.models import Edge, Record


@lru_cache(maxsize=1)
def _fixture_weights() -> dict[str, float]:
    """Return the fast-mlsirm estimate for the declared synthetic design."""
    estimate = estimate_fixture_channel_weights()
    assert estimate is not None
    return estimate.weights
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
                "channel_set_code": "channel_set_deterministic",
                "estimation_run_id": "00000000-0000-0000-0000-000000000001",
                "estimation_method_code": "mls2plm_discrimination",
                "estimator_version": "5006c382",
                "anchor_method_code": "unanchored_channel_covariance",
                "source_snapshot_sha256": "a" * 64,
                "sample_pair_count": 600,
                "knowledge_cutoff": datetime(2026, 1, 1, tzinfo=UTC),
            }
            return [
                {**provenance, "channel_code": channel, "weight_value": weight}
                for channel, weight in _fixture_weights().items()
            ]

    assert asyncio.run(
        ingestion.load_estimated_channel_weights(
            StoredWeightConnection(), {"temporal", "secondary_key", "text"}
        )
    ) is None


def test_tepp_criterion_anchor_activates_an_exact_complete_vector() -> None:
    """ADR 0205 activates only an exact persisted TEPP criterion anchor."""

    class StoredWeightConnection:
        async def fetchval(self, _query: str):
            return True

        async def fetch(self, _query: str):
            provenance = {
                "channel_set_code": "channel_set_deterministic",
                "estimation_run_id": "00000000-0000-0000-0000-000000000001",
                "estimation_method_code": "mls2plm_expected_information",
                "estimator_version": "1.0.0",
                "anchor_method_code": "tepp_lineage_criterion_v1",
                "source_snapshot_sha256": "a" * 64,
                "sample_pair_count": 600,
                "knowledge_cutoff": datetime(2026, 1, 1, tzinfo=UTC),
                "anchor_kind_code": "lineage_pair_criterion",
                "anchor_contract_version": 1,
                "anchor_snapshot_sha256": "a" * 64,
                "anchor_knowledge_cutoff": datetime(2026, 1, 1, tzinfo=UTC),
                "criterion_validity_status_code": "accepted",
                "validated_pair_count": 600,
                "tepp_result_sha256": "b" * 64,
                "tepp_run_kind_code": "analysis_run_tepp",
                "tepp_snapshot_sha256": "a" * 64,
                "tepp_knowledge_cutoff": datetime(2026, 1, 1, tzinfo=UTC),
            }
            return [
                {**provenance, "channel_code": channel, "weight_value": weight}
                for channel, weight in _fixture_weights().items()
            ]

    assert asyncio.run(
        ingestion.load_estimated_channel_weights(
            StoredWeightConnection(), {"temporal", "secondary_key", "text"}
        )
    ) == _fixture_weights()


def test_duplicate_exact_channel_sets_fail_closed() -> None:
    """Two equally matching TEPP sets are ambiguous and neither is activated."""

    class StoredWeightConnection:
        async def fetchval(self, _query: str):
            return True

        async def fetch(self, _query: str):
            cutoff = datetime(2026, 1, 1, tzinfo=UTC)
            base = {
                "estimation_method_code": "mls2plm_expected_information",
                "estimator_version": "1.0.0",
                "anchor_method_code": "tepp_lineage_criterion_v1",
                "source_snapshot_sha256": "a" * 64,
                "sample_pair_count": 600,
                "knowledge_cutoff": cutoff,
                "anchor_kind_code": "lineage_pair_criterion",
                "anchor_contract_version": 1,
                "anchor_snapshot_sha256": "a" * 64,
                "anchor_knowledge_cutoff": cutoff,
                "criterion_validity_status_code": "accepted",
                "validated_pair_count": 600,
                "tepp_result_sha256": "b" * 64,
                "tepp_run_kind_code": "analysis_run_tepp",
                "tepp_snapshot_sha256": "a" * 64,
                "tepp_knowledge_cutoff": cutoff,
            }
            return [
                {
                    **base,
                    "channel_set_code": set_code,
                    "estimation_run_id": run_id,
                    "channel_code": channel,
                    "weight_value": weight,
                }
                for set_code, run_id in (
                    ("channel_set_deterministic", "00000000-0000-0000-0000-000000000001"),
                    ("channel_set_duplicate", "00000000-0000-0000-0000-000000000002"),
                )
                for channel, weight in (("temporal", 0.5), ("secondary_key", 0.3), ("text", 0.2))
            ]

    assert asyncio.run(
        ingestion.load_estimated_channel_weights(
            StoredWeightConnection(), {"temporal", "secondary_key", "text"}
        )
    ) is None


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("criterion_validity_status_code", "rejected"),
        ("anchor_snapshot_sha256", "b" * 64),
        ("tepp_knowledge_cutoff", datetime(2026, 1, 2, tzinfo=UTC)),
        ("validated_pair_count", 599),
    ),
)
def test_tepp_anchor_mismatch_disables_the_whole_vector(field: str, value: object) -> None:
    """No TEPP identity or validity mismatch is repaired or inferred."""

    class StoredWeightConnection:
        async def fetchval(self, _query: str):
            return True

        async def fetch(self, _query: str):
            cutoff = datetime(2026, 1, 1, tzinfo=UTC)
            provenance = {
                "channel_set_code": "channel_set_deterministic",
                "estimation_run_id": "00000000-0000-0000-0000-000000000001",
                "estimation_method_code": "mls2plm_expected_information",
                "estimator_version": "1.0.0",
                "anchor_method_code": "tepp_lineage_criterion_v1",
                "source_snapshot_sha256": "a" * 64,
                "sample_pair_count": 600,
                "knowledge_cutoff": cutoff,
                "anchor_kind_code": "lineage_pair_criterion",
                "anchor_contract_version": 1,
                "anchor_snapshot_sha256": "a" * 64,
                "anchor_knowledge_cutoff": cutoff,
                "criterion_validity_status_code": "accepted",
                "validated_pair_count": 600,
                "tepp_result_sha256": "b" * 64,
                "tepp_run_kind_code": "analysis_run_tepp",
                "tepp_snapshot_sha256": "a" * 64,
                "tepp_knowledge_cutoff": cutoff,
                field: value,
            }
            return [
                {**provenance, "channel_code": channel, "weight_value": weight}
                for channel, weight in (("temporal", 0.5), ("secondary_key", 0.3), ("text", 0.2))
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
            return [
                {
                    "channel_set_code": "channel_set_deterministic",
                    "channel_code": "temporal",
                    "weight_value": 1.0,
                }
            ]

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
                "channel_set_code": "channel_set_deterministic",
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
                "channel_set_code": "channel_set_deterministic",
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


def test_weight_loader_picks_the_set_matching_the_active_channels(
    monkeypatch,
) -> None:
    """Migration 0200: one persisted set per active-channel combination.

    A 3-channel rebuild and a 4-channel (llm-inclusive) run each get
    exactly their own set; an active combination with no matching set
    returns ``None`` -- never a partial mix of estimation runs.
    """
    monkeypatch.setattr(ingestion, "_SUPPORTED_ANCHOR_METHOD_CODES", {"test_anchor"})

    class TwoSetConnection:
        async def fetchval(self, _query: str):
            return True

        async def fetch(self, _query: str):
            def rows(set_code, run_id, channel_weights):
                return [
                    {
                        "channel_set_code": set_code,
                        "channel_code": channel,
                        "weight_value": weight,
                        "estimation_run_id": run_id,
                        "estimation_method_code": "test_method",
                        "estimator_version": "1.0.0",
                        "anchor_method_code": "test_anchor",
                        "source_snapshot_sha256": "a" * 64,
                        "sample_pair_count": 600,
                        "knowledge_cutoff": datetime(2026, 1, 1, tzinfo=UTC),
                    }
                    for channel, weight in channel_weights
                ]

            return rows(
                "channel_set_deterministic",
                "00000000-0000-0000-0000-000000000001",
                (("temporal", 0.6), ("secondary_key", 0.3), ("text", 0.1)),
            ) + rows(
                "channel_set_with_llm",
                "00000000-0000-0000-0000-000000000002",
                (
                    ("temporal", 0.4),
                    ("secondary_key", 0.2),
                    ("text", 0.1),
                    ("llm", 0.3),
                ),
            )

    deterministic = asyncio.run(
        ingestion.load_estimated_channel_weights(
            TwoSetConnection(), {"temporal", "secondary_key", "text"}
        )
    )
    assert deterministic == {"temporal": 0.6, "secondary_key": 0.3, "text": 0.1}
    with_llm = asyncio.run(
        ingestion.load_estimated_channel_weights(
            TwoSetConnection(), {"temporal", "secondary_key", "text", "llm"}
        )
    )
    assert with_llm is not None and with_llm["llm"] == 0.3
    assert asyncio.run(
        ingestion.load_estimated_channel_weights(
            TwoSetConnection(), {"temporal", "text"}
        )
    ) is None


def test_weight_loader_reads_a_pre_0200_schema_as_one_deterministic_set(
    monkeypatch,
) -> None:
    """Before migration 0200 no channel_set_code column exists; the loader
    must probe the catalog (never a failing statement) and treat the rows
    as the single implicit deterministic set.
    """
    monkeypatch.setattr(ingestion, "_SUPPORTED_ANCHOR_METHOD_CODES", {"test_anchor"})

    class Pre0200Connection:
        def __init__(self) -> None:
            self.fetch_queries: list[str] = []

        async def fetchval(self, query: str):
            if "information_schema.columns" in query:
                return False
            return True

        async def fetch(self, query: str):
            self.fetch_queries.append(query)
            provenance = {
                "channel_set_code": "channel_set_deterministic",
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
                for channel, weight in (
                    ("temporal", 0.6),
                    ("secondary_key", 0.3),
                    ("text", 0.1),
                )
            ]

    connection = Pre0200Connection()
    loaded = asyncio.run(
        ingestion.load_estimated_channel_weights(
            connection, {"temporal", "secondary_key", "text"}
        )
    )
    assert loaded == {"temporal": 0.6, "secondary_key": 0.3, "text": 0.1}
    assert all(
        "select channel_set_code" not in query
        for query in connection.fetch_queries
    ), "a pre-0200 schema must never be queried for the missing column"


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
    events: list[str] = []

    class FakeTransaction:
        async def __aenter__(self):
            events.append("transaction_enter")

        async def __aexit__(self, *_args):
            events.append("transaction_exit")

    class FakeConnection:
        async def fetch(self, _query: str, *_args):
            events.append("fetch")
            return []

        async def fetchval(self, _query: str):
            return False

        def transaction(self):
            return FakeTransaction()

    client = object()
    captured: dict[str, object] = {}

    def fake_lineage_edge_specs(_records, *, llm=None, weights=None):
        captured["llm"] = llm
        captured["weights"] = weights
        return []

    async def fake_load_weights(_conn, _channels):
        return _fixture_weights()

    async def fake_persist_lineage_edges(_conn, _edges, _weights=None, _points=None):
        events.append("persist")
        return None

    async def fake_to_thread(function, *args, **kwargs):
        events.append("reconstruct")
        captured["offloaded_function"] = function
        return function(*args, **kwargs)

    monkeypatch.setattr(
        "backend.app.lineage_ingestion.lineage_edge_specs", fake_lineage_edge_specs
    )
    monkeypatch.setattr(
        "backend.app.lineage_ingestion.persist_lineage_edges", fake_persist_lineage_edges
    )
    monkeypatch.setattr(
        "backend.app.lineage_ingestion.load_estimated_channel_weights", fake_load_weights
    )
    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    asyncio.run(rebuild_lineage(FakeConnection(), llm=client))

    assert captured["llm"] is client
    assert captured["weights"] == _fixture_weights()
    assert captured["offloaded_function"] is fake_lineage_edge_specs
    assert events == ["fetch", "reconstruct", "transaction_enter", "persist", "transaction_exit"]


def test_estimated_weight_channels_include_only_an_available_llm() -> None:
    """Weight lookup must match the exact channel set reconstruction can use."""
    assert ingestion.estimated_weight_channels(None) == {
        "temporal",
        "secondary_key",
        "text",
    }
    assert ingestion.estimated_weight_channels(type("LLM", (), {"available": True})()) == {
        "temporal",
        "secondary_key",
        "text",
        "llm",
    }


def test_rebuild_drops_llm_before_candidate_pair_budget_is_exceeded(monkeypatch) -> None:
    """Keep a large live rebuild from issuing unbounded provider calls."""

    records = [
        Record(f"record-{index}", "shared-group", f"Record {index}", datetime(2026, 1, index + 1))
        for index in range(3)
    ]
    monkeypatch.setattr(
        "backend.app.lineage_ingestion.MAXIMUM_LIVE_LLM_PAIR_EVALUATIONS", 1
    )

    assert _budgeted_llm(records, object()) is None


def test_rebuild_drops_llm_before_estimated_weight_lookup(monkeypatch) -> None:
    """Never load a four-channel estimate for a three-channel reconstruction."""

    records = [
        Record(f"record-{index}", "shared-group", f"Record {index}", datetime(2026, 1, index + 1))
        for index in range(3)
    ]
    captured: dict[str, object] = {}

    class FakeTransaction:
        async def __aenter__(self):
            return None

        async def __aexit__(self, *_args):
            return None

    class FakeConnection:
        def transaction(self):
            return FakeTransaction()

    async def fake_load_records(_conn):
        return records

    async def fake_load_weights(_conn, channels):
        captured["channels"] = channels
        return _fixture_weights()

    async def fake_reconstruct(_records, llm, _weights):
        captured["llm"] = llm
        return []

    async def fake_persist(_conn, _edges, _weights, _points):
        return None

    monkeypatch.setattr(ingestion, "MAXIMUM_LIVE_LLM_PAIR_EVALUATIONS", 1)
    monkeypatch.setattr(ingestion, "_load_lineage_records", fake_load_records)
    monkeypatch.setattr(ingestion, "load_estimated_channel_weights", fake_load_weights)
    monkeypatch.setattr(ingestion, "_reconstruct_lineage_records", fake_reconstruct)
    monkeypatch.setattr(ingestion, "persist_lineage_edges", fake_persist)

    asyncio.run(rebuild_lineage(FakeConnection(), llm=type("LLM", (), {"available": True})()))

    assert captured == {
        "channels": {"temporal", "secondary_key", "text"},
        "llm": None,
    }


def test_pooled_rebuild_releases_the_connection_during_reconstruction(monkeypatch) -> None:
    """Keep provider work outside the pool and transaction, then replace atomically."""
    events: list[str] = []

    class FakeTransaction:
        async def __aenter__(self):
            events.append("transaction-enter")

        async def __aexit__(self, *_args):
            events.append("transaction-exit")

    class FakeConnection:
        async def fetch(self, _query: str, *_args):
            events.append("fetch")
            return []

        async def fetchval(self, _query: str):
            return False

        def transaction(self):
            return FakeTransaction()

    class FakeAcquire:
        def __init__(self, pool):
            self.pool = pool

        async def __aenter__(self):
            self.pool.active += 1
            events.append("acquire")
            return self.pool.connection

        async def __aexit__(self, *_args):
            self.pool.active -= 1
            events.append("release")

    class FakePool:
        def __init__(self):
            self.active = 0
            self.connection = FakeConnection()

        def acquire(self):
            return FakeAcquire(self)

    pool = FakePool()

    async def fake_to_thread(function, *args, **kwargs):
        assert pool.active == 0
        events.append("reconstruct")
        return function(*args, **kwargs)

    async def fake_persist(_conn, _edges, _weights=None, _points=None):
        assert pool.active == 1
        assert events[-1] == "transaction-enter"
        events.append("persist")

    async def fake_load_weights(_conn, _channels):
        return _fixture_weights()

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(
        "backend.app.lineage_ingestion.persist_lineage_edges", fake_persist
    )
    monkeypatch.setattr(
        "backend.app.lineage_ingestion.load_estimated_channel_weights", fake_load_weights
    )

    asyncio.run(rebuild_lineage_from_pool(pool))

    assert events == [
        "acquire",
        "fetch",
        "release",
        "reconstruct",
        "acquire",
        "transaction-enter",
        "persist",
        "transaction-exit",
        "release",
    ]


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
    edges = lineage_edge_specs(
        records_from_source_posts(rows),
        weights=_fixture_weights(),
    )
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
                    {},
                    points_by_post_id={"parent": {"created_at": datetime(2026, 1, 1)}},
            )
        )
    assert connection.calls == []


def test_rebuild_fails_closed_without_an_activated_weight_estimate() -> None:
    """ADR 0200 point 1: no activated estimate -> no reconstruction on
    constants. The raised message names the next action (run the
    estimation script) so the operator is never left guessing, and
    nothing is written.
    """
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

    class FakeTransaction:
        async def __aenter__(self):
            return None

        async def __aexit__(self, *_args):
            return None

    class FakeConnection:
        def __init__(self) -> None:
            self.executions: list[tuple[str, tuple[object, ...]]] = []

        async def fetch(self, query: str, *_args):
            assert "from source_post" in query
            return rows

        async def fetchval(self, query: str):
            assert "to_regclass('public.lineage_channel_weight')" in query
            return False

        async def executemany(self, query: str, args) -> None:
            for row in args:
                self.executions.append((query, row))

        def transaction(self):
            return FakeTransaction()

    connection = FakeConnection()
    with pytest.raises(ingestion.ChannelWeightsNotEstimated) as raised:
        asyncio.run(ingestion.rebuild_lineage(connection))
    assert "estimate_channel_weights" in str(raised.value)
    assert connection.executions == []


def test_rebuild_reconstructs_with_an_activated_estimate() -> None:
    """With an activated estimate the designed fork persists as before."""
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
    weight_rows = [
        {
            "channel_set_code": "channel_set_deterministic",
            "channel_code": channel,
            "weight_value": weight,
            "estimation_run_id": "00000000-0000-0000-0000-000000000001",
            "estimation_method_code": "mls2plm_expected_information",
            "estimator_version": "1.0.0",
            "anchor_method_code": "tepp_lineage_criterion_v1",
            "source_snapshot_sha256": "a" * 64,
            "sample_pair_count": 600,
            "knowledge_cutoff": datetime(2026, 1, 1, tzinfo=UTC),
            "anchor_kind_code": "lineage_pair_criterion",
            "anchor_contract_version": 1,
            "anchor_snapshot_sha256": "a" * 64,
            "anchor_knowledge_cutoff": datetime(2026, 1, 1, tzinfo=UTC),
            "criterion_validity_status_code": "accepted",
            "validated_pair_count": 600,
            "tepp_result_sha256": "b" * 64,
            "tepp_run_kind_code": "analysis_run_tepp",
            "tepp_snapshot_sha256": "a" * 64,
            "tepp_knowledge_cutoff": datetime(2026, 1, 1, tzinfo=UTC),
        }
        for channel, weight in _fixture_weights().items()
    ]

    class FakeTransaction:
        async def __aenter__(self):
            return None

        async def __aexit__(self, *_args):
            return None

    class FakeConnection:
        def __init__(self) -> None:
            self.executions: list[tuple[str, tuple[object, ...]]] = []

        async def fetch(self, query: str):
            if "lineage_channel_weight" in query:
                return weight_rows
            assert "from source_post" in query
            return rows

        async def fetchval(self, _query: str):
            return True

        async def execute(self, query: str, *args: object) -> None:
            self.executions.append((query, args))

        async def executemany(self, query: str, args) -> None:
            for row in args:
                self.executions.append((query, row))

        def transaction(self):
            return FakeTransaction()

    connection = FakeConnection()
    edges = asyncio.run(ingestion.rebuild_lineage(connection))

    pairs = {(edge.parent_id, edge.child_id) for edge in edges}
    assert {("rec-002", "rec-003"), ("rec-002", "rec-004")} <= pairs
    assert connection.executions[0] == ("delete from post_lineage_edge", ())
    inserted_edges = [
        row
        for query, row in connection.executions
        if query.startswith("insert into post_lineage_edge (")
    ]
    assert len(inserted_edges) == len(edges)


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
    assert isolated["isolation_reason"] == "no_comparison_group"
    assert focused["edges"][0]["channel_evidence"] == []


def test_landing_lineage_applies_abac_and_limit_in_database() -> None:
    class FakeConnection:
        statements: list[tuple[str, tuple]] = []

        async def fetch(self, query: str, *args):
            self.statements.append((query, args))
            if "from source_post" in query:
                return []
            return []

    connection = FakeConnection()
    graph = asyncio.run(
        visible_lineage_graph(
            connection,
            lambda row: True,
            limit=500,
            corporate_entity_ids=("corp-a",),
            process_unit_ids=("pu-a",),
        )
    )

    post_query, post_args = connection.statements[0]
    assert "corporate_entity_id::text = any($1::text[])" in post_query
    assert "process_unit_id::text = any($2::text[])" in post_query
    assert "order by created_at desc, post_id desc limit $3" in post_query
    assert post_args == (["corp-a"], ["pu-a"], 501)
    assert graph["nodes"] == []
    assert graph["truncated"] is False


def test_landing_lineage_does_not_optimize_with_incomplete_abac_scope() -> None:
    """A future caller cannot make corporate scope imply every process unit."""
    connection = _RecordingConnection()
    asyncio.run(
        visible_lineage_graph(
            connection,
            lambda row: True,
            corporate_entity_ids=("corp-a",),
        )
    )

    assert not any("any($1::text[])" in query for query, _ in connection.statements)


class _RecordingConnection:
    def __init__(self) -> None:
        self.statements: list[tuple[str, tuple]] = []
        self.batches: list[tuple[str, list[tuple]]] = []

    async def execute(self, query: str, *args):
        self.statements.append((query, args))

    async def executemany(self, query: str, args):
        rows = list(args)
        self.batches.append((query, rows))
        self.statements.extend((query, row) for row in rows)

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
                "signal_weight": _fixture_weights()["text"],
                "signal_contribution": _fixture_weights()["text"] * 0.5,
            },
            {
                "parent_post_id": "post-a",
                "child_post_id": "post-b",
                "signal_code": "lineage_signal_temporal",
                "signal_score": 0.8,
                "signal_weight": _fixture_weights()["temporal"],
                "signal_contribution": _fixture_weights()["temporal"] * 0.8,
            },
            {
                "parent_post_id": "post-a",
                "child_post_id": "post-b",
                "signal_code": "lineage_signal_secondary_key",
                "signal_score": 1.0,
                "signal_weight": _fixture_weights()["secondary_key"],
                "signal_contribution": _fixture_weights()["secondary_key"],
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
            {
                "signal_code": f"lineage_signal_{channel}",
                "signal_weight": weight,
            }
            for channel in ("temporal", "secondary_key", "text")
            for weight in (_fixture_weights()[channel],)
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
    assert {item["signal_code"] for item in evidence} == {"secondary_key", "text", "temporal"}
    assert [item["rank"] for item in evidence] == [1, 2, 3]
    assert "llm" not in {item["signal_code"] for item in evidence}
    assert graph["reconstruction"]["reconstruction_version"] == "lineageweave.reconstruct/2.14.0"
    assert graph["reconstruction"]["active_weights"][0]["signal_code"] == "temporal"
    signal_query = next(query for query in connection.queries if "post_lineage_edge_signal" in query)
    assert "parent_post_id = any($1::uuid[])" in signal_query
    assert "child_post_id = any($2::uuid[])" in signal_query
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
                "signal_weight": _fixture_weights()["text"],
                "signal_contribution": _fixture_weights()["text"] * 0.9,
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


def test_focused_graph_cannot_bridge_through_an_invisible_post() -> None:
    class FakeConnection:
        posts = tuple(
            {
                "post_id": post_id,
                "post_title": post_id,
                "voc_type_code": "voc",
                "visibility_code": visibility,
                "corporate_entity_id": "corp",
                "process_unit_id": "pu",
                "thread_group_key": "thread-a",
                "created_at": datetime(2026, 1, day, tzinfo=timezone.utc),
            }
            for day, post_id, visibility in (
                (1, "post-a", "public"),
                (2, "post-hidden", "restricted"),
                (3, "post-b", "public"),
            )
        )
        edges = (
            {"parent_post_id": "post-a", "child_post_id": "post-hidden", "fused_score": 0.8},
            {"parent_post_id": "post-hidden", "child_post_id": "post-b", "fused_score": 0.8},
        )

        async def fetch(self, query: str, *_args):
            if "post_lineage_edge_signal" in query:
                return []
            if "event_lineage_rebuild_channel" in query:
                return []
            if "event_lineage_rebuild" in query:
                return []
            return self.edges if "post_lineage_edge" in query else self.posts

    graph = asyncio.run(
        visible_lineage_graph(
            FakeConnection(),
            lambda row: row["visibility_code"] == "public",
            focus_post_id="post-a",
        )
    )

    assert graph["nodes"] == []
    assert graph["edges"] == []


def test_persist_lineage_edges_replaces_signals_atomically_without_llm() -> None:
    from lineageweave.lineage_persistence import lineage_rebuild_spec
    from lineageweave.models import Edge

    scores = {"temporal": 0.8, "secondary_key": 1.0, "text": 0.5}
    weights = _fixture_weights()
    fused = sum(weights[name] * scores[name] for name in scores)
    edge = Edge(
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        fused,
        scores,
    )
    connection = _RecordingConnection()
    points = {
        edge.parent_id: {"created_at": datetime(2026, 1, 1)},
        edge.child_id: {"created_at": datetime(2026, 1, 2)},
    }
    asyncio.run(persist_lineage_edges(connection, [edge], weights, points))
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
    assert [len(rows) for _query, rows in connection.batches] == [3, 1, 3]
    assert connection.batches[0][1] == [
        (f"lineage_signal_{channel}", quantize_signal_value(weights[channel]))
        for channel in ("temporal", "secondary_key", "text")
    ]
    spec = lineage_rebuild_spec([edge], weights=weights, package_version="2.14.0")
    assert spec.reconstruction_version == "lineageweave.reconstruct/2.14.0"


def test_duplicate_rebuild_replays_the_same_delete_insert_sequence() -> None:
    from lineageweave.models import Edge

    scores = {"temporal": 0.8, "secondary_key": 1.0, "text": 0.5}
    weights = _fixture_weights()
    fused = sum(weights[name] * scores[name] for name in scores)
    edge = Edge(
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        fused,
        scores,
    )
    first = _RecordingConnection()
    second = _RecordingConnection()
    points = {
        edge.parent_id: {"created_at": datetime(2026, 1, 1)},
        edge.child_id: {"created_at": datetime(2026, 1, 2)},
    }
    asyncio.run(persist_lineage_edges(first, [edge], weights, points))
    asyncio.run(persist_lineage_edges(second, [edge], weights, points))
    assert [sql for sql, _args in first.statements] == [sql for sql, _args in second.statements]
    assert [args for _sql, args in first.statements] == [args for _sql, args in second.statements]


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
            if "post_lineage_edge_signal" in query:
                return []
            if "event_lineage_rebuild" in query:
                return []
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

        async def fetch(self, query: str, *_args):
            if "post_lineage_edge_signal" in query:
                return []
            if "event_lineage_rebuild_channel" in query:
                return []
            if "event_lineage_rebuild" in query:
                return [
                    {
                        "reconstruction_version": "lineageweave.reconstruct/2.14.0",
                        "generated_at": datetime(2026, 1, 5),
                        "min_fused_score": 0.5,
                        "candidate_window": 6,
                    }
                ]
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
    assert merged["reconstruction"]["reconstruction_version"] == (
        "lineageweave.reconstruct/2.14.0"
    )


def test_lineage_graphs_for_posts_with_no_citations_is_empty() -> None:
    class FakeConnection:
        async def fetch(self, query: str, *_args):
            return []

    merged = asyncio.run(lineage_graphs_for_posts(FakeConnection(), lambda row: True, []))
    assert merged == {
        "nodes": [],
        "edges": [],
        "truncated": False,
        "reconstruction": None,
    }
def test_lineage_graphs_for_posts_fetches_posts_and_edges_once_for_n_citations() -> None:
    """N citations must not refetch source_post / post_lineage_edge per cite."""

    class FakeConnection:
        posts = [
            {
                "post_id": f"post-{index}",
                "post_title": f"P{index}",
                "voc_type_code": "voc",
                "visibility_code": "public",
                "corporate_entity_id": "corp",
                "process_unit_id": "pu",
                "thread_group_key": f"thread-{index}",
                "created_at": datetime(2026, 1, index),
            }
            for index in range(1, 5)
        ]
        edges = [
            {
                "parent_post_id": "post-1",
                "child_post_id": "post-2",
                "fused_score": 0.5,
            }
        ]
        queries: list[str] = []

        async def fetch(self, query: str, *_args):
            self.queries.append(query)
            if "post_lineage_edge_signal" in query:
                return []
            if "event_lineage_rebuild_channel" in query:
                return []
            if "event_lineage_rebuild" in query:
                return []
            return self.edges if "post_lineage_edge" in query else self.posts

    connection = FakeConnection()
    merged = asyncio.run(
        lineage_graphs_for_posts(
            connection,
            lambda row: True,
            ["post-1", "post-3", "post-4", "post-1"],
        )
    )

    post_queries = [query for query in connection.queries if "from source_post" in query]
    edge_queries = [query for query in connection.queries if "from post_lineage_edge" in query and "post_lineage_edge_signal" not in query]
    assert len(post_queries) == 1
    assert len(edge_queries) == 1
    assert {node["id"] for node in merged["nodes"]} == {
        "post-1",
        "post-2",
        "post-3",
        "post-4",
    }
    assert merged["truncated"] is False


def test_lineage_graphs_for_posts_names_truncation_and_keeps_cited_posts() -> None:
    posts = [
        {
            "post_id": f"post-{index}",
            "post_title": f"P{index}",
            "voc_type_code": "voc",
            "visibility_code": "public",
            "corporate_entity_id": "corp",
            "process_unit_id": "pu",
            "thread_group_key": "thread-chain",
            "created_at": datetime(2026, 1, index),
        }
        for index in range(1, 7)
    ]
    edges = [
        {
            "parent_post_id": f"post-{index}",
            "child_post_id": f"post-{index + 1}",
            "fused_score": 0.4,
        }
        for index in range(1, 6)
    ]

    class FakeConnection:
        async def fetch(self, query: str, *_args):
            if "post_lineage_edge_signal" in query:
                return []
            if "event_lineage_rebuild_channel" in query:
                return []
            if "event_lineage_rebuild" in query:
                return []
            return edges if "post_lineage_edge" in query else posts

    merged = asyncio.run(
        lineage_graphs_for_posts(
            FakeConnection(),
            lambda row: True,
            ["post-1", "post-6"],
            node_limit=3,
        )
    )

    node_ids = [node["id"] for node in merged["nodes"]]
    assert node_ids[:2] == ["post-1", "post-6"]
    assert len(node_ids) == 3
    assert merged["truncated"] is True
    assert all(
        edge["source"] in node_ids and edge["target"] in node_ids
        for edge in merged["edges"]
    )


def _post(
    post_id: str,
    title: str,
    thread_group_key: str,
    created_at: datetime,
) -> dict[str, object]:
    return {
        "post_id": post_id,
        "post_title": title,
        "voc_type_code": "voc",
        "visibility_code": "public",
        "corporate_entity_id": "corp",
        "process_unit_id": "pu",
        "thread_group_key": thread_group_key,
        "created_at": created_at,
    }


class FakeConnection:
    def __init__(self, posts: list[dict[str, object]], edges: list[dict[str, object]]) -> None:
        self.posts = posts
        self.edges = edges
        self.executions: list[tuple[object, ...]] = []

    async def fetch(self, query: str, *_args):
        if "post_lineage_edge_signal" in query:
            return []
        if "event_lineage_rebuild_channel" in query:
            return []
        if "event_lineage_rebuild" in query:
            return []
        return self.edges if "post_lineage_edge" in query else self.posts

    async def fetchval(self, query: str):
        assert "to_regclass('public.lineage_channel_weight')" in query
        return False

    async def execute(self, *args: object) -> None:
        self.executions.append(args)


def test_two_visible_group_members_report_comparison_candidates_available() -> None:
    connection = FakeConnection(
        [
            _post("post-a", "A", "thread-a", datetime(2026, 1, 1)),
            _post("post-b", "B", "thread-a", datetime(2026, 1, 2)),
        ],
        [],
    )
    focused = asyncio.run(
        visible_lineage_graph(connection, lambda row: True, focus_post_id="post-a")
    )
    assert focused == {
        "nodes": [],
        "edges": [],
        "truncated": False,
        "reconstruction": None,
        "isolation_reason": "comparison_candidates_available",
    }


def test_hidden_sibling_does_not_flip_isolation_to_candidates_available() -> None:
    """ABAC-hidden siblings must not leak through candidate availability."""
    connection = FakeConnection(
        [
            _post("post-c", "C", "thread-c", datetime(2026, 1, 3)),
            _post("post-d", "D", "thread-c", datetime(2026, 1, 4)),
        ],
        [],
    )
    isolated = asyncio.run(
        visible_lineage_graph(
            connection,
            lambda row: str(row["post_id"]) != "post-d",
            focus_post_id="post-c",
        )
    )
    assert isolated["isolation_reason"] == "no_comparison_group"
    assert isolated["nodes"] == []


def test_inaccessible_focus_does_not_report_an_isolation_reason() -> None:
    connection = FakeConnection(
        [_post("post-a", "A", "thread-a", datetime(2026, 1, 1))],
        [],
    )
    hidden = asyncio.run(
        visible_lineage_graph(
            connection,
            lambda row: False,
            focus_post_id="post-a",
        )
    )
    assert hidden == {
        "nodes": [],
        "edges": [],
        "truncated": False,
        "reconstruction": None,
        "isolation_reason": None,
    }


def test_landing_graph_never_reports_an_isolation_reason() -> None:
    connection = FakeConnection(
        [_post("post-c", "C", "thread-c", datetime(2026, 1, 3))],
        [],
    )
    landing = asyncio.run(visible_lineage_graph(connection, lambda row: True))
    assert landing["isolation_reason"] is None
    assert [node["id"] for node in landing["nodes"]] == ["post-c"]
