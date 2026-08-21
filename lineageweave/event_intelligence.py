"""Evidence-bound Event Intelligence Dossier v1.

The dossier composes, without blending authority:

* LineageWeave knowledge-graph and ontology evidence;
* TEPP temporal-event/topic artifacts;
* fast-mlsirm psychometric artifacts; and
* contextual-orchestrator evidence-bounded judgments.

It is a deterministic interchange/read artifact, not a numerical estimator.
Every surfaced claim and measurement resolves to immutable evidence available
at the dossier's knowledge cutoff.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
import re
from typing import Any

import rfc8785

from .adjudication_client import ALLOWED_ADJUDICATION_VERDICTS

EVENT_INTELLIGENCE_CONTRACT_VERSION = 1
CHANNEL_AVAILABLE = "available"
CHANNEL_UNAVAILABLE = "unavailable"

_SOURCE_SYSTEMS = frozenset(
    {
        "source_document",
        "lineageweave_knowledge_graph",
        "lineageweave_ontology",
        "tepp",
        "fast_mlsirm",
        "contextual_orchestrator",
    }
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MAX_SAFE_INTEGER = 2**53 - 1
_RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)

_ROOT_FIELDS = frozenset(
    {
        "contract_version",
        "event_id",
        "event_title",
        "source_snapshot_id",
        "temporal_context",
        "event_ontology",
        "evidence",
        "knowledge_graph",
        "tepp",
        "fast_mlsirm",
        "contextual_orchestrator",
        "claims",
        "dossier_sha256",
    }
)
_TEMPORAL_FIELDS = frozenset(
    {
        "event_start",
        "event_end",
        "assertion_time",
        "document_time",
        "available_time",
        "knowledge_cutoff",
    }
)
_ONTOLOGY_FIELDS = frozenset(
    {"term_iri", "preferred_label", "vocabulary_version", "semantic_role_code"}
)
_EVIDENCE_FIELDS = frozenset(
    {
        "evidence_id",
        "source_system",
        "source_uri",
        "content_sha256",
        "available_time",
        "recorded_time",
    }
)
_GRAPH_FIELDS = frozenset({"status_code", "nodes", "edges"})
_NODE_FIELDS = frozenset(
    {"node_id", "node_type_code", "label", "ontology", "relevance", "evidence_ids"}
)
_EDGE_FIELDS = frozenset(
    {
        "source_node_id",
        "target_node_id",
        "edge_type_code",
        "ontology",
        "evidence_ids",
    }
)
_RELEVANCE_FIELDS = frozenset(
    {
        "method_code",
        "method_version",
        "authority_system",
        "estimate",
        "uncertainty_lower",
        "uncertainty_upper",
        "evidence_ids",
    }
)
_TEPP_FIELDS = frozenset(
    {
        "status_code",
        "remote_run_id",
        "artifact_id",
        "snapshot_id",
        "knowledge_cutoff",
        "model_contract_version",
        "engine_version",
        "artifact_digest_sha256",
        "topic_relevance",
        "evidence_ids",
    }
)
_PSYCHOMETRIC_FIELDS = frozenset(
    {
        "status_code",
        "artifact_id",
        "model_contract_version",
        "scale_code",
        "estimate",
        "standard_error",
        "engine_version",
        "artifact_digest_sha256",
        "evidence_ids",
    }
)
_JUDGE_FIELDS = frozenset(
    {
        "status_code",
        "trace_id",
        "operation_code",
        "policy_version",
        "prompt_sha256",
        "verdict_code",
        "confidence",
        "rationale",
        "evidence_ids",
    }
)
_CLAIM_FIELDS = frozenset(
    {"claim_id", "claim_text", "claim_type_code", "evidence_ids"}
)


class EventIntelligenceValidationError(ValueError):
    """Raised when an Event Intelligence Dossier violates its public contract."""


def _object(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise EventIntelligenceValidationError(f"{field} must be an object")
    return value


def _exact(value: Mapping[str, Any], expected: frozenset[str], field: str) -> None:
    actual = frozenset(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        raise EventIntelligenceValidationError(
            f"{field} is missing fields: {', '.join(missing)}"
        )
    if extra:
        raise EventIntelligenceValidationError(
            f"{field} has unexpected fields: {', '.join(extra)}"
        )


def _text(value: object, field: str, *, maximum: int = 4_000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EventIntelligenceValidationError(f"{field} must be a non-empty string")
    if len(value) > maximum:
        raise EventIntelligenceValidationError(
            f"{field} must be at most {maximum} characters"
        )
    return value


def _timestamp(value: object, field: str, *, optional: bool = False) -> datetime | None:
    if value is None and optional:
        return None
    text = _text(value, field, maximum=64)
    if _RFC3339.fullmatch(text) is None:
        raise EventIntelligenceValidationError(
            f"{field} must be an RFC 3339 timestamp with a UTC offset (ISO-8601)"
        )
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EventIntelligenceValidationError(
            f"{field} must be an ISO-8601 timestamp"
        ) from exc
    return parsed


def _digest(value: object, field: str) -> str:
    text = _text(value, field, maximum=64)
    if _SHA256.fullmatch(text) is None:
        raise EventIntelligenceValidationError(
            f"{field} must be a lowercase SHA-256 digest"
        )
    return text


def _number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EventIntelligenceValidationError(f"{field} must be a number")
    if isinstance(value, int) and not -_MAX_SAFE_INTEGER <= value <= _MAX_SAFE_INTEGER:
        raise EventIntelligenceValidationError(
            f"{field} must be representable as an IEEE-754 safe integer"
        )
    normalized = float(value)
    if not math.isfinite(normalized):
        raise EventIntelligenceValidationError(f"{field} must be finite")
    return normalized


def _probability(value: object, field: str) -> float:
    normalized = _number(value, field)
    if not 0.0 <= normalized <= 1.0:
        raise EventIntelligenceValidationError(f"{field} must be between 0.0 and 1.0")
    return normalized


def _array(value: object, field: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise EventIntelligenceValidationError(f"{field} must be an array")
    return value


def _string_array(value: object, field: str) -> tuple[str, ...]:
    strings = tuple(
        _text(item, f"{field}[{index}]", maximum=256)
        for index, item in enumerate(_array(value, field))
    )
    if not strings:
        raise EventIntelligenceValidationError(f"{field} must not be empty")
    if len(strings) != len(set(strings)):
        raise EventIntelligenceValidationError(f"{field} must contain unique values")
    return strings


def _ontology(value: object, field: str) -> tuple[str, str]:
    item = _object(value, field)
    _exact(item, _ONTOLOGY_FIELDS, field)
    iri = _text(item["term_iri"], f"{field}.term_iri", maximum=1_024)
    if not iri.startswith(("https://", "http://", "urn:")):
        raise EventIntelligenceValidationError(
            f"{field}.term_iri must be an absolute IRI"
        )
    _text(item["preferred_label"], f"{field}.preferred_label", maximum=256)
    _text(item["vocabulary_version"], f"{field}.vocabulary_version", maximum=128)
    role = _text(item["semantic_role_code"], f"{field}.semantic_role_code", maximum=128)
    return iri, role


def _evidence_ids(value: object, field: str, known: set[str]) -> tuple[str, ...]:
    identifiers = _string_array(value, field)
    unknown = sorted(set(identifiers) - known)
    if unknown:
        raise EventIntelligenceValidationError(
            f"{field} references unknown evidence ids: {', '.join(unknown)}"
        )
    return identifiers


def _relevance(value: object, field: str, known: set[str]) -> None:
    item = _object(value, field)
    _exact(item, _RELEVANCE_FIELDS, field)
    _text(item["method_code"], f"{field}.method_code", maximum=128)
    _text(item["method_version"], f"{field}.method_version", maximum=128)
    authority = _text(item["authority_system"], f"{field}.authority_system", maximum=128)
    if authority not in _SOURCE_SYSTEMS:
        raise EventIntelligenceValidationError(
            f"{field}.authority_system is not supported"
        )
    estimate = _probability(item["estimate"], f"{field}.estimate")
    lower = _probability(item["uncertainty_lower"], f"{field}.uncertainty_lower")
    upper = _probability(item["uncertainty_upper"], f"{field}.uncertainty_upper")
    if not lower <= estimate <= upper:
        raise EventIntelligenceValidationError(
            f"{field} uncertainty must contain the estimate"
        )
    _evidence_ids(item["evidence_ids"], f"{field}.evidence_ids", known)


def _unavailable_or(
    value: object,
    field: str,
    expected: frozenset[str],
) -> Mapping[str, Any] | None:
    item = _object(value, field)
    status = item.get("status_code")
    if status == CHANNEL_UNAVAILABLE:
        _exact(item, frozenset({"status_code"}), field)
        return None
    if status != CHANNEL_AVAILABLE:
        raise EventIntelligenceValidationError(
            f"{field}.status_code must be available or unavailable"
        )
    _exact(item, expected, field)
    return item


def _validate_temporal(root: Mapping[str, Any]) -> tuple[datetime, datetime]:
    item = _object(root["temporal_context"], "temporal_context")
    _exact(item, _TEMPORAL_FIELDS, "temporal_context")
    event_start = _timestamp(item["event_start"], "temporal_context.event_start")
    event_end = _timestamp(
        item["event_end"], "temporal_context.event_end", optional=True
    )
    assertion = _timestamp(item["assertion_time"], "temporal_context.assertion_time")
    document = _timestamp(item["document_time"], "temporal_context.document_time")
    available = _timestamp(item["available_time"], "temporal_context.available_time")
    cutoff = _timestamp(item["knowledge_cutoff"], "temporal_context.knowledge_cutoff")
    assert event_start is not None and assertion is not None and document is not None
    assert available is not None and cutoff is not None
    if event_end is not None and event_end < event_start:
        raise EventIntelligenceValidationError(
            "temporal_context.event_end must not precede event_start"
        )
    if assertion > available:
        raise EventIntelligenceValidationError(
            "temporal_context.assertion_time must not follow available_time"
        )
    if document > available:
        raise EventIntelligenceValidationError(
            "temporal_context.document_time must not follow available_time"
        )
    if available > cutoff:
        raise EventIntelligenceValidationError(
            "temporal_context.available_time must not follow knowledge_cutoff"
        )
    return available, cutoff


def _validate_evidence(
    root: Mapping[str, Any], cutoff: datetime
) -> set[str]:
    identifiers: set[str] = set()
    for index, raw in enumerate(_array(root["evidence"], "evidence")):
        field = f"evidence[{index}]"
        item = _object(raw, field)
        _exact(item, _EVIDENCE_FIELDS, field)
        evidence_id = _text(item["evidence_id"], f"{field}.evidence_id", maximum=256)
        if evidence_id in identifiers:
            raise EventIntelligenceValidationError("evidence ids must be unique")
        identifiers.add(evidence_id)
        source = _text(item["source_system"], f"{field}.source_system", maximum=128)
        if source not in _SOURCE_SYSTEMS:
            raise EventIntelligenceValidationError(
                f"{field}.source_system is not supported"
            )
        _text(item["source_uri"], f"{field}.source_uri", maximum=2_048)
        _digest(item["content_sha256"], f"{field}.content_sha256")
        available = _timestamp(item["available_time"], f"{field}.available_time")
        recorded = _timestamp(item["recorded_time"], f"{field}.recorded_time")
        assert available is not None and recorded is not None
        if available > cutoff:
            raise EventIntelligenceValidationError(
                f"{field} is available after the knowledge cutoff"
            )
        if recorded < available:
            raise EventIntelligenceValidationError(
                f"{field}.recorded_time must not precede available_time"
            )
    if not identifiers:
        raise EventIntelligenceValidationError("evidence must not be empty")
    return identifiers


def _validate_ontology(root: Mapping[str, Any]) -> None:
    seen: set[tuple[str, str]] = set()
    for index, raw in enumerate(_array(root["event_ontology"], "event_ontology")):
        identity = _ontology(raw, f"event_ontology[{index}]")
        if identity in seen:
            raise EventIntelligenceValidationError(
                "ontology references must be unique by term and semantic role"
            )
        seen.add(identity)
    if not seen:
        raise EventIntelligenceValidationError("event_ontology must not be empty")


def _validate_graph(root: Mapping[str, Any], known: set[str]) -> None:
    graph = _object(root["knowledge_graph"], "knowledge_graph")
    _exact(graph, _GRAPH_FIELDS, "knowledge_graph")
    if graph["status_code"] != CHANNEL_AVAILABLE:
        raise EventIntelligenceValidationError("knowledge_graph must be available")

    node_ids: set[str] = set()
    for index, raw in enumerate(_array(graph["nodes"], "knowledge_graph.nodes")):
        field = f"knowledge_graph.nodes[{index}]"
        node = _object(raw, field)
        _exact(node, _NODE_FIELDS, field)
        node_id = _text(node["node_id"], f"{field}.node_id", maximum=256)
        if node_id in node_ids:
            raise EventIntelligenceValidationError("knowledge graph node ids must be unique")
        node_ids.add(node_id)
        _text(node["node_type_code"], f"{field}.node_type_code", maximum=128)
        _text(node["label"], f"{field}.label", maximum=512)
        _relevance(node["relevance"], f"{field}.relevance", known)
        _ontology(node["ontology"], f"{field}.ontology")
        _evidence_ids(node["evidence_ids"], f"{field}.evidence_ids", known)
    if not node_ids:
        raise EventIntelligenceValidationError("knowledge_graph.nodes must not be empty")
    if root["event_id"] not in node_ids:
        raise EventIntelligenceValidationError(
            "event_id must identify a knowledge graph node"
        )

    edge_ids: set[tuple[str, str, str]] = set()
    for index, raw in enumerate(_array(graph["edges"], "knowledge_graph.edges")):
        field = f"knowledge_graph.edges[{index}]"
        edge = _object(raw, field)
        _exact(edge, _EDGE_FIELDS, field)
        source = _text(edge["source_node_id"], f"{field}.source_node_id", maximum=256)
        target = _text(edge["target_node_id"], f"{field}.target_node_id", maximum=256)
        edge_type = _text(edge["edge_type_code"], f"{field}.edge_type_code", maximum=128)
        if source not in node_ids or target not in node_ids:
            raise EventIntelligenceValidationError(
                f"{field} must reference existing graph nodes"
            )
        identity = (source, target, edge_type)
        if identity in edge_ids:
            raise EventIntelligenceValidationError("knowledge graph edges must be unique")
        edge_ids.add(identity)
        _ontology(edge["ontology"], f"{field}.ontology")
        _evidence_ids(edge["evidence_ids"], f"{field}.evidence_ids", known)


def _validate_tepp(
    root: Mapping[str, Any], known: set[str], cutoff: datetime
) -> None:
    item = _unavailable_or(root["tepp"], "tepp", _TEPP_FIELDS)
    if item is None:
        return
    _text(item["remote_run_id"], "tepp.remote_run_id", maximum=256)
    _text(item["artifact_id"], "tepp.artifact_id", maximum=256)
    snapshot = _text(item["snapshot_id"], "tepp.snapshot_id", maximum=256)
    if snapshot != root["source_snapshot_id"]:
        raise EventIntelligenceValidationError(
            "tepp.snapshot_id must match source_snapshot_id"
        )
    tepp_cutoff = _timestamp(item["knowledge_cutoff"], "tepp.knowledge_cutoff")
    assert tepp_cutoff is not None
    if tepp_cutoff != cutoff:
        raise EventIntelligenceValidationError(
            "tepp.knowledge_cutoff must match temporal_context.knowledge_cutoff"
        )
    _text(item["model_contract_version"], "tepp.model_contract_version", maximum=128)
    _text(item["engine_version"], "tepp.engine_version", maximum=128)
    _digest(item["artifact_digest_sha256"], "tepp.artifact_digest_sha256")
    for index, value in enumerate(_array(item["topic_relevance"], "tepp.topic_relevance")):
        _relevance(value, f"tepp.topic_relevance[{index}]", known)
    _evidence_ids(item["evidence_ids"], "tepp.evidence_ids", known)


def _validate_psychometric(root: Mapping[str, Any], known: set[str]) -> None:
    item = _unavailable_or(
        root["fast_mlsirm"], "fast_mlsirm", _PSYCHOMETRIC_FIELDS
    )
    if item is None:
        return
    for name in ("artifact_id", "model_contract_version", "scale_code", "engine_version"):
        _text(item[name], f"fast_mlsirm.{name}", maximum=256)
    _number(item["estimate"], "fast_mlsirm.estimate")
    standard_error = _number(item["standard_error"], "fast_mlsirm.standard_error")
    if standard_error < 0:
        raise EventIntelligenceValidationError(
            "fast_mlsirm.standard_error must not be negative"
        )
    _digest(
        item["artifact_digest_sha256"], "fast_mlsirm.artifact_digest_sha256"
    )
    _evidence_ids(item["evidence_ids"], "fast_mlsirm.evidence_ids", known)


def _validate_judge(root: Mapping[str, Any], known: set[str]) -> None:
    item = _unavailable_or(
        root["contextual_orchestrator"],
        "contextual_orchestrator",
        _JUDGE_FIELDS,
    )
    if item is None:
        return
    for name in ("trace_id", "operation_code", "policy_version"):
        _text(item[name], f"contextual_orchestrator.{name}", maximum=256)
    _digest(
        item["prompt_sha256"],
        "contextual_orchestrator.prompt_sha256",
    )
    verdict = _text(
        item["verdict_code"], "contextual_orchestrator.verdict_code", maximum=64
    )
    if verdict not in ALLOWED_ADJUDICATION_VERDICTS:
        raise EventIntelligenceValidationError(
            "contextual_orchestrator.verdict_code is not supported"
        )
    _probability(item["confidence"], "contextual_orchestrator.confidence")
    _text(item["rationale"], "contextual_orchestrator.rationale", maximum=2_000)
    _evidence_ids(
        item["evidence_ids"], "contextual_orchestrator.evidence_ids", known
    )


def _validate_claims(root: Mapping[str, Any], known: set[str]) -> None:
    claim_ids: set[str] = set()
    for index, raw in enumerate(_array(root["claims"], "claims")):
        field = f"claims[{index}]"
        item = _object(raw, field)
        _exact(item, _CLAIM_FIELDS, field)
        claim_id = _text(item["claim_id"], f"{field}.claim_id", maximum=256)
        if claim_id in claim_ids:
            raise EventIntelligenceValidationError("claim ids must be unique")
        claim_ids.add(claim_id)
        _text(item["claim_text"], f"{field}.claim_text", maximum=4_000)
        _text(item["claim_type_code"], f"{field}.claim_type_code", maximum=128)
        _evidence_ids(item["evidence_ids"], f"{field}.evidence_ids", known)


def _canonical_without_digest(payload: Mapping[str, Any]) -> str:
    value = dict(payload)
    value.pop("dossier_sha256", None)
    try:
        return rfc8785.dumps(value).decode("utf-8")
    except (TypeError, ValueError, rfc8785.CanonicalizationError) as exc:
        raise EventIntelligenceValidationError(
            "dossier contains a value that RFC 8785 cannot canonicalize"
        ) from exc


def _payload_digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_without_digest(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class EventIntelligenceDossier:
    """A validated, immutable Event Intelligence Dossier payload."""

    _payload: Mapping[str, Any]

    @property
    def contract_version(self) -> int:
        """Return the dossier contract version."""
        return int(self._payload["contract_version"])

    @property
    def event_id(self) -> str:
        """Return the event node identity."""
        return str(self._payload["event_id"])

    def dossier_sha256(self) -> str:
        """Return the canonical dossier digest."""
        return _payload_digest(self._payload)

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible payload including its digest."""
        result = deepcopy(dict(self._payload))
        result["dossier_sha256"] = self.dossier_sha256()
        return result

    def to_json(self) -> str:
        """Serialize the dossier as canonical UTF-8 JSON text."""
        try:
            return rfc8785.dumps(self.to_dict()).decode("utf-8")
        except (TypeError, ValueError, rfc8785.CanonicalizationError) as exc:
            raise EventIntelligenceValidationError(
                "dossier contains a value that RFC 8785 cannot canonicalize"
            ) from exc


