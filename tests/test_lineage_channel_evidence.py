"""Regression tests for explainable Event Lineage edge evidence."""

from __future__ import annotations

import asyncio
import math
from datetime import datetime, timezone
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


def _writes(
    connection: _PersistConnection,
    table_name: str,
) -> list[tuple[Any, ...]]:
    return [
        arguments
        for query, arguments in connection.calls
        if f"insert into {table_name} (" in " ".join(query.split())
    ]


def test_persist_lineage_edges_writes_versioned_weights_and_contributions() -> None:
    connection = _PersistConnection()
    weights = {
        "temporal": 0.15,
        "secondary_key": 0.15,
        "text": 0.30,
        "llm": 0.40,
    }
    edge = Edge(
        parent_id="11111111-1111-1111-1111-111111111111",
        child_id="22222222-2222-2222-2222-222222222222",
        fused_score=0.67,
        channel_scores={
            "temporal": 0.8,
            "secondary_key": 1.0,
            "text": 0.4,
            "llm": 0.7,
        },
    )

    asyncio.run(
        persist_lineage_edges(
            connection,
            [edge],
            channel_weights=weights,
            reconstruction_version="weighted-convex-test-v1",
        )
    )

    run_writes = _writes(connection, "lineage_reconstruction_run")
    assert len(run_writes) == 1
    run_id, version, generated_at = run_writes[0]
    assert version == "weighted-convex-test-v1"
    assert generated_at.tzinfo is not None

    assert _writes(connection, "lineage_reconstruction_run_channel") == [
        (run_id, "lineage_channel_temporal", 0.15),
        (run_id, "lineage_channel_secondary_key", 0.15),
        (run_id, "lineage_channel_text", 0.30),
        (run_id, "lineage_channel_llm", 0.40),
    ]
    assert _writes(connection, "post_lineage_edge") == [
        (edge.parent_id, edge.child_id, 0.67, run_id)
    ]

    signal_writes = _writes(connection, "lineage_edge_channel_score")
    assert signal_writes == [
        (
            edge.parent_id,
            edge.child_id,
            "lineage_channel_temporal",
            0.8,
            pytest.approx(0.12),
        ),
        (
            edge.parent_id,
            edge.child_id,
            "lineage_channel_secondary_key",
            1.0,
            pytest.approx(0.15),
        ),
        (
            edge.parent_id,
            edge.child_id,
            "lineage_channel_text",
            0.4,
            pytest.approx(0.12),
        ),
        (
            edge.parent_id,
            edge.child_id,
            "lineage_channel_llm",
            0.7,
            pytest.approx(0.28),
        ),
    ]
    assert math.isclose(
        sum(arguments[4] for arguments in signal_writes),
        edge.fused_score,
        abs_tol=1e-12,
    )


def test_no_llm_reconstruction_persists_exactly_three_active_channels() -> None:
    connection = _PersistConnection()
    weights = {"temporal": 0.25, "secondary_key": 0.25, "text": 0.50}
    edge = Edge(
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
        0.65,
        {"temporal": 0.8, "secondary_key": 1.0, "text": 0.4},
    )

    asyncio.run(
        persist_lineage_edges(
            connection,
            [edge],
            channel_weights=weights,
            reconstruction_version="weighted-convex-test-v1",
        )
    )

    profile_codes = {
        arguments[1]
        for arguments in _writes(connection, "lineage_reconstruction_run_channel")
    }
    signal_codes = {
        arguments[2]
        for arguments in _writes(connection, "lineage_edge_channel_score")
    }
    assert profile_codes == {
        "lineage_channel_temporal",
        "lineage_channel_secondary_key",
        "lineage_channel_text",
    }
    assert signal_codes == profile_codes
    assert "lineage_channel_llm" not in signal_codes


