"""Adapter for TEPP's published "modular consumer" contract.

`TEPP <https://github.com/ContextualWisdomLab/TEPP>`_ (Temporal Event
Psychometrics Platform) is consumed here exactly the way its own
``docs/connectors/naruon-artifact-consumer.md`` specifies for any external
service: submit a versioned ``AnalysisRunRequest``, never read TEPP's
database tables directly, and never present this repo's own heuristic
lineage scores as TEPP's calibrated psychometric measurement (they answer
different questions -- see docs/lineage-bi-research-notes.md).

TEPP publishes versioned submit and status/read contracts. This client keeps
those transports separate so an accepted receipt cannot be mistaken for a
terminal measurement result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

ANALYSIS_RUN_CONTRACT_VERSION = 1


class TeppNotAvailable(RuntimeError):
    """Raised by the default transport: TEPP has no live REST API yet."""


def _no_transport(request: dict[str, Any]) -> dict[str, Any]:
    """Implement the _no_transport operation for this channel."""
    raise TeppNotAvailable(
        "TEPP has no live HTTP endpoint yet (Rust-crate-only as of this writing). "
        "Pass a transport= callable to TeppClient once one exists, or consume TEPP "
        "as a Rust crate directly per its own docs/API_CONTRACT.md."
    )


def _no_status_transport(run_id: str) -> dict[str, Any]:
    """Fail closed when no TEPP status/read transport is configured."""
    raise TeppNotAvailable("TEPP status transport unavailable")


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
    contract_version: int = ANALYSIS_RUN_CONTRACT_VERSION

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


class TeppClient:
    """Submit and read TEPP analysis runs through separate transports."""

    def __init__(
        self,
        transport: Callable[[dict[str, Any]], dict[str, Any]] = _no_transport,
        status_transport: Callable[[str], dict[str, Any]] = _no_status_transport,
    ) -> None:
        self._transport = transport
        self._status_transport = status_transport

    def submit_analysis_run(self, request: AnalysisRunRequest) -> dict[str, Any]:
        """Submit a request; returns TEPP's ``AnalysisRunAccepted`` envelope."""
        return self._transport(request.to_json())

    def get_analysis_run_status(self, run_id: str) -> dict[str, Any]:
        """Read TEPP's status envelope for one opaque remote run id."""
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id must be a non-empty string")
        return self._status_transport(run_id)
