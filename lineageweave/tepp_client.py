"""Adapter for TEPP's published "modular consumer" contract.

`TEPP <https://github.com/ContextualWisdomLab/TEPP>`_ (Temporal Event
Psychometrics Platform) is consumed here exactly the way its own
``docs/connectors/naruon-artifact-consumer.md`` specifies for any external
service: submit a versioned ``AnalysisRunRequest``, never read TEPP's
database tables directly, and never present this repo's own heuristic
lineage scores as TEPP's calibrated psychometric measurement (they answer
different questions -- see docs/lineage-bi-research-notes.md).

TEPP does not expose a live HTTP endpoint yet (as of this writing it is
Rust-crate-only; see ``docs/API_CONTRACT.md`` in that repo). This client
builds and validates the exact wire shape TEPP has published
(``schemas/analysis_run_request_v1.json``) so wiring in a real transport is
a one-line change (:meth:`TeppClient.__init__`'s ``transport`` argument) once
that endpoint exists, instead of a redesign.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


class TeppNotAvailable(RuntimeError):
    """Raised by the default transport: TEPP has no live REST API yet."""


def _no_transport(request: dict[str, Any]) -> dict[str, Any]:
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
        return {
            "contract_version": self.contract_version,
            "idempotency_key": self.idempotency_key,
            "tenant_workspace_id": self.tenant_workspace_id,
            "snapshot_id": self.snapshot_id,
            "knowledge_cutoff": self.knowledge_cutoff,
            "model_contract_version": self.model_contract_version,
            "output_profile": self.output_profile,
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

    def __init__(self, transport: Callable[[dict[str, Any]], dict[str, Any]] = _no_transport) -> None:
        self._transport = transport

    def submit_analysis_run(self, request: AnalysisRunRequest) -> dict[str, Any]:
        """Submit a request; returns TEPP's published ``AnalysisRunAccepted`` envelope.

        That acknowledgement is not a completed measurement. LineageWeave
        stores it as aggregate transport evidence and never stamps
        Succeeded from ``run_state=accepted``.
        """
        return self._transport(request.to_json())