@pytest.mark.parametrize(
    ("edge", "weights", "message"),
    [
        (Edge("parent", "child", 0.5, {"mystery": 0.5}), {"mystery": 1.0}, "unsupported lineage channel"),
        (Edge("parent", "child", 0.5, {"text": 1.01}), {"text": 1.0}, "between 0 and 1"),
        (Edge("parent", "child", 0.5, {"text": 0.5}), {"text": 0.9}, "sum to 1"),
        (
            Edge("parent", "child", 0.5, {"temporal": 0.5}),
            {"temporal": 0.5, "text": 0.5},
            "active channel set",
        ),
        (Edge("parent", "child", 0.9, {"text": 0.5}), {"text": 1.0}, "reconcile"),
    ],
)
def test_persist_lineage_edges_fails_closed_before_replacing_graph(
    edge: Edge,
    weights: dict[str, float],
    message: str,
) -> None:
    connection = _PersistConnection()

    with pytest.raises(ValueError, match=message):
        asyncio.run(
            persist_lineage_edges(
                connection,
                [edge],
                channel_weights=weights,
                reconstruction_version="test-v1",
            )
        )

    assert connection.calls == []


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
            generated_at = datetime(2026, 8, 20, 4, 0, tzinfo=timezone.utc)
            return [
                {
                    "parent_post_id": "post-a",
                    "child_post_id": "post-b",
                    "channel_code": "lineage_channel_temporal",
                    "channel_label": "Time proximity",
                    "channel_score": 0.9,
                    "channel_weight": 0.25,
                    "channel_contribution": 0.225,
                    "display_order": 0,
                    "reconstruction_version": "weighted-convex-v1",
                    "generated_at": generated_at,
                },
                {
                    "parent_post_id": "post-a",
                    "child_post_id": "post-b",
                    "channel_code": "lineage_channel_secondary_key",
                    "channel_label": "Secondary key",
                    "channel_score": 1.0,
                    "channel_weight": 0.25,
                    "channel_contribution": 0.25,
                    "display_order": 1,
                    "reconstruction_version": "weighted-convex-v1",
                    "generated_at": generated_at,
                },
                {
                    "parent_post_id": "post-a",
                    "child_post_id": "post-b",
                    "channel_code": "lineage_channel_text",
                    "channel_label": "Text similarity",
                    "channel_score": 0.42,
                    "channel_weight": 0.50,
                    "channel_contribution": 0.21,
                    "display_order": 2,
                    "reconstruction_version": "weighted-convex-v1",
                    "generated_at": generated_at,
                },
            ]
        if "from post_lineage_edge" in query:
            return [
                {
                    "parent_post_id": "post-a",
                    "child_post_id": "post-b",
                    "fused_score": 0.685,
                    "lineage_reconstruction_run_id": "run-1",
                }
            ]
        raise AssertionError(f"unexpected query: {query}")


def test_visible_lineage_graph_exposes_ranked_audit_evidence_without_inventing_llm() -> None:
    connection = _ReadConnection()
    graph = asyncio.run(visible_lineage_graph(connection, lambda row: True))

    edge = graph["edges"][0]
    assert edge["source"] == "post-a"
    assert edge["target"] == "post-b"
    assert edge["fused_score"] == 0.685
    assert edge["channel_scores"] == {
        "temporal": 0.9,
        "secondary_key": 1.0,
        "text": 0.42,
    }
    assert edge["channel_evidence"] == [
        {
            "signal_code": "secondary_key",
            "signal_label": "Secondary key",
            "score": 1.0,
            "weight": 0.25,
            "contribution": 0.25,
            "rank": 1,
        },
        {
            "signal_code": "temporal",
            "signal_label": "Time proximity",
            "score": 0.9,
            "weight": 0.25,
            "contribution": 0.225,
            "rank": 2,
        },
        {
            "signal_code": "text",
            "signal_label": "Text similarity",
            "score": 0.42,
            "weight": 0.5,
            "contribution": 0.21,
            "rank": 3,
        },
    ]
    assert edge["reconstruction_version"] == "weighted-convex-v1"
    assert edge["reconstructed_at"] == "2026-08-20T04:00:00+00:00"
    assert "llm" not in edge["channel_scores"]
    assert all(item["signal_code"] != "llm" for item in edge["channel_evidence"])
    assert connection.channel_arguments == (["post-a", "post-b"],)


def test_channel_score_migration_is_normalized_bounded_versioned_and_reversible() -> None:
    migration = Path("migrations/0055_lineage_edge_channel_score.sql").read_text(
        encoding="utf-8"
    )
    rollback = Path(
        "migrations/rollback/0055_lineage_edge_channel_score.sql"
    ).read_text(encoding="utf-8")
    docker_migrate = Path("docker/postgres-init/migrate.sh").read_text(
        encoding="utf-8"
    )

    assert "create table if not exists lineage_reconstruction_run" in migration
    assert "create table if not exists lineage_reconstruction_run_channel" in migration
    assert "lineage_reconstruction_run_id" in migration
    assert "reconstruction_version" in migration
    assert "generated_at" in migration
    assert "channel_weight" in migration
    assert "create table if not exists lineage_edge_channel_score" in migration
    assert "channel_contribution" in migration
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
    assert "channel_weight > 0" in migration
    assert "channel_weight <= 1" in migration
    assert "channel_contribution >= 0" in migration
    assert "channel_contribution <= 1" in migration
    assert "drop table if exists lineage_edge_channel_score" in rollback
    assert "drop table if exists lineage_reconstruction_run_channel" in rollback
    assert "drop table if exists lineage_reconstruction_run" in rollback
    assert "0055_*" in docker_migrate
    assert "0056_*" in docker_migrate
