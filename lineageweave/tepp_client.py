"""Adapter for TEPP's published "modular consumer" contract.

`TEPP <https://github.com/ContextualWisdomLab/TEPP>`_ (Temporal Event
Psychometrics Platform) is consumed here exactly the way its own
``docs/connectors/naruon-artifact-consumer.md`` specifies for any external
service: submit a versioned ``AnalysisRunRequest``, never read TEPP's
database tables directly, and never present this repo's own heuristic
lineage scores as TEPP's calibrated psychometric measurement (they answer
different questions -- see docs/lineage-bi-research-notes.md).

TEPP publishes an accepted-run contract and a distinct cutoff-safe temporal
context contract. This client builds the exact wire shapes TEPP has published
(``schemas/analysis_run_request_v1.json``) so wiring in a real transport is
a one-line change (:meth:`TeppClient.__init__`'s ``transport`` argument) once
that endpoint exists, instead of a redesign.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any


class TeppNotAvailable(RuntimeError):
    """Raised by the default transport: TEPP has no live REST API yet."""


class TeppInvalidResponse(ValueError):
    """Raised when TEPP returns a status payload outside its v1 contract."""


def _no_transport(request: dict[str, Any]) -> dict[str, Any]:
    """Implement the _no_transport operation for this channel."""
    raise TeppNotAvailable(
        "TEPP has no live HTTP endpoint yet (Rust-crate-only as of this writing). "
        "Pass a transport= callable to TeppClient once one exists, or consume TEPP "
        "as a Rust crate directly per its own docs/API_CONTRACT.md."
    )


def _no_status_transport(remote_run_id: str) -> dict[str, Any]:
    """Refuse status reads until a provider-owned read transport is supplied."""
    raise TeppNotAvailable(f"TEPP status transport unavailable for {remote_run_id!r}")


@dataclass(frozen=True)
class AnalysisRunRequest:
    """Mirrors TEPP's ``schemas/analysis_run_request_v1.json`` exactly.

    ``additionalProperties: false`` in that schema -- this dataclass has no
    fields beyond the seven TEPP requires, on purpose.
    """

    idempotency_key: str
    tenant_workspace_id: str
    snapshot_id: str
    knowledge_cutoff: str
    model_contract_version: str
    output_profile: str
    contract_version: int = 1

    def to_json(self) -> dict[str, Any]:
        """Serialize the accepted TEPP result into its wire representation."""
        return {
            "contract_version": self.contract_version,
            "idempotency_key": self.idempotency_key,
            "tenant_workspace_id": self.tenant_workspace_id,
            "snapshot_id": self.snapshot_id,
            "knowledge_cutoff": self.knowledge_cutoff,
            "model_contract_version": self.model_contract_version,
            "output_profile": self.output_profile,
        }


@dataclass(frozen=True)
class TemporalContextEvent:
    """One opaque event in TEPP's temporal-context v1 request."""

    event_id: str
    source_post_id: str
    event_type_code: str
    event_label: str
    event_time: str
    available_time: str
    project_reference: str | None
    actor_references: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        """Serialize this temporal event to TEPP's published request shape."""
        return {
            "event_id": self.event_id,
            "source_post_id": self.source_post_id,
            "event_type_code": self.event_type_code,
            "event_label": self.event_label,
            "event_time": self.event_time,
            "available_time": self.available_time,
            "project_reference": self.project_reference,
            "actor_references": list(self.actor_references),
        }


@dataclass(frozen=True)
class TemporalContextRequest:
    """TEPP's cutoff-safe LineageWeave temporal-context v1 request."""

    knowledge_cutoff: str
    subject_post_id: str
    events: tuple[TemporalContextEvent, ...]
    contract_version: int = 1
    consumer_code: str = "lineageweave"

    def to_json(self) -> dict[str, Any]:
        """Serialize this cutoff-safe temporal-context request for TEPP."""
        return {
            "contract_version": self.contract_version,
            "consumer_code": self.consumer_code,
            "knowledge_cutoff": self.knowledge_cutoff,
            "subject_post_id": self.subject_post_id,
            "events": [event.to_json() for event in self.events],
        }


