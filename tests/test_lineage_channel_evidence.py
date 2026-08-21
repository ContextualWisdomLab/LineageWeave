"""Event Lineage channel evidence must round-trip without fabricating LLM scores."""

from __future__ import annotations

from pathlib import Path

import pytest

from lineageweave.fixtures import sample_records
from lineageweave.lineage_persistence import (
    CHANNEL_EVIDENCE_TOLERANCE,
    LINEAGE_SIGNAL_LOOKUP_CODES,
    channel_signal_rows,
    default_no_llm_weights,
    lineage_edge_specs,
    lineage_rebuild_spec,
    llm_participated,
    rank_channel_evidence,
    reconstruction_version,
    weights_for_channel_scores,
)
from lineageweave.models import Edge

_ROOT = Path(__file__).resolve().parents[1]


def _four_channel_edge() -> Edge:
    scores = {"temporal": 0.8, "secondary_key": 1.0, "text": 0.5, "llm": 0.9}
    weights = {"temporal": 0.15, "secondary_key": 0.15, "text": 0.30, "llm": 0.40}
    fused = sum(weights[name] * scores[name] for name in scores)
    return Edge("parent-a", "child-b", fused, scores)


def _no_llm_edge() -> Edge:
    scores = {"temporal": 0.8, "secondary_key": 1.0, "text": 0.5}
    weights = default_no_llm_weights()
    fused = sum(weights[name] * scores[name] for name in scores)
    return Edge("parent-a", "child-b", fused, scores)


def test_four_channel_edge_round_trips_scores_and_normalized_weights() -> None:
    edge = _four_channel_edge()
    rows = channel_signal_rows(edge)
    codes = [row["channel_name"] for row in rows]
    assert codes == ["temporal", "secondary_key", "text", "llm"]
    by_name = {row["channel_name"]: row for row in rows}
    assert by_name["llm"]["signal_code"] == "lineage_signal_llm"
    assert by_name["temporal"]["signal_weight"] == pytest.approx(0.15)
    assert by_name["text"]["signal_weight"] == pytest.approx(0.30)
    evidence = rank_channel_evidence(rows)
    assert [item["rank"] for item in evidence] == [1, 2, 3, 4]
    assert evidence[0]["signal_code"] == "llm"
    assert sum(item["contribution"] for item in evidence) == pytest.approx(edge.fused_score)


def test_no_llm_reconstruction_persists_exactly_three_channels() -> None:
    edge = _no_llm_edge()
    rows = channel_signal_rows(edge)
    assert [row["channel_name"] for row in rows] == ["temporal", "secondary_key", "text"]
    assert "llm" not in {row["channel_name"] for row in rows}
    assert "lineage_signal_llm" not in {row["signal_code"] for row in rows}
    evidence = rank_channel_evidence(rows)
    assert llm_participated(evidence) is False
    weights = weights_for_channel_scores(edge.channel_scores)
    assert weights == pytest.approx({"temporal": 0.25, "secondary_key": 0.25, "text": 0.5})


def test_contributions_reconcile_to_fused_score_within_tolerance() -> None:
    edge = _four_channel_edge()
    rows = channel_signal_rows(edge)
    residual = abs(sum(float(row["signal_contribution"]) for row in rows) - edge.fused_score)
    assert residual <= CHANNEL_EVIDENCE_TOLERANCE


def test_rebuild_accepts_expected_multi_channel_quantization_error() -> None:
    scores = {
        "temporal": 0.1234567,
        "secondary_key": 0.2345678,
        "text": 0.3456789,
        "llm": 0.4567891,
    }
    weights = {"temporal": 0.15, "secondary_key": 0.15, "text": 0.30, "llm": 0.40}
    edge = Edge(
        "parent-a",
        "child-b",
        sum(weights[name] * scores[name] for name in scores),
        scores,
    )

    rows = channel_signal_rows(edge)
    assert len(rows) == 4
    assert lineage_rebuild_spec([edge]).signal_rows


def test_mismatched_fused_score_is_rejected() -> None:
    edge = Edge("parent-a", "child-b", 0.99, {"temporal": 0.1, "secondary_key": 0.1, "text": 0.1})
    with pytest.raises(ValueError, match="do not reconcile"):
        channel_signal_rows(edge)


def test_fixture_reconstruction_never_fabricates_llm() -> None:
    edges = lineage_edge_specs(sample_records())
    assert edges
    spec = lineage_rebuild_spec(edges)
    assert all(row["channel_name"] != "llm" for row in spec.signal_rows)
    assert "lineage_signal_llm" not in {code for code, _weight in spec.channel_weights}
    for edge in edges:
        rows = channel_signal_rows(edge)
        residual = abs(sum(float(row["signal_contribution"]) for row in rows) - edge.fused_score)
        assert residual <= CHANNEL_EVIDENCE_TOLERANCE


def test_rebuild_spec_is_idempotent_for_the_same_edges() -> None:
    edges = lineage_edge_specs(sample_records())
    first = lineage_rebuild_spec(edges, package_version="2.14.0")
    second = lineage_rebuild_spec(edges, package_version="2.14.0")
    assert first == second
    assert first.reconstruction_version == reconstruction_version("2.14.0")
    assert first.reconstruction_version == "lineageweave.reconstruct/2.14.0"


def test_rank_is_contribution_then_controlled_signal_order() -> None:
    rows = [
        {
            "channel_name": "text",
            "signal_code": LINEAGE_SIGNAL_LOOKUP_CODES["text"],
            "signal_score": 1.0,
            "signal_weight": 0.5,
            "signal_contribution": 0.2,
        },
        {
            "channel_name": "temporal",
            "signal_code": LINEAGE_SIGNAL_LOOKUP_CODES["temporal"],
            "signal_score": 1.0,
            "signal_weight": 0.25,
            "signal_contribution": 0.2,
        },
        {
            "channel_name": "secondary_key",
            "signal_code": LINEAGE_SIGNAL_LOOKUP_CODES["secondary_key"],
            "signal_score": 0.4,
            "signal_weight": 0.25,
            "signal_contribution": 0.1,
        },
    ]
    evidence = rank_channel_evidence(rows)
    assert [item["signal_code"] for item in evidence] == ["temporal", "text", "secondary_key"]
    assert [item["rank"] for item in evidence] == [1, 2, 3]


def test_migrate_sh_replays_channel_evidence_and_tenant_settings() -> None:
    migrate = (_ROOT / "docker/postgres-init/migrate.sh").read_text()
    assert "0103_*" in migrate
    assert "0104_*" in migrate
    assert "0105_*" in migrate


def test_channel_evidence_migration_has_no_jsonb() -> None:
    migration = (_ROOT / "migrations" / "0105_post_lineage_edge_signal.sql").read_text()
    assert "jsonb" not in migration.casefold()
    assert "post_lineage_edge_signal" in migration
    assert "event_lineage_rebuild" in migration
    assert "on delete cascade" in migration.casefold()
