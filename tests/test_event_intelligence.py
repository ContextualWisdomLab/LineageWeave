"""Runtime tests for Event Intelligence Dossier v1."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from lineageweave.event_intelligence import (
    CHANNEL_UNAVAILABLE,
    EventIntelligenceDossier,
    EventIntelligenceValidationError,
    event_intelligence_dossier_from_dict,
)

ROOT = Path(__file__).parents[1]
EXAMPLE = ROOT / "examples" / "event-intelligence-dossier-v1.json"


def example() -> dict[str, object]:
    """Load a detached canonical example."""
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_example_round_trip_is_deterministic() -> None:
    """The published example preserves its digest and canonical serialization."""
    payload = example()
    dossier = event_intelligence_dossier_from_dict(payload)
    assert isinstance(dossier, EventIntelligenceDossier)
    assert dossier.contract_version == 1
    assert dossier.event_id == "event-1"
    assert dossier.to_dict() == payload
    assert json.loads(dossier.to_json()) == payload
    assert dossier.dossier_sha256() == payload["dossier_sha256"]


def test_composer_mode_adds_digest_without_mutating_input() -> None:
    """An undigested composer payload becomes a detached, digest-bound artifact."""
    payload = example()
    payload.pop("dossier_sha256")
    original = deepcopy(payload)
    dossier = event_intelligence_dossier_from_dict(payload, require_digest=False)
    assert payload == original
    assert dossier.to_dict()["dossier_sha256"] == dossier.dossier_sha256()


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda p: p.update(extra=True), "unexpected fields"),
        (lambda p: p.pop("claims"), "missing fields: claims"),
        (lambda p: p.update(contract_version=True), "must be an integer"),
        (lambda p: p.update(contract_version=2), "not supported"),
        (lambda p: p.update(event_id=""), "non-empty string"),
        (lambda p: p.update(dossier_sha256="0" * 64), "does not match"),
    ],
)
def test_root_contract_is_strict(mutate, message: str) -> None:
    """Root shape, version, identifiers, and digest fail closed."""
    payload = example()
    mutate(payload)
    with pytest.raises(EventIntelligenceValidationError, match=message):
        event_intelligence_dossier_from_dict(payload)


@pytest.mark.parametrize("root", [None, [], {1: "bad"}])
def test_root_must_be_a_json_object(root: object) -> None:
    """Non-object or non-string-key roots are rejected."""
    with pytest.raises(EventIntelligenceValidationError, match="must be an object"):
        event_intelligence_dossier_from_dict(root)


def test_digest_is_required_by_default() -> None:
    """Wire validation requires a self-digest unless composer mode is explicit."""
    payload = example()
    payload.pop("dossier_sha256")
    with pytest.raises(EventIntelligenceValidationError, match="dossier_sha256"):
        event_intelligence_dossier_from_dict(payload)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("event_end", "2026-08-18T08:59:59+09:00", "event_end"),
        ("assertion_time", "2026-08-19T10:00:01Z", "assertion_time"),
        ("document_time", "2026-08-19T10:00:01Z", "document_time"),
        ("available_time", "2026-08-19T12:00:01Z", "available_time"),
        ("event_start", "2026-08-18T09:00:00", "UTC offset"),
        ("event_start", "not-a-time", "ISO-8601"),
    ],
)
def test_temporal_clocks_prevent_leakage(field: str, value: object, message: str) -> None:
    """Event, report, availability, and cutoff clocks retain their ordering."""
    payload = example()
    payload.pop("dossier_sha256")
    payload["temporal_context"][field] = value
    with pytest.raises(EventIntelligenceValidationError, match=message):
        event_intelligence_dossier_from_dict(payload, require_digest=False)


def test_optional_event_end_is_supported() -> None:
    """Open-ended event intervals remain representable."""
    payload = example()
    payload.pop("dossier_sha256")
    payload["temporal_context"]["event_end"] = None
    assert event_intelligence_dossier_from_dict(payload, require_digest=False).event_id == "event-1"


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda p: p["evidence"].append(deepcopy(p["evidence"][0])),
            "evidence ids must be unique",
        ),
        (
            lambda p: p["evidence"][0].update(source_system="unknown"),
            "source_system is not supported",
        ),
        (
            lambda p: p["evidence"][0].update(content_sha256="ABC"),
            "lowercase SHA-256",
        ),
        (
            lambda p: p["evidence"][0].update(available_time="2026-08-19T12:00:01Z"),
            "available after",
        ),
        (
            lambda p: p["evidence"][0].update(recorded_time="2026-08-19T09:59:59Z"),
            "recorded_time",
        ),
        (lambda p: p.update(evidence=[]), "evidence must not be empty"),
    ],
)
def test_evidence_is_immutable_cutoff_safe_and_authorized(mutate, message: str) -> None:
    """Evidence identity, authority, digest, and availability remain explicit."""
    payload = example()
    payload.pop("dossier_sha256")
    mutate(payload)
    with pytest.raises(EventIntelligenceValidationError, match=message):
        event_intelligence_dossier_from_dict(payload, require_digest=False)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda p: p["event_ontology"].append(deepcopy(p["event_ontology"][0])),
            "ontology references must be unique",
        ),
        (lambda p: p.update(event_ontology=[]), "event_ontology must not be empty"),
        (
            lambda p: p["event_ontology"][0].update(term_iri="relative"),
            "absolute IRI",
        ),
    ],
)
def test_ontology_profile_is_versioned_and_unique(mutate, message: str) -> None:
    """Semantic references cannot be ambiguous or relative."""
    payload = example()
    payload.pop("dossier_sha256")
    mutate(payload)
    with pytest.raises(EventIntelligenceValidationError, match=message):
        event_intelligence_dossier_from_dict(payload, require_digest=False)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda p: p["knowledge_graph"].update(status_code="unavailable"), "must be available"),
        (lambda p: p["knowledge_graph"].update(nodes=[]), "nodes must not be empty"),
        (
            lambda p: p["knowledge_graph"]["nodes"].append(
                deepcopy(p["knowledge_graph"]["nodes"][0])
            ),
            "node ids must be unique",
        ),
        (
            lambda p: p.update(event_id="missing-event"),
            "event_id must identify",
        ),
        (
            lambda p: p["knowledge_graph"]["edges"][0].update(target_node_id="missing"),
            "existing graph nodes",
        ),
        (
            lambda p: p["knowledge_graph"]["edges"].append(
                deepcopy(p["knowledge_graph"]["edges"][0])
            ),
            "edges must be unique",
        ),
        (
            lambda p: p["knowledge_graph"]["nodes"][0]["relevance"].update(estimate=2.0),
            "uncertainty must contain",
        ),
        (
            lambda p: p["knowledge_graph"]["nodes"][0]["relevance"].update(authority_system="unknown"),
            "authority_system is not supported",
        ),
        (
            lambda p: p["knowledge_graph"]["nodes"][0]["relevance"].update(evidence_ids=["missing"]),
            "unknown evidence ids",
        ),
    ],
)
def test_knowledge_graph_is_resolvable_and_evidence_backed(mutate, message: str) -> None:
    """Nodes, edges, relevance, and evidence form one resolvable projection."""
    payload = example()
    payload.pop("dossier_sha256")
    mutate(payload)
    with pytest.raises(EventIntelligenceValidationError, match=message):
        event_intelligence_dossier_from_dict(payload, require_digest=False)


@pytest.mark.parametrize("channel", ["tepp", "fast_mlsirm", "contextual_orchestrator"])
def test_optional_channels_are_explicitly_unavailable(channel: str) -> None:
    """Unavailable scientific channels are not fabricated as zero values."""
    payload = example()
    payload.pop("dossier_sha256")
    payload[channel] = {"status_code": CHANNEL_UNAVAILABLE}
    assert event_intelligence_dossier_from_dict(payload, require_digest=False).to_dict()[channel] == {
        "status_code": CHANNEL_UNAVAILABLE
    }


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda p: p["tepp"].update(snapshot_id="other"), "snapshot_id"),
        (
            lambda p: p["tepp"].update(knowledge_cutoff="2026-08-19T11:59:59Z"),
            "knowledge_cutoff",
        ),
        (
            lambda p: p["tepp"].update(artifact_digest_sha256="bad"),
            "SHA-256",
        ),
        (
            lambda p: p["fast_mlsirm"].update(standard_error=-0.1),
            "must not be negative",
        ),
        (
            lambda p: p["contextual_orchestrator"].update(verdict_code="maybe"),
            "verdict_code is not supported",
        ),
        (
            lambda p: p["contextual_orchestrator"].update(confidence=True),
            "must be a number",
        ),
        (
            lambda p: p["contextual_orchestrator"].update(psychometric_score=0.9),
            "unexpected fields",
        ),
        (
            lambda p: p["tepp"].update(status_code="pending"),
            "available or unavailable",
        ),
    ],
)
def test_provider_authorities_cannot_be_collapsed(mutate, message: str) -> None:
    """TEPP, fast-mlsirm, and the judge retain separate typed authority."""
    payload = example()
    payload.pop("dossier_sha256")
    mutate(payload)
    with pytest.raises(EventIntelligenceValidationError, match=message):
        event_intelligence_dossier_from_dict(payload, require_digest=False)


def test_claims_are_unique_and_evidence_grounded() -> None:
    """Every buyer claim has a unique identity and committed evidence."""
    payload = example()
    payload.pop("dossier_sha256")
    payload["claims"].append(deepcopy(payload["claims"][0]))
    with pytest.raises(EventIntelligenceValidationError, match="claim ids must be unique"):
        event_intelligence_dossier_from_dict(payload, require_digest=False)

    payload = example()
    payload.pop("dossier_sha256")
    payload["claims"][0]["evidence_ids"] = ["missing"]
    with pytest.raises(EventIntelligenceValidationError, match="unknown evidence ids"):
        event_intelligence_dossier_from_dict(payload, require_digest=False)


def test_scalar_and_evidence_list_bounds_are_enforced() -> None:
    """Text, numbers, probabilities, and reference lists keep hard bounds."""
    payload = example()
    payload.pop("dossier_sha256")
    payload["event_title"] = "x" * 4001
    with pytest.raises(EventIntelligenceValidationError, match="at most"):
        event_intelligence_dossier_from_dict(payload, require_digest=False)

    payload = example()
    payload.pop("dossier_sha256")
    payload["knowledge_graph"]["nodes"][0]["relevance"]["estimate"] = float("inf")
    with pytest.raises(EventIntelligenceValidationError, match="finite"):
        event_intelligence_dossier_from_dict(payload, require_digest=False)

    payload = example()
    payload.pop("dossier_sha256")
    payload["contextual_orchestrator"]["confidence"] = 1.1
    with pytest.raises(EventIntelligenceValidationError, match=r"between 0\.0 and 1\.0"):
        event_intelligence_dossier_from_dict(payload, require_digest=False)

    payload = example()
    payload.pop("dossier_sha256")
    payload["claims"][0]["evidence_ids"] = []
    with pytest.raises(EventIntelligenceValidationError, match="must not be empty"):
        event_intelligence_dossier_from_dict(payload, require_digest=False)

    payload = example()
    payload.pop("dossier_sha256")
    payload["claims"][0]["evidence_ids"] = ["source-post", "source-post"]
    with pytest.raises(EventIntelligenceValidationError, match="unique values"):
        event_intelligence_dossier_from_dict(payload, require_digest=False)
