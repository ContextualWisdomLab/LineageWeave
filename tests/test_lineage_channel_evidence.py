"""Event Lineage channel evidence must round-trip without fabricating LLM scores."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pytest

from lineageweave.channel_weight_estimation import (
    estimate_channel_weights,
)
from lineageweave.fixtures import sample_records
from lineageweave.lineage_persistence import (
    CHANNEL_EVIDENCE_TOLERANCE,
    LINEAGE_SIGNAL_LOOKUP_CODES,
    channel_signal_rows,
    lineage_edge_specs,
    lineage_rebuild_spec,
    llm_participated,
    rank_channel_evidence,
    quantize_signal_value,
    reconstruction_version,
)
from lineageweave.models import Edge

_ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def _estimated_weights() -> dict[str, float]:
    """Return an explicit non-measurement fixture for projection tests."""
    return {"temporal": 0.5, "secondary_key": 0.3, "text": 0.2}


def _no_llm_edge() -> Edge:
    scores = {"temporal": 0.8, "secondary_key": 1.0, "text": 0.5}
    weights = _estimated_weights()
    fused = sum(weights[name] * scores[name] for name in scores)
    return Edge("parent-a", "child-b", fused, scores)


def test_grounded_edge_round_trips_scores_and_normalized_weights() -> None:
    edge = _no_llm_edge()
    weights = _estimated_weights()
    rows = channel_signal_rows(edge, weights)
    codes = [row["channel_name"] for row in rows]
    assert codes == ["temporal", "secondary_key", "text"]
    by_name = {row["channel_name"]: row for row in rows}
    assert by_name["temporal"]["signal_weight"] == quantize_signal_value(weights["temporal"])
    assert by_name["text"]["signal_weight"] == quantize_signal_value(weights["text"])
    evidence = rank_channel_evidence(rows)
    assert [item["rank"] for item in evidence] == [1, 2, 3]
    assert sum(item["contribution"] for item in evidence) == pytest.approx(edge.fused_score)


def test_no_llm_reconstruction_persists_exactly_three_channels() -> None:
    edge = _no_llm_edge()
    weights = _estimated_weights()
    rows = channel_signal_rows(edge, weights)
    assert [row["channel_name"] for row in rows] == ["temporal", "secondary_key", "text"]
    assert "llm" not in {row["channel_name"] for row in rows}
    assert "lineage_signal_llm" not in {row["signal_code"] for row in rows}
    evidence = rank_channel_evidence(rows)
    assert llm_participated(evidence) is False
    assert {row["channel_name"]: row["signal_weight"] for row in rows} == {
        channel: quantize_signal_value(weight) for channel, weight in weights.items()
    }


def test_contributions_reconcile_to_fused_score_within_tolerance() -> None:
    edge = _no_llm_edge()
    rows = channel_signal_rows(edge, _estimated_weights())
    residual = abs(sum(float(row["signal_contribution"]) for row in rows) - edge.fused_score)
    assert residual <= CHANNEL_EVIDENCE_TOLERANCE


def test_rebuild_accepts_expected_multi_channel_quantization_error() -> None:
    scores = {
        "temporal": 0.1234567,
        "secondary_key": 0.2345678,
        "text": 0.3456789,
    }
    weights = _estimated_weights()
    edge = Edge(
        "parent-a",
        "child-b",
        sum(weights[name] * scores[name] for name in scores),
        scores,
    )

    rows = channel_signal_rows(edge, weights)
    assert len(rows) == 3
    assert lineage_rebuild_spec([edge], weights=weights).signal_rows


def test_duplicated_text_proxy_cannot_invent_an_llm_weight() -> None:
    """A copied text score is not an independent LLM validity anchor."""
    pair_scores = [{"temporal": 0.8, "secondary_key": 0.6, "text": 0.4}]
    group_ids = [0]
    assert (
        estimate_channel_weights(
            [{**scores, "llm": scores["text"]} for scores in pair_scores],
            group_ids,
        )
        is None
    )


def test_mismatched_fused_score_is_rejected() -> None:
    edge = Edge("parent-a", "child-b", 0.99, {"temporal": 0.1, "secondary_key": 0.1, "text": 0.1})
    with pytest.raises(ValueError, match="do not reconcile"):
        channel_signal_rows(edge, _estimated_weights())


def test_fixture_reconstruction_never_fabricates_llm() -> None:
    weights = _estimated_weights()
    edges = lineage_edge_specs(sample_records(), weights=weights)
    assert edges
    spec = lineage_rebuild_spec(edges, weights=weights)
    assert all(row["channel_name"] != "llm" for row in spec.signal_rows)
    assert "lineage_signal_llm" not in {code for code, _weight in spec.channel_weights}
    for edge in edges:
        rows = channel_signal_rows(edge, weights)
        residual = abs(sum(float(row["signal_contribution"]) for row in rows) - edge.fused_score)
        assert residual <= CHANNEL_EVIDENCE_TOLERANCE


def test_rebuild_spec_is_idempotent_for_the_same_edges() -> None:
    weights = _estimated_weights()
    edges = lineage_edge_specs(sample_records(), weights=weights)
    first = lineage_rebuild_spec(edges, weights=weights, package_version="2.14.0")
    second = lineage_rebuild_spec(edges, weights=weights, package_version="2.14.0")
    assert first == second
    assert first.reconstruction_version == reconstruction_version("2.14.0")
    assert first.reconstruction_version == "lineageweave.reconstruct/2.14.0"


def test_rank_is_contribution_then_controlled_signal_order() -> None:
    weights = _estimated_weights()
    tied_contribution = min(weights.values())
    rows = [
        {
            "channel_name": "text",
            "signal_code": LINEAGE_SIGNAL_LOOKUP_CODES["text"],
            "signal_score": tied_contribution / weights["text"],
            "signal_weight": weights["text"],
            "signal_contribution": tied_contribution,
        },
        {
            "channel_name": "temporal",
            "signal_code": LINEAGE_SIGNAL_LOOKUP_CODES["temporal"],
            "signal_score": tied_contribution / weights["temporal"],
            "signal_weight": weights["temporal"],
            "signal_contribution": tied_contribution,
        },
        {
            "channel_name": "secondary_key",
            "signal_code": LINEAGE_SIGNAL_LOOKUP_CODES["secondary_key"],
            "signal_score": tied_contribution / weights["secondary_key"],
            "signal_weight": weights["secondary_key"],
            "signal_contribution": tied_contribution,
        },
    ]
    evidence = rank_channel_evidence(rows)
    assert [item["signal_code"] for item in evidence] == ["temporal", "secondary_key", "text"]
    assert [item["rank"] for item in evidence] == [1, 2, 3]


def test_migrate_sh_replays_channel_evidence_and_tenant_settings() -> None:
    """ADR 0166's portable filename boundary must still cover 0103 and 0174
    on existing volumes -- no individual allowlist entry is needed for
    either, since the general four-digit pattern already replays both.
    """
    migrate = (_ROOT / "docker/postgres-init/migrate.sh").read_text()
    assert "[0-9][0-9][0-9][0-9]_*" in migrate
    assert "000[0-9]_*|001[01]_*" in migrate
    assert "0103_*" not in migrate
    assert "0174_*" not in migrate


def test_channel_evidence_migration_has_no_jsonb() -> None:
    migration = (_ROOT / "migrations" / "0174_post_lineage_edge_signal.sql").read_text()
    assert "jsonb" not in migration.casefold()
    assert "post_lineage_edge_signal" in migration
    assert "event_lineage_rebuild" in migration
    assert "on delete cascade" in migration.casefold()
