"""Adapter for TEPP's published "modular consumer" contract.

`TEPP <https://github.com/ContextualWisdomLab/TEPP>`_ (Temporal Event
Psychometrics Platform) is consumed here exactly the way its own
``docs/connectors/naruon-artifact-consumer.md`` specifies for any external
service: submit a versioned ``AnalysisRunRequest``, never read TEPP's
database tables directly, and never present this repo's own heuristic
lineage scores as TEPP's calibrated psychometric measurement (they answer
different questions -- see docs/lineage-bi-research-notes.md).

TEPP does not expose a live HTTP endpoint on its protected main
(Rust-crate-only as of this writing; see ``docs/API_CONTRACT.md``).
This client builds the published request shape and, when
``TEPP_BASE_URL`` is set, POSTs it to ``/v1/analysis-runs`` through
``http_client.post_json``. A missing or failing service returns a
fail-closed envelope -- never a fabricated theta.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


from .fail_closed import (
    CHANNEL_TEPP,
    OUTCOME_ACCEPTED,
    OUTCOME_TEPP_NOT_AVAILABLE,
    OUTCOME_TEPP_TRANSPORT_FAILED,
    FailClosedEnvelope,
    tepp_accepted_action,
    tepp_transport_failed_action,
    tepp_unavailable_action,
)


class TeppNotAvailable(RuntimeError):
    """Raised by the default transport: TEPP has no live REST API yet."""


def _no_transport(request: dict[str, Any]) -> dict[str, Any]:
    raise TeppNotAvailable(
        "TEPP has no live HTTP endpoint yet (Rust-crate-only as of this writing). "
        "Pass a transport= callable to TeppClient, or set TEPP_BASE_URL."
    )


def http_tepp_transport(base_url: str, *, timeout: float = 10.0) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """POST the published request to TEPP's target ``/v1/analysis-runs``.

    ``http_client.post_json`` allowlists ``http``/``https`` and never
    opens ``file://``. A non-success HTTP status becomes
    :class:`TeppNotAvailable` so callers stay fail-closed.
    """
    root = base_url.rstrip("/")

    def send(payload: dict[str, Any]) -> dict[str, Any]:
        from .http_client import HttpClientError, post_json

        try:
            return post_json(
                f"{root}/v1/analysis-runs",
                payload,
                headers={"accept": "application/json"},
                timeout=timeout,
            )
        except (HttpClientError, ValueError, OSError) as exc:
            raise TeppNotAvailable(str(exc)) from exc

    return send


def client_from_base_url(base_url: str | None) -> TeppClient:
    """HTTP client when ``base_url`` is set; otherwise the crate-only default."""
    if base_url and base_url.strip():
        return TeppClient(transport=http_tepp_transport(base_url.strip()))
    return TeppClient()


def submit_fail_closed(client: TeppClient, request: AnalysisRunRequest) -> FailClosedEnvelope:
    """Submit a run and always return an envelope. Never invent a theta."""
    try:
        accepted = client.submit_analysis_run(request)
    except TeppNotAvailable:
        return FailClosedEnvelope(
            channel_code=CHANNEL_TEPP,
            outcome_code=OUTCOME_TEPP_NOT_AVAILABLE,
            next_action=tepp_unavailable_action(),
            request=request.to_json(),
        )
    except Exception:
        return FailClosedEnvelope(
            channel_code=CHANNEL_TEPP,
            outcome_code=OUTCOME_TEPP_TRANSPORT_FAILED,
            next_action=tepp_transport_failed_action(),
            request=request.to_json(),
        )
    if not isinstance(accepted, dict):
        return FailClosedEnvelope(
            channel_code=CHANNEL_TEPP,
            outcome_code=OUTCOME_TEPP_TRANSPORT_FAILED,
            next_action=tepp_transport_failed_action(),
            request=request.to_json(),
        )
    return FailClosedEnvelope(
        channel_code=CHANNEL_TEPP,
        outcome_code=OUTCOME_ACCEPTED,
        next_action=tepp_accepted_action(),
        request=request.to_json(),
        accepted=accepted,
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