def event_intelligence_dossier_from_dict(
    payload: object, *, require_digest: bool = True
) -> EventIntelligenceDossier:
    """Validate and detach one dossier mapping.

    When ``require_digest`` is false, callers may supply an undigested composer
    payload; any supplied digest must still be correct.  The returned dossier
    always emits the canonical digest.
    """
    root = _object(payload, "dossier")
    expected = (
        _ROOT_FIELDS
        if "dossier_sha256" in root
        else _ROOT_FIELDS - {"dossier_sha256"}
    )
    _exact(root, expected, "dossier")

    version = root["contract_version"]
    if isinstance(version, bool) or not isinstance(version, int):
        raise EventIntelligenceValidationError("contract_version must be an integer")
    if version != EVENT_INTELLIGENCE_CONTRACT_VERSION:
        raise EventIntelligenceValidationError("contract_version is not supported")
    for field in ("event_id", "event_title", "source_snapshot_id"):
        _text(root[field], field, maximum=256)

    _validate_ontology(root)
    _, cutoff = _validate_temporal(root)
    known = _validate_evidence(root, cutoff)
    _validate_graph(root, known)
    _validate_tepp(root, known, cutoff)
    _validate_psychometric(root, known)
    _validate_judge(root, known)
    _validate_claims(root, known)

    actual_digest = root.get("dossier_sha256")
    if actual_digest is not None:
        _digest(actual_digest, "dossier_sha256")
        if actual_digest != _payload_digest(root):
            raise EventIntelligenceValidationError(
                "dossier_sha256 does not match the canonical payload"
            )
    elif require_digest:
        raise EventIntelligenceValidationError("dossier is missing fields: dossier_sha256")

    detached = json.loads(
        json.dumps(root, ensure_ascii=False, allow_nan=False, sort_keys=True)
    )
    return EventIntelligenceDossier(detached)


__all__ = [
    "CHANNEL_AVAILABLE",
    "CHANNEL_UNAVAILABLE",
    "EVENT_INTELLIGENCE_CONTRACT_VERSION",
    "EventIntelligenceDossier",
    "EventIntelligenceValidationError",
    "event_intelligence_dossier_from_dict",
]
