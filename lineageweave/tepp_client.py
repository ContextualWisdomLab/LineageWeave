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

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


class TeppNotAvailable(RuntimeError):
    """Raised by the default transport: TEPP has no live REST API yet."""


def _no_transport(request: dict[str, Any]) -> dict[str, Any]:
    """Implement the _no_transport operation for this channel."""
    raise TeppNotAvailable(
        "TEPP has no live HTTP endpoint yet (Rust-crate-only as of this writing). "
        "Pass a transport= callable to TeppClient once one exists, or consume TEPP "
        "as a Rust crate directly per its own docs/API_CONTRACT.md."
    )


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
    ) -> None:
        self._transport = transport
        self._temporal_transport = temporal_transport

    def submit_analysis_run(self, request: AnalysisRunRequest) -> dict[str, Any]:
        """Submit a request; returns TEPP's ``AnalysisRunAccepted`` envelope."""
        return self._transport(request.to_json())

    def temporal_context(self, request: TemporalContextRequest) -> dict[str, Any]:
        """Return TEPP-owned ordering; callers must validate its claim boundary."""
        response = self._temporal_transport(request.to_json())
        if not _valid_temporal_response(request, response):
            raise TeppNotAvailable("TEPP temporal-context response was invalid")
        return response


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
