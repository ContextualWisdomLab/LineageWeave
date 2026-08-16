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
from urllib.parse import urlparse

from .http_client import HttpClientError, post_json

Poster = Callable[..., dict[str, Any]]


class TeppNotAvailable(RuntimeError):
    """Raised when TEPP transport is missing, non-HTTPS, or fail-closed."""


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
        """Submit a request; returns TEPP's ``AnalysisRunAccepted`` envelope."""
        return self._transport(request.to_json())


def analysis_run_request_from_registry(
    *,
    snapshot_id: str,
    knowledge_cutoff: str,
    idempotency_key: str,
    tenant_workspace_id: str,
    model_contract_version: str,
    output_profile: str,
    contract_version: int = 1,
) -> AnalysisRunRequest:
    """Build TEPP's published request from registry snapshot and cutoff clocks.

    ``snapshot_id`` and ``knowledge_cutoff`` are required registry facts. This
    helper does not invent TEPP arithmetic, read TEPP tables, or add fields
    beyond the published seven-property wire contract.
    """

    trimmed_snapshot = snapshot_id.strip()
    trimmed_cutoff = knowledge_cutoff.strip()
    if not trimmed_snapshot:
        raise ValueError("snapshot_id is required")
    if not trimmed_cutoff:
        raise ValueError("knowledge_cutoff is required")
    return AnalysisRunRequest(
        idempotency_key=idempotency_key,
        tenant_workspace_id=tenant_workspace_id,
        snapshot_id=trimmed_snapshot,
        knowledge_cutoff=trimmed_cutoff,
        model_contract_version=model_contract_version,
        output_profile=output_profile,
        contract_version=contract_version,
    )


def create_https_analysis_run_transport(
    base_url: str,
    *,
    api_key: str | None = None,
    poster: Poster = post_json,
    timeout: float = 60.0,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Return a fail-closed HTTPS POST ``/v1/analysis-runs`` transport.

    The default :class:`TeppClient` transport stays :class:`TeppNotAvailable`.
    Callers inject this factory only when a real HTTPS endpoint exists.
    """

    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise TeppNotAvailable(
            "TEPP HTTP transport requires an https:// base URL for POST /v1/analysis-runs"
        )
    endpoint = f"{base_url.rstrip('/')}/v1/analysis-runs"
    headers = {"authorization": f"Bearer {api_key}"} if api_key else {}

    def transport(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return poster(endpoint, payload, headers=headers, timeout=timeout)
        except HttpClientError as exc:
            raise TeppNotAvailable(f"TEPP HTTPS POST failed: {exc}") from exc

    return transport


def create_in_process_tepp_transport(
    tepp_api: Callable[[dict[str, Any]], dict[str, Any]],
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Wrap an injected in-process ``tepp_api`` callable as a TeppClient transport.

    LineageWeave never imports or queries another service's tables. The
    callable must already be a versioned TEPP API, not a local reimplementation
    of TEPP arithmetic.
    """

    def transport(payload: dict[str, Any]) -> dict[str, Any]:
        return tepp_api(payload)

    return transport

