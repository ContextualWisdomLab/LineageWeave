"""Strict transport contract for externally computed topic-context influence.

LineageWeave only validates and moves evidence.  TEPP owns temporal topic
posterior evidence and fast-mlsirm owns the Rust case-deletion computation
defined by ADR 0210.
"""

from __future__ import annotations

import hashlib
import base64
import binascii
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from .http_client import post_json

REQUEST_SCHEMA_VERSION = "lineageweave.topic_context_influence_request.v1"
RESULT_SCHEMA_VERSION = "fast_mlsirm.topic_context_influence.v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_REVISION = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
_DIMENSIONS = frozenset({"business_unit", "process_unit", "team", "person"})


class TopicInfluenceNotAvailable(RuntimeError):
    """Raised when no fast-mlsirm topic-influence transport is configured."""


class TopicInfluenceInvalidResponse(ValueError):
    """Raised when a result is incomplete or not bound to its request."""


def _json_artifact_bytes(value: object) -> bytes:
    """Encode one LineageWeave-owned request artifact for exact transport."""
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


@dataclass(frozen=True)
class TopicInfluenceRequest:
    """One immutable TEPP posterior and multiple-membership evidence request."""

    payload: dict[str, Any]
    artifact_bytes: bytes

    @property
    def request_sha256(self) -> str:
        """Return the content identity of the exact producer input."""
        return hashlib.sha256(self.artifact_bytes).hexdigest()

    @property
    def membership_fingerprint_sha256(self) -> str:
        """Return the declared source-derived membership design identity."""
        return str(self.payload["membership_fingerprint_sha256"])

    def to_json(self) -> dict[str, Any]:
        """Transport exact owned bytes and the opaque identity the producer echoes."""
        return {
            "request_sha256": self.request_sha256,
            "request_base64": base64.b64encode(self.artifact_bytes).decode("ascii"),
        }


@dataclass(frozen=True)
class TopicInfluenceResult:
    """Validated fast-mlsirm result ready for exact persistence."""

    payload: dict[str, Any]


