"""Published schema and example contract tests without optional dependencies."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from lineageweave.event_intelligence import (
    CHANNEL_UNAVAILABLE,
    EventIntelligenceValidationError,
    event_intelligence_dossier_from_dict,
)

ROOT = Path(__file__).parents[1]
SCHEMA_PATH = ROOT / "schemas" / "event_intelligence_dossier_v1.schema.json"
EXAMPLE_PATH = ROOT / "examples" / "event-intelligence-dossier-v1.json"


def load_schema() -> dict[str, object]:
    """Load the committed JSON Schema as a plain mapping."""
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def load_example() -> dict[str, object]:
    """Load the committed canonical example."""
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def test_schema_declares_strict_draft_2020_12_contract() -> None:
    """The published schema fixes its draft, identifier, and strict root shape."""
    schema = load_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith("event_intelligence_dossier_v1.schema.json")
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["properties"]["event_ontology"]["uniqueItems"] is True
    graph = schema["$defs"]["knowledge_graph"]["properties"]
    assert graph["nodes"]["minItems"] == 1
    assert graph["nodes"]["uniqueItems"] is True
    assert graph["edges"]["uniqueItems"] is True


def test_canonical_example_round_trips_through_production_validator() -> None:
    """The example reconstructs and preserves its committed self-digest."""
    payload = load_example()
    schema_errors = list(Draft202012Validator(load_schema()).iter_errors(payload))
    assert schema_errors == []
    dossier = event_intelligence_dossier_from_dict(payload)
    assert dossier.to_dict() == payload


def test_runtime_validator_owns_evidence_id_uniqueness() -> None:
    """Runtime validation rejects duplicate IDs even when object fields differ."""
    payload = load_example()
    duplicate = deepcopy(payload["evidence"][0])
    duplicate["source_uri"] = "urn:test:duplicate-source"
    payload["evidence"].append(duplicate)
    assert Draft202012Validator(load_schema()).is_valid(payload)
    with pytest.raises(EventIntelligenceValidationError, match="evidence ids must be unique"):
        event_intelligence_dossier_from_dict(payload, require_digest=False)


def test_validator_refuses_judge_psychometric_override_and_unknown_fields() -> None:
    """A judge cannot smuggle a numerical measurement into its channel."""
    payload = load_example()
    payload["contextual_orchestrator"]["psychometric_score"] = 0.99
    with pytest.raises(EventIntelligenceValidationError, match="unexpected fields"):
        event_intelligence_dossier_from_dict(payload)


def test_validator_accepts_explicitly_unavailable_optional_channels() -> None:
    """Missing scientific channels are explicit unavailable objects, never null scores."""
    payload = load_example()
    for name in ("tepp", "fast_mlsirm", "contextual_orchestrator"):
        payload[name] = {"status_code": CHANNEL_UNAVAILABLE}
    payload.pop("dossier_sha256")
    dossier = event_intelligence_dossier_from_dict(payload, require_digest=False)
    serialized = dossier.to_dict()
    for name in ("tepp", "fast_mlsirm", "contextual_orchestrator"):
        assert serialized[name] == {"status_code": CHANNEL_UNAVAILABLE}


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda payload: None, "dossier must be an object"),
        (lambda payload: {1: "not-a-string-key"}, "dossier must be an object"),
    ],
)
def test_validator_refuses_non_object_roots(mutator, message: str) -> None:
    """Wire roots must be JSON-style objects with string keys."""
    payload = load_example()
    invalid = mutator(payload)
    with pytest.raises(EventIntelligenceValidationError, match=message):
        event_intelligence_dossier_from_dict(invalid)


def test_validator_refuses_missing_fields_non_arrays_and_invalid_channel_status() -> None:
    """Wire reconstruction fails closed at structural boundaries."""
    payload = load_example()
    payload.pop("claims")
    with pytest.raises(EventIntelligenceValidationError, match="missing fields: claims"):
        event_intelligence_dossier_from_dict(payload)

    payload = load_example()
    payload["claims"] = "not-an-array"
    with pytest.raises(EventIntelligenceValidationError, match="claims must be an array"):
        event_intelligence_dossier_from_dict(payload)

    payload = load_example()
    payload["tepp"] = {"status_code": "pending"}
    with pytest.raises(EventIntelligenceValidationError, match="available or unavailable"):
        event_intelligence_dossier_from_dict(payload)


def test_validator_refuses_unavailable_knowledge_graph_and_digest_tampering() -> None:
    """The local graph is mandatory and the self-digest is authoritative."""
    payload = load_example()
    payload["knowledge_graph"]["status_code"] = CHANNEL_UNAVAILABLE
    with pytest.raises(EventIntelligenceValidationError, match="must be available"):
        event_intelligence_dossier_from_dict(payload)

    payload = load_example()
    payload["dossier_sha256"] = "0" * 64
    with pytest.raises(EventIntelligenceValidationError, match="does not match"):
        event_intelligence_dossier_from_dict(payload)


def test_composer_mode_accepts_an_existing_valid_digest() -> None:
    """Composer mode can verify an already-digested payload without requiring removal."""
    payload = load_example()
    assert event_intelligence_dossier_from_dict(payload, require_digest=False).to_dict() == payload