class TeppClient:
    """Submits :class:`AnalysisRunRequest` through a pluggable transport.

    The default transport always raises :class:`TeppNotAvailable` -- this
    class exists so the rest of LineageWeave can be written against a
    stable interface today, and gains a real TEPP integration by supplying
    a ``transport`` (an HTTP POST to TEPP's future ``/v1/analysis-runs``, or
    an in-process call into the ``tepp_api`` Rust crate via FFI) without
    touching any other module.
    """

    def __init__(
        self,
        transport: Callable[[dict[str, Any]], dict[str, Any]] = _no_transport,
        *,
        temporal_transport: Callable[[dict[str, Any]], dict[str, Any]] = _no_transport,
        status_transport: Callable[[str], dict[str, Any]] = _no_status_transport,
    ) -> None:
        self._transport = transport
        self._temporal_transport = temporal_transport
        self._status_transport = status_transport

    def submit_analysis_run(self, request: AnalysisRunRequest) -> dict[str, Any]:
        """Submit a request; returns TEPP's ``AnalysisRunAccepted`` envelope."""
        return self._transport(request.to_json())

    def read_analysis_run_status(
        self, remote_run_id: str, request: AnalysisRunRequest
    ) -> dict[str, Any]:
        """Read and validate TEPP's request-bound status/result v1 payload."""
        response = self._status_transport(remote_run_id)
        if not _valid_analysis_run_status(remote_run_id, request, response):
            raise TeppInvalidResponse("TEPP analysis-run status response was invalid")
        return response

    def temporal_context(self, request: TemporalContextRequest) -> dict[str, Any]:
        """Return TEPP-owned ordering; callers must validate its claim boundary."""
        response = self._temporal_transport(request.to_json())
        if not _valid_temporal_response(request, response):
            raise TeppNotAvailable("TEPP temporal-context response was invalid")
        return response


_SHA256 = re.compile(r"[0-9a-f]{64}")
_FAILURE_CODE = re.compile(r"[a-z][a-z0-9_]{0,63}")


def _nonempty(value: object) -> bool:
    """Return whether a wire string contains non-whitespace text."""
    return (
        isinstance(value, str)
        and bool(value.strip())
        and not any(unicodedata.category(char).startswith("C") for char in value)
    )


def _rfc3339(value: object) -> bool:
    """Accept an RFC 3339 timestamp understood by the Python runtime."""
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _valid_analysis_run_status(
    remote_run_id: str, request: AnalysisRunRequest, response: object
) -> bool:
    """Validate TEPP v1 status and every terminal request binding."""
    if not isinstance(response, dict):
        return False
    try:
        encoded = json.dumps(
            response, separators=(",", ":"), ensure_ascii=False
        ).encode()
        if len(encoded) > 64 * 1024:
            return False
    except (TypeError, ValueError):
        return False
    status_keys = {
        "contract_version",
        "run_id",
        "run_state",
        "idempotency_key",
        "terminal_result",
    }
    if (
        set(response) != status_keys
        or response["contract_version"] != 1
        or response["run_id"] != remote_run_id
        or response["idempotency_key"] != request.idempotency_key
    ):
        return False
    state = response["run_state"]
    terminal = response["terminal_result"]
    if state in {"accepted", "running"}:
        return terminal is None
    if state not in {"succeeded", "failed"} or not isinstance(terminal, dict):
        return False
    terminal_keys = {
        "contract_version",
        "run_id",
        "run_state",
        "idempotency_key",
        "tenant_workspace_id",
        "snapshot_id",
        "knowledge_cutoff",
        "model_contract_version",
        "output_profile",
        "result_artifact_id",
        "result_sha256",
        "result_schema_version",
        "completed_at",
        "summary",
        "failure_code",
    }
    if (
        set(terminal) != terminal_keys
        or terminal["contract_version"] != 1
        or terminal["run_id"] != remote_run_id
        or terminal["run_state"] != state
        or terminal["idempotency_key"] != request.idempotency_key
        or terminal["tenant_workspace_id"] != request.tenant_workspace_id
        or terminal["snapshot_id"] != request.snapshot_id
        or terminal["knowledge_cutoff"] != request.knowledge_cutoff
        or terminal["model_contract_version"] != request.model_contract_version
        or terminal["output_profile"] != request.output_profile
        or not _rfc3339(terminal["completed_at"])
    ):
        return False
    if state == "failed":
        return (
            terminal["result_artifact_id"] is None
            and terminal["result_sha256"] is None
            and terminal["result_schema_version"] is None
            and terminal["summary"] is None
            and isinstance(terminal["failure_code"], str)
            and _FAILURE_CODE.fullmatch(terminal["failure_code"]) is not None
        )
    summary = terminal["summary"]
    return (
        _nonempty(terminal["result_artifact_id"])
        and isinstance(terminal["result_sha256"], str)
        and _SHA256.fullmatch(terminal["result_sha256"]) is not None
        and _nonempty(terminal["result_schema_version"])
        and terminal["failure_code"] is None
        and isinstance(summary, dict)
        and set(summary)
        == {"analysis_family", "evidence_count", "statistic_count", "validation_status"}
        and _nonempty(summary["analysis_family"])
        and _nonempty(summary["validation_status"])
        and type(summary["evidence_count"]) is int
        and 0 <= summary["evidence_count"] <= 1_000_000_000
        and type(summary["statistic_count"]) is int
        and 0 <= summary["statistic_count"] <= 1_000_000_000
    )