def build_topic_influence_request(
    *,
    tepp_run: dict[str, Any],
    topics: list[int],
    observations: list[dict[str, Any]],
) -> TopicInfluenceRequest:
    """Build and validate one request without performing numerical work."""
    required_run = {
        "tepp_run_id",
        "tepp_artifact_sha256",
        "source_snapshot_sha256",
        "knowledge_cutoff",
        "posterior_draw_set_id",
        "posterior_draw_count",
        "coordinate_kind_code",
        "topic_model_run_id",
    }
    if set(tepp_run) != required_run or not _SHA256.fullmatch(
        str(tepp_run.get("tepp_artifact_sha256", ""))
    ) or not _SHA256.fullmatch(str(tepp_run.get("source_snapshot_sha256", ""))):
        raise ValueError("TEPP run evidence is incomplete")
    if (
        not isinstance(tepp_run["posterior_draw_count"], int)
        or isinstance(tepp_run["posterior_draw_count"], bool)
        or tepp_run["posterior_draw_count"] <= 0
        or tepp_run["coordinate_kind_code"]
        not in {"logistic_normal_coordinate", "plausible_value"}
    ):
        raise ValueError("TEPP posterior contract is invalid")
    if not topics or any(type(topic) is not int or topic < 0 for topic in topics):
        raise ValueError("topic identities must be non-empty non-negative integers")
    if len(set(topics)) != len(topics):
        raise ValueError("topic identities must be unique")

    if not observations:
        raise ValueError("topic observations must be non-empty")
    membership_material: list[dict[str, Any]] = []
    observed_dimensions: set[str] = set()
    seen_membership_ids: set[str] = set()
    seen_posts: set[str] = set()
    for observation in observations:
        if set(observation) != {"post_id", "event_time", "coordinates", "memberships"}:
            raise ValueError("topic observation shape is invalid")
        post_id = observation["post_id"]
        if not isinstance(post_id, str) or not post_id.strip() or post_id in seen_posts:
            raise ValueError("topic observation post identity is invalid")
        seen_posts.add(post_id)
        coordinates = observation["coordinates"]
        memberships = observation["memberships"]
        if (
            not isinstance(coordinates, list)
            or not coordinates
            or not isinstance(memberships, list)
            or not memberships
        ):
            raise ValueError("topic observation requires coordinates and memberships")
        expected_coordinates = {
            (topic, draw)
            for topic in topics
            for draw in range(tepp_run["posterior_draw_count"])
        }
        actual_coordinates: set[tuple[int, int]] = set()
        for coordinate in coordinates:
            if set(coordinate) != {"topic_index", "posterior_draw_ordinal", "value"}:
                raise ValueError("topic coordinate shape is invalid")
            key = (coordinate["topic_index"], coordinate["posterior_draw_ordinal"])
            value = coordinate["value"]
            if (
                key in actual_coordinates
                or type(value) not in {int, float}
                or not math.isfinite(value)
            ):
                raise ValueError("topic coordinate is duplicate or non-finite")
            actual_coordinates.add(key)
        if actual_coordinates != expected_coordinates:
            raise ValueError("topic coordinates are incomplete")
        for membership in memberships:
            if set(membership) != {
                "membership_id",
                "dimension_code",
                "context_id",
                "weight",
                "valid_from",
                "valid_to",
                "evidence_sha256",
                "provenance_assertion_id",
            }:
                raise ValueError("topic membership shape is invalid")
            membership_id = membership["membership_id"]
            dimension = membership["dimension_code"]
            context_id = membership["context_id"]
            weight = membership["weight"]
            if (
                not isinstance(membership_id, str)
                or not membership_id.strip()
                or membership_id in seen_membership_ids
                or dimension not in _DIMENSIONS
                or not isinstance(context_id, str)
                or not context_id.strip()
                or type(weight) not in {int, float}
                or not math.isfinite(weight)
                or weight <= 0
                or not _SHA256.fullmatch(str(membership["evidence_sha256"]))
            ):
                raise ValueError("topic membership evidence is invalid")
            seen_membership_ids.add(membership_id)
            observed_dimensions.add(dimension)
            membership_material.append(
                {"post_id": post_id, **membership}
            )
    if observed_dimensions != _DIMENSIONS:
        raise ValueError("topic run requires evidence across all four context dimensions")
    membership_material.sort(
        key=lambda row: (
            row["post_id"],
            row["dimension_code"],
            row["context_id"],
            row["membership_id"],
        )
    )
    membership_artifact_bytes = _json_artifact_bytes(membership_material)
    payload = {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "requested_result_schema_version": RESULT_SCHEMA_VERSION,
        "tepp_run": tepp_run,
        "topic_indices": sorted(topics),
        "observations": observations,
        "membership_artifact_base64": base64.b64encode(
            membership_artifact_bytes
        ).decode("ascii"),
        "membership_fingerprint_sha256": hashlib.sha256(
            membership_artifact_bytes
        ).hexdigest(),
    }
    return TopicInfluenceRequest(payload, _json_artifact_bytes(payload))


