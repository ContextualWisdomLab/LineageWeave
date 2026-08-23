"""Strict LineageWeave consumer for TEPP topic-lineage artifacts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
import hashlib
import json
from typing import Any
from uuid import UUID

TOPIC_LINEAGE_ARTIFACT_SCHEMA_VERSION = "tepp.trsl_topic_lineage.v1"
TOPIC_LINEAGE_MODEL_CONTRACT_VERSION = "trsl_tm_cpu_f64_v1"
TOPIC_LINEAGE_OUTPUT_PROFILE = "trsl_topic_lineage_v1"
TOPIC_LINEAGE_INFERENCE_STATUS = "fitted_topic_association_not_causation"
TOPIC_LINEAGE_ARTIFACT_BYTE_LIMIT = 256 * 1024
TOPIC_LINEAGE_EDGE_LIMIT = 100_000
_U64_MAXIMUM = 2**64 - 1
_ARTIFACT_FIELDS = frozenset(
    {
        "schema_version",
        "run_id",
        "snapshot_id",
        "knowledge_cutoff",
        "selected_seed",
        "iterations",
        "objective",
        "topic_count",
        "evidence_count",
        "connected_post_count",
        "lineage_count",
        "sequence_edges",
        "inference_status",
    }
)
_EDGE_FIELDS = frozenset(
    {
        "predecessor_document_id",
        "successor_document_id",
        "topic_index",
        "association_strength",
    }
)


class TopicLineageUnavailable(ValueError):
    """TEPP topic-lineage evidence was absent or violated its contract."""


def _text(value: Any, name: str, maximum: int = 256) -> str:
    """Return bounded non-empty text without control characters."""

    if not isinstance(value, str) or value != value.strip():
        raise TopicLineageUnavailable(f"{name} must be canonical text")
    if (
        not value
        or len(value.encode("utf-8")) > maximum
        or any(ord(character) < 0x20 or ord(character) == 0x7F for character in value)
    ):
        raise TopicLineageUnavailable(f"{name} is outside its bound")
    return value


def _u64(value: Any, name: str) -> int:
    """Return one unsigned 64-bit integer without accepting booleans."""

    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= _U64_MAXIMUM:
        raise TopicLineageUnavailable(f"{name} must be an unsigned 64-bit integer")
    return value


def _rfc3339_utc(value: Any, name: str) -> str:
    """Return one offset-aware timestamp in canonical UTC form."""

    raw = _text(value, name, 64)
    try:
        parsed = datetime.fromisoformat(raw[:-1] + "+00:00" if raw.endswith("Z") else raw)
    except ValueError as exc:
        raise TopicLineageUnavailable(f"{name} must be RFC 3339") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TopicLineageUnavailable(f"{name} must include an offset")
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _uuid(value: Any, name: str) -> str:
    """Return one lowercase canonical UUID."""

    raw = _text(value, name, 36)
    try:
        parsed = UUID(raw)
    except ValueError as exc:
        raise TopicLineageUnavailable(f"{name} must be a UUID") from exc
    if str(parsed) != raw:
        raise TopicLineageUnavailable(f"{name} must be a canonical UUID")
    return raw


def _json_object(value: Any, *, maximum_bytes: int) -> Mapping[str, Any]:
    """Decode one bounded JSON object or validate an in-memory mapping."""

    if isinstance(value, str):
        if len(value.encode("utf-8")) > maximum_bytes:
            raise TopicLineageUnavailable("topic-lineage JSON exceeds its byte limit")
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise TopicLineageUnavailable("topic-lineage JSON is invalid") from exc
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise TopicLineageUnavailable("topic-lineage value is not JSON") from exc
    if len(encoded) > maximum_bytes:
        raise TopicLineageUnavailable("topic-lineage JSON exceeds its byte limit")
    if not isinstance(value, Mapping):
        raise TopicLineageUnavailable("topic-lineage JSON must be an object")
    return value


def parse_topic_lineage_artifact(value: Any) -> dict[str, Any]:
    """Validate and canonicalize one exact TEPP topic-lineage artifact."""

    artifact = _json_object(value, maximum_bytes=TOPIC_LINEAGE_ARTIFACT_BYTE_LIMIT)
    if frozenset(artifact) != _ARTIFACT_FIELDS:
        raise TopicLineageUnavailable("topic-lineage artifact fields are invalid")
    schema_version = _text(artifact["schema_version"], "schema_version", 64)
    if schema_version != TOPIC_LINEAGE_ARTIFACT_SCHEMA_VERSION:
        raise TopicLineageUnavailable("topic-lineage artifact schema is unsupported")
    run_id = _text(artifact["run_id"], "run_id")
    snapshot_id = _text(artifact["snapshot_id"], "snapshot_id")
    knowledge_cutoff = _rfc3339_utc(artifact["knowledge_cutoff"], "knowledge_cutoff")
    selected_seed = _u64(artifact["selected_seed"], "selected_seed")
    iterations = _u64(artifact["iterations"], "iterations")
    if iterations == 0:
        raise TopicLineageUnavailable("iterations must be positive")
    objective = artifact["objective"]
    if isinstance(objective, bool) or not isinstance(objective, (int, float)):
        raise TopicLineageUnavailable("objective must be numeric")
    try:
        objective = float(objective)
    except OverflowError as exc:
        raise TopicLineageUnavailable("objective must be finite") from exc
    topic_count = _u64(artifact["topic_count"], "topic_count")
    evidence_count = _u64(artifact["evidence_count"], "evidence_count")
    connected_post_count = _u64(artifact["connected_post_count"], "connected_post_count")
    lineage_count = _u64(artifact["lineage_count"], "lineage_count")
    if topic_count < 2 or evidence_count < 2:
        raise TopicLineageUnavailable("topic and evidence counts must be at least two")
    if connected_post_count > evidence_count or lineage_count > topic_count:
        raise TopicLineageUnavailable("topic-lineage counts exceed their dimensions")
    raw_edges = artifact["sequence_edges"]
    if not isinstance(raw_edges, list) or len(raw_edges) > TOPIC_LINEAGE_EDGE_LIMIT:
        raise TopicLineageUnavailable("sequence_edges is outside its bound")
    pairs: set[tuple[str, str]] = set()
    connected: set[str] = set()
    lineages: set[int] = set()
    edges: list[dict[str, Any]] = []
    for raw_edge in raw_edges:
        if not isinstance(raw_edge, Mapping) or frozenset(raw_edge) != _EDGE_FIELDS:
            raise TopicLineageUnavailable("topic-lineage edge fields are invalid")
        predecessor = _uuid(raw_edge["predecessor_document_id"], "predecessor_document_id")
        successor = _uuid(raw_edge["successor_document_id"], "successor_document_id")
        topic_index = _u64(raw_edge["topic_index"], "topic_index")
        strength = raw_edge["association_strength"]
        if isinstance(strength, bool) or not isinstance(strength, (int, float)):
            raise TopicLineageUnavailable("association_strength must be numeric")
        try:
            strength = float(strength)
        except OverflowError as exc:
            raise TopicLineageUnavailable("association_strength must be finite") from exc
        pair = (predecessor, successor)
        if (
            predecessor == successor
            or topic_index >= topic_count
            or not 0.0 < strength <= 1.0
            or pair in pairs
        ):
            raise TopicLineageUnavailable("topic-lineage edge is invalid")
        pairs.add(pair)
        connected.update(pair)
        lineages.add(topic_index)
        edges.append(
            {
                "predecessor_document_id": predecessor,
                "successor_document_id": successor,
                "topic_index": topic_index,
                "association_strength": strength,
            }
        )
    inference_status = _text(artifact["inference_status"], "inference_status", 64)
    if inference_status != TOPIC_LINEAGE_INFERENCE_STATUS:
        raise TopicLineageUnavailable("topic-lineage inference status is unsupported")
    if connected_post_count != len(connected) or lineage_count != len(lineages):
        raise TopicLineageUnavailable("topic-lineage counts do not match the edges")
    return {
        "schema_version": schema_version,
        "run_id": run_id,
        "snapshot_id": snapshot_id,
        "knowledge_cutoff": knowledge_cutoff,
        "selected_seed": selected_seed,
        "iterations": iterations,
        "objective": objective,
        "topic_count": topic_count,
        "evidence_count": evidence_count,
        "connected_post_count": connected_post_count,
        "lineage_count": lineage_count,
        "sequence_edges": edges,
        "inference_status": inference_status,
    }


def topic_lineage_artifact_sha256(value: Any) -> str:
    """Return TEPP's SHA-256 over canonical artifact field order."""

    artifact = parse_topic_lineage_artifact(value)
    wire = json.dumps(artifact, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(wire).hexdigest()


def parse_topic_lineage_envelope(
    value: Any,
    *,
    expected_snapshot_id: str | None = None,
    expected_knowledge_cutoff: str | None = None,
    expected_remote_run_id: str | None = None,
) -> dict[str, Any]:
    """Validate a completed, digest-bound transport envelope and its artifact."""

    envelope = _json_object(value, maximum_bytes=TOPIC_LINEAGE_ARTIFACT_BYTE_LIMIT * 2)
    if envelope.get("status") not in {"completed", "succeeded"}:
        raise TopicLineageUnavailable("topic-lineage run is not completed")
    remote_run_id = envelope.get("analysis_run_id") or envelope.get("run_id")
    remote_run_id = _text(remote_run_id, "remote_run_id")
    artifact = parse_topic_lineage_artifact(envelope.get("result"))
    if envelope.get("result_schema_version") != TOPIC_LINEAGE_ARTIFACT_SCHEMA_VERSION:
        raise TopicLineageUnavailable("topic-lineage result schema is unsupported")
    digest = _text(envelope.get("result_sha256"), "result_sha256", 64)
    if digest != topic_lineage_artifact_sha256(artifact):
        raise TopicLineageUnavailable("topic-lineage result digest does not match")
    if artifact["run_id"] != remote_run_id:
        raise TopicLineageUnavailable("topic-lineage run identity does not match")
    if expected_remote_run_id is not None and remote_run_id != expected_remote_run_id:
        raise TopicLineageUnavailable("topic-lineage persisted run identity does not match")
    if expected_snapshot_id is not None and artifact["snapshot_id"] != expected_snapshot_id:
        raise TopicLineageUnavailable("topic-lineage snapshot identity does not match")
    if expected_knowledge_cutoff is not None and artifact["knowledge_cutoff"] != _rfc3339_utc(
        expected_knowledge_cutoff, "expected_knowledge_cutoff"
    ):
        raise TopicLineageUnavailable("topic-lineage knowledge cutoff does not match")
    return artifact


def project_topic_lineage_projection(
    artifacts: Sequence[Mapping[str, Any]], visible_post_ids: Sequence[str]
) -> dict[str, Any]:
    """Filter validated TEPP edges to one authorized Project History post set."""

    visible = set(visible_post_ids)
    connected: set[str] = set()
    lineages: set[tuple[str, int]] = set()
    edges: list[dict[str, Any]] = []
    contributing_runs: set[str] = set()
    for value in artifacts:
        artifact = parse_topic_lineage_artifact(value)
        for edge in artifact["sequence_edges"]:
            predecessor = edge["predecessor_document_id"]
            successor = edge["successor_document_id"]
            if predecessor not in visible or successor not in visible:
                continue
            connected.update((predecessor, successor))
            lineages.add((artifact["run_id"], edge["topic_index"]))
            contributing_runs.add(artifact["run_id"])
            edges.append(
                {
                    "artifact_run_id": artifact["run_id"],
                    "predecessor_post_id": predecessor,
                    "successor_post_id": successor,
                    "topic_index": edge["topic_index"],
                    "association_strength": edge["association_strength"],
                }
            )
    edges.sort(
        key=lambda edge: (
            edge["predecessor_post_id"],
            edge["successor_post_id"],
            edge["artifact_run_id"],
            edge["topic_index"],
        )
    )
    available = bool(edges)
    return {
        "status": "validated" if available else "unavailable",
        "schema_version": TOPIC_LINEAGE_ARTIFACT_SCHEMA_VERSION if available else None,
        "inference_status": TOPIC_LINEAGE_INFERENCE_STATUS if available else None,
        "artifact_count": len(contributing_runs),
        "connected_post_count": len(connected) if available else None,
        "lineage_count": len(lineages) if available else None,
        "sequence_edges": edges,
    }