def _valid_temporal_response(
    request: TemporalContextRequest, response: object
) -> bool:
    """Validate TEPP temporal-context v1 before evidence promotion."""
    if not isinstance(response, dict) or set(response) != {
        "contract_version",
        "claim_boundary",
        "timeline_events",
        "temporal_relations",
        "transition_gap_candidates",
        "source_post_ids",
    }:
        return False
    timeline = response["timeline_events"]
    relations = response["temporal_relations"]
    gaps = response["transition_gap_candidates"]
    source_ids = response["source_post_ids"]
    if (
        response["contract_version"] != 1
        or response["claim_boundary"] != "association_not_causal"
        or not isinstance(timeline, list)
        or not isinstance(relations, list)
        or not isinstance(gaps, list)
        or not isinstance(source_ids, list)
        or len(timeline) != len(request.events)
        or len(relations) != len(timeline) - 1
        or len(gaps) != len(timeline) - 1
    ):
        return False
    request_events = {event.event_id: event for event in request.events}
    event_ids: list[str] = []
    for ordinal, item in enumerate(timeline):
        if not isinstance(item, dict) or set(item) != {
            "event_id",
            "source_post_id",
            "event_type_code",
            "event_label",
            "event_time",
            "project_reference",
            "actor_references",
            "sequence_ordinal",
            "is_subject",
        }:
            return False
        event = request_events.get(item["event_id"])
        if (
            event is None
            or type(item["sequence_ordinal"]) is not int
            or item["sequence_ordinal"] != ordinal
            or item["source_post_id"] != event.source_post_id
            or item["event_type_code"] != event.event_type_code
            or item["event_label"] != event.event_label
            or item["event_time"] != event.event_time
            or item["project_reference"] != event.project_reference
            or item["actor_references"] != list(event.actor_references)
            or item["is_subject"] != (event.source_post_id == request.subject_post_id)
        ):
            return False
        event_ids.append(event.event_id)
    if len(set(event_ids)) != len(event_ids) or source_ids != [
        item["source_post_id"] for item in timeline
    ]:
        return False
    for index, relation in enumerate(relations):
        if relation != {
            "from_event_id": event_ids[index],
            "to_event_id": event_ids[index + 1],
            "relation_code": "before",
        }:
            return False
    return all(
        gap
        == {
            "from_event_id": event_ids[index],
            "to_event_id": event_ids[index + 1],
            "evidence_status_code": "candidate_not_causal",
        }
        for index, gap in enumerate(gaps)
    )