def validate_topic_influence_result(
    request: TopicInfluenceRequest, response: object
) -> TopicInfluenceResult:
    """Admit one exact, complete, converged, digest-bound producer result."""
    required = {
        "schema_version",
        "request_sha256",
        "tepp_run_id",
        "source_snapshot_sha256",
        "knowledge_cutoff",
        "membership_fingerprint_sha256",
        "producer_version",
        "code_revision",
        "compute_backend_code",
        "precision_code",
        "posterior_draw_coverage",
        "convergence_status_code",
        "identification_status_code",
        "parity_status_code",
        "influences",
    }
    if not isinstance(response, dict) or set(response) != {"artifact_sha256", "artifact_base64"}:
        raise TopicInfluenceInvalidResponse("topic influence result shape is invalid")
    artifact_sha256 = response["artifact_sha256"]
    encoded = response["artifact_base64"]
    if not _SHA256.fullmatch(str(artifact_sha256)) or not isinstance(encoded, str):
        raise TopicInfluenceInvalidResponse("topic influence artifact envelope is invalid")
    try:
        artifact_bytes = base64.b64decode(encoded, validate=True)
    except binascii.Error as exc:
        raise TopicInfluenceInvalidResponse("topic influence artifact bytes are invalid") from exc
    if hashlib.sha256(artifact_bytes).hexdigest() != artifact_sha256:
        raise TopicInfluenceInvalidResponse("topic influence artifact digest is invalid")
    try:
        decoded = json.loads(artifact_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TopicInfluenceInvalidResponse("topic influence artifact bytes are invalid") from exc
    if not isinstance(decoded, dict) or set(decoded) != required:
        raise TopicInfluenceInvalidResponse("topic influence result shape is invalid")
    response = decoded
    tepp = request.payload["tepp_run"]
    if (
        response["schema_version"] != RESULT_SCHEMA_VERSION
        or response["request_sha256"] != request.request_sha256
        or response["tepp_run_id"] != tepp["tepp_run_id"]
        or response["source_snapshot_sha256"] != tepp["source_snapshot_sha256"]
        or response["knowledge_cutoff"] != tepp["knowledge_cutoff"]
        or response["membership_fingerprint_sha256"]
        != request.membership_fingerprint_sha256
        or response["posterior_draw_coverage"] != tepp["posterior_draw_count"]
        or response["convergence_status_code"] != "converged"
        or response["identification_status_code"] != "identified"
        or response["parity_status_code"] != "passed"
        or response["compute_backend_code"] not in {"rust_cpu", "rust_gpu"}
        or response["precision_code"] not in {"f64", "f32"}
        or not _REVISION.fullmatch(str(response["code_revision"]))
        or not isinstance(response["producer_version"], str)
        or not response["producer_version"].strip()
    ):
        raise TopicInfluenceInvalidResponse("topic influence result binding is invalid")
    expected = {
        (observation["post_id"], membership["membership_id"], topic)
        for observation in request.payload["observations"]
        for membership in observation["memberships"]
        for topic in request.payload["topic_indices"]
    }
    actual: set[tuple[str, str, int]] = set()
    influences = response["influences"]
    if not isinstance(influences, list):
        raise TopicInfluenceInvalidResponse("topic influence rows are invalid")
    for influence in influences:
        if not isinstance(influence, dict) or set(influence) != {
            "post_id",
            "membership_id",
            "topic_index",
            "influence_value",
            "uncertainty_method_code",
            "uncertainty_lower_value",
            "uncertainty_upper_value",
            "diagnostic_status_code",
        }:
            raise TopicInfluenceInvalidResponse("topic influence row shape is invalid")
        key = (influence["post_id"], influence["membership_id"], influence["topic_index"])
        values = (
            influence["influence_value"],
            influence["uncertainty_lower_value"],
            influence["uncertainty_upper_value"],
        )
        if (
            key in actual
            or any(type(value) not in {int, float} or not math.isfinite(value) for value in values)
            or values[0] < 0
            or values[1] < 0
            or values[2] < values[1]
            or influence["diagnostic_status_code"] != "accepted"
            or not isinstance(influence["uncertainty_method_code"], str)
            or not influence["uncertainty_method_code"].strip()
        ):
            raise TopicInfluenceInvalidResponse("topic influence row evidence is invalid")
        actual.add(key)
    if actual != expected:
        raise TopicInfluenceInvalidResponse("topic influence result is incomplete")
    return TopicInfluenceResult({**response, "artifact_sha256": artifact_sha256})


class TopicInfluenceClient:
    """Submit one request to a configured fast-mlsirm service transport."""

    available = True

    def __init__(
        self,
        transport: Callable[[dict[str, Any]], object],
        *,
        lease_timeout_seconds: int,
    ) -> None:
        if type(lease_timeout_seconds) is not int or lease_timeout_seconds <= 0:
            raise ValueError("lease_timeout_seconds must be a positive integer")
        self._transport = transport
        self.lease_timeout_seconds = lease_timeout_seconds

    def estimate(self, request: TopicInfluenceRequest) -> TopicInfluenceResult:
        """Return only a request-bound, complete result envelope."""
        return validate_topic_influence_result(request, self._transport(request.to_json()))


class HttpTopicInfluenceClient(TopicInfluenceClient):
    """Use the owner service's versioned topic-influence endpoint."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float,
        lease_timeout_seconds: int,
    ) -> None:
        if not base_url.strip():
            raise TopicInfluenceNotAvailable("fast-mlsirm topic influence is unavailable")
        if (
            type(timeout) not in {int, float}
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ValueError("timeout must be a positive finite number")
        url = f"{base_url.rstrip('/')}/v1/topic-context-influence"
        super().__init__(
            lambda payload: post_json(
                url,
                payload,
                headers={"authorization": f"Bearer {api_key}"} if api_key else {},
                timeout=timeout,
                service_peer_name="fast-mlsirm",
            ),
            lease_timeout_seconds=lease_timeout_seconds,
        )
