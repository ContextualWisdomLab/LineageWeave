"""Exact TEPP topic-lineage artifact consumer contracts."""

from copy import deepcopy

import pytest

from lineageweave.topic_lineage_artifact import (
    TopicLineageUnavailable,
    parse_topic_lineage_artifact,
    parse_topic_lineage_envelope,
    project_topic_lineage_projection,
    topic_lineage_artifact_sha256,
)


def _artifact(run_id: str = "tepp-run-1") -> dict[str, object]:
    """Return one synthetic, non-identifying TEPP artifact."""

    return {
        "schema_version": "tepp.trsl_topic_lineage.v1",
        "run_id": run_id,
        "snapshot_id": "ab" * 32,
        "knowledge_cutoff": "2026-01-12T12:00:00Z",
        "selected_seed": 7,
        "iterations": 4,
        "objective": 1.25,
        "topic_count": 2,
        "evidence_count": 3,
        "connected_post_count": 3,
        "lineage_count": 2,
        "sequence_edges": [
            {
                "predecessor_document_id": "00000000-0000-0000-0000-000000000001",
                "successor_document_id": "00000000-0000-0000-0000-000000000002",
                "topic_index": 0,
                "association_strength": 0.8,
            },
            {
                "predecessor_document_id": "00000000-0000-0000-0000-000000000002",
                "successor_document_id": "00000000-0000-0000-0000-000000000003",
                "topic_index": 1,
                "association_strength": 0.7,
            },
        ],
        "inference_status": "fitted_topic_association_not_causation",
    }


def _envelope(artifact: dict[str, object] | None = None) -> dict[str, object]:
    """Wrap one artifact in TEPP's completed digest-bound envelope."""

    result = artifact or _artifact()
    return {
        "status": "completed",
        "run_id": result["run_id"],
        "result_schema_version": result["schema_version"],
        "result_sha256": topic_lineage_artifact_sha256(result),
        "result": result,
    }


def test_exact_envelope_and_authorized_projection() -> None:
    """Only validated edges whose endpoints are visible contribute counts."""

    artifact = parse_topic_lineage_envelope(
        _envelope(),
        expected_snapshot_id="ab" * 32,
        expected_knowledge_cutoff="2026-01-12T12:00:00+00:00",
        expected_remote_run_id="tepp-run-1",
    )
    projection = project_topic_lineage_projection(
        [artifact],
        [
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000000002",
        ],
    )

    assert projection["status"] == "validated"
    assert projection["connected_post_count"] == 2
    assert projection["lineage_count"] == 1
    assert projection["artifact_count"] == 1
    assert len(projection["sequence_edges"]) == 1


def test_projection_keeps_run_scoped_topic_identity_and_unavailable_state() -> None:
    """Equal topic indexes from separate runs remain separate lineages."""

    second = deepcopy(_artifact("tepp-run-2"))
    second["sequence_edges"] = [deepcopy(_artifact()["sequence_edges"][0])]
    second["connected_post_count"] = 2
    second["lineage_count"] = 1
    second["evidence_count"] = 2
    visible = [
        "00000000-0000-0000-0000-000000000001",
        "00000000-0000-0000-0000-000000000002",
    ]

    projection = project_topic_lineage_projection([_artifact(), second], visible)
    assert projection["lineage_count"] == 2
    assert projection["artifact_count"] == 2
    assert project_topic_lineage_projection([_artifact()], [visible[0]])["status"] == "unavailable"


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda value: value.update(run_id=None), "canonical text"),
        (lambda value: value.update(run_id=""), "outside"),
        (lambda value: value.update(selected_seed=True), "unsigned"),
        (lambda value: value.update(knowledge_cutoff="bad-date"), "RFC 3339"),
        (lambda value: value.update(knowledge_cutoff="2026-01-12T12:00:00"), "offset"),
        (lambda value: value.update(schema_version="unknown"), "schema"),
        (lambda value: value.update(iterations=0), "iterations"),
        (lambda value: value.update(objective="1.25"), "objective"),
        (lambda value: value.update(objective=10**400), "finite"),
        (lambda value: value.update(topic_count=1), "at least two"),
        (lambda value: value.update(connected_post_count=4), "dimensions"),
        (lambda value: value.update(connected_post_count=2), "counts"),
        (lambda value: value.update(sequence_edges=()), "sequence_edges"),
        (lambda value: value.update(inference_status="causal"), "inference"),
        (lambda value: value.update(extra=True), "fields"),
        (lambda value: value["sequence_edges"][0].update(extra=True), "edge fields"),
        (
            lambda value: value["sequence_edges"][0].update(
                predecessor_document_id="not-a-uuid"
            ),
            "UUID",
        ),
        (
            lambda value: value["sequence_edges"][0].update(
                predecessor_document_id="AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA"
            ),
            "canonical UUID",
        ),
        (lambda value: value["sequence_edges"][0].update(association_strength="0.8"), "numeric"),
        (lambda value: value["sequence_edges"][0].update(association_strength=10**400), "finite"),
        (lambda value: value["sequence_edges"][0].update(topic_index=2), "edge"),
        (
            lambda value: value["sequence_edges"][0].update(
                successor_document_id=value["sequence_edges"][0]["predecessor_document_id"]
            ),
            "edge",
        ),
    ],
)
def test_artifact_rejects_contract_drift(mutate, message: str) -> None:
    """Schema, convergence, count, inference, and edge drift fail closed."""

    artifact = _artifact()
    mutate(artifact)
    with pytest.raises(TopicLineageUnavailable, match=message):
        parse_topic_lineage_artifact(artifact)


@pytest.mark.parametrize(
    "value",
    [
        "{not-json",
        "x" * (256 * 1024 + 1),
        ["not", "an", "object"],
        {"oversized": "x" * (256 * 1024)},
        {"not_json": float("inf")},
    ],
)
def test_artifact_rejects_invalid_or_oversized_json(value) -> None:
    """The JSON boundary is bounded and rejects non-objects and non-finite values."""

    with pytest.raises(TopicLineageUnavailable):
        parse_topic_lineage_artifact(value)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(status="accepted"),
        lambda value: value.update(result_sha256="0" * 64),
        lambda value: value.update(run_id="another-run"),
    ],
)
def test_envelope_rejects_incomplete_or_unbound_results(mutation) -> None:
    """Completion, digest, and run identity are mandatory."""

    envelope = _envelope()
    mutation(envelope)
    with pytest.raises(TopicLineageUnavailable):
        parse_topic_lineage_envelope(envelope)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"expected_remote_run_id": "another-run"},
        {"expected_snapshot_id": "different-snapshot"},
        {"expected_knowledge_cutoff": "2026-01-13T12:00:00Z"},
    ],
)
def test_envelope_rejects_persisted_identity_drift(kwargs) -> None:
    """Stored run, snapshot, and cutoff bindings cannot drift."""

    with pytest.raises(TopicLineageUnavailable):
        parse_topic_lineage_envelope(_envelope(), **kwargs)


def test_envelope_rejects_an_unknown_result_schema() -> None:
    """A completed result with another schema remains unavailable."""

    envelope = _envelope()
    envelope["result_schema_version"] = "unknown"
    with pytest.raises(TopicLineageUnavailable, match="result schema"):
        parse_topic_lineage_envelope(envelope)
