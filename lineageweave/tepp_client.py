"""Adapter for TEPP's published "modular consumer" contract.

`TEPP <https://github.com/ContextualWisdomLab/TEPP>`_ (Temporal Event
Psychometrics Platform) is consumed here exactly the way its own
``docs/connectors/naruon-artifact-consumer.md`` specifies for any external
service: submit a versioned ``AnalysisRunRequest``, never read TEPP's
database tables directly, and never present this repo's own heuristic
lineage scores as TEPP's calibrated psychometric measurement (they answer
different questions -- see docs/lineage-bi-research-notes.md).

TEPP's current protected main exposes Rust library/domain contracts and an
accepted target API contract, not a deployed HTTP service (see
``docs/API_CONTRACT.md`` in that repo). This client builds and validates the
exact wire shape TEPP has published
(``schemas/analysis_run_request_v1.json``), so an executable transport can be
added through :meth:`TeppClient.__init__` without a consumer redesign.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


class TeppNotAvailable(RuntimeError):
    """Raised when no executable TEPP transport is configured."""


def _no_transport(request: dict[str, Any]) -> dict[str, Any]:
    """Fail closed while TEPP exposes no executable transport."""
    raise TeppNotAvailable(
        "No executable TEPP transport is configured. TEPP currently publishes "
        "Rust library/domain contracts and an accepted target API contract; "
        "configure transport= when an executable service is available."
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

    def __post_init__(self) -> None:
        """Reject payloads that violate TEPP's v1 schema before transport."""
        if type(self.contract_version) is not int or self.contract_version != 1:
            raise ValueError("TEPP AnalysisRunRequest requires contract_version=1")
        for field_name in (
            "idempotency_key",
            "tenant_workspace_id",
            "snapshot_id",
            "knowledge_cutoff",
            "model_contract_version",
            "output_profile",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"TEPP AnalysisRunRequest field {field_name} must be non-blank text"
                )

    def to_json(self) -> dict[str, Any]:
        """Serialize the validated request into TEPP's v1 wire representation."""
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
        """Submit a request; returns TEPP's ``AnalysisRunAccepted`` envelope."""
        try:
            return self._transport(request.to_json())
        except TeppNotAvailable:
            raise
        except Exception as exc:
            raise TeppNotAvailable("TEPP transport request failed") from exc
