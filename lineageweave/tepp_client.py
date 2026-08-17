"""Adapter for TEPP's published "modular consumer" contract.

`TEPP <https://github.com/ContextualWisdomLab/TEPP>`_ (Temporal Event
Psychometrics Platform) is consumed here exactly the way its own
``docs/connectors/naruon-artifact-consumer.md`` specifies for any external
service: submit a versioned ``AnalysisRunRequest``, never read TEPP's
database tables directly, and never present this repo's own heuristic
lineage scores as TEPP's calibrated psychometric measurement (they answer
different questions -- see docs/lineage-bi-research-notes.md).

When ``TEPP_BASE_URL`` and ``TEPP_API_TOKEN`` are set, :func:`http_transport`
POSTs the published seven-field body to ``/v1/analysis-runs`` (ADR 0014).
HTTPS is required unless ``LINEAGEWEAVE_DEV_MODE=1``. The default transport
still raises :class:`TeppNotAvailable`. Neither path invents a theta.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

from .http_client import HttpClientError

TEPP_STATES = frozenset(
    {
        "accepted",
        "validating",
        "queued",
        "running",
        "verifying",
        "completed",
        "failed",
        "rejected",
        "retryable",
        "cancelling",
        "cancelled",
    }
)
_HTTP_STATUS = re.compile(r"^HTTP (\d{3}) ")


class TeppNotAvailable(RuntimeError):
    """Raised by the default transport: TEPP has no live REST API yet."""


class TeppConfigError(RuntimeError):
    """Operator TEPP settings are missing or unsafe."""

    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        super().__init__(message)


class TeppEnvelopeError(RuntimeError):
    """TEPP returned an unusable accepted/error envelope."""

    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        super().__init__(message)


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


def tepp_http_config(environ: Mapping[str, str] | None = None) -> tuple[str, str]:
    """Return ``(base_url, token)`` or raise :class:`TeppConfigError`."""
    env = os.environ if environ is None else environ
    base = str(env.get("TEPP_BASE_URL", "")).strip()
    token = str(env.get("TEPP_API_TOKEN", "")).strip()
    if not base or not token:
        raise TeppConfigError(
            "tepp_service_unavailable",
            "TEPP_BASE_URL and TEPP_API_TOKEN must both be set",
        )
    parsed = urlparse(base)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise TeppConfigError("tepp_base_url_invalid", f"TEPP_BASE_URL is not an http(s) URL: {base!r}")
    if parsed.scheme != "https" and str(env.get("LINEAGEWEAVE_DEV_MODE", "")).strip() != "1":
        raise TeppConfigError("tepp_https_required", "TEPP_BASE_URL must be https unless LINEAGEWEAVE_DEV_MODE=1")
    return base.rstrip("/"), token


def normalize_tepp_accepted(payload: object) -> dict[str, Any]:
    """Keep lifecycle metadata only. Never copy a score or theta."""
    if not isinstance(payload, dict):
        raise TeppEnvelopeError("invalid", "TEPP body must be a JSON object")
    if "error_code" in payload:
        code = str(payload.get("error_code") or "tepp_error")
        raise TeppEnvelopeError(code, str(payload.get("message") or code))
    run_id = payload.get("analysis_run_id") or payload.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise TeppEnvelopeError("missing_run_id", "TEPP accepted envelope has no run id")
    state = payload.get("status") or payload.get("state") or "accepted"
    if not isinstance(state, str) or state not in TEPP_STATES:
        raise TeppEnvelopeError("invalid_state", f"unsupported TEPP state {state!r}")
    request_id = payload.get("request_id")
    return {
        "run_id": run_id.strip(),
        "state": state,
        "request_id": request_id if isinstance(request_id, str) else None,
        "retryable": bool(payload.get("retryable", False)),
    }


def _http_error_code(exc: HttpClientError) -> str:
    status = exc.status
    if status is None:
        match = _HTTP_STATUS.match(str(exc))
        status = int(match.group(1)) if match else None
    if status == 409:
        return "idempotency_conflict"
    if status == 429:
        return "rate_limited"
    if status is not None and status >= 500:
        return f"http_{status}"
    if status is not None:
        return f"http_{status}"
    return "unreachable"


def http_transport(
    base_url: str,
    token: str,
    *,
    post: Callable[..., dict[str, Any]] | None = None,
    timeout: float = 180.0,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """POST the published request to ``{base}/v1/analysis-runs``."""
    if post is None:
        from .http_client import post_json

        post = post_json

    def send(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            body = post(
                f"{base_url.rstrip('/')}/v1/analysis-runs",
                payload,
                headers={"authorization": f"Bearer {token}"},
                timeout=timeout,
            )
        except HttpClientError as exc:
            raise TeppEnvelopeError(_http_error_code(exc), str(exc)) from exc
        return normalize_tepp_accepted(body)

    return send


class TeppClient:
    """Submits :class:`AnalysisRunRequest` through a pluggable transport.

    The default transport always raises :class:`TeppNotAvailable`. Supply
    :func:`http_transport` when TEPP's HTTP service is configured.
    """

    def __init__(self, transport: Callable[[dict[str, Any]], dict[str, Any]] = _no_transport) -> None:
        self._transport = transport

    def submit_analysis_run(self, request: AnalysisRunRequest) -> dict[str, Any]:
        """Submit a request; returns TEPP's accepted envelope (lifecycle only)."""
        return self._transport(request.to_json())


def tepp_client_from_env(environ: Mapping[str, str] | None = None) -> TeppClient:
    """HTTP client when configured; otherwise the fail-closed default."""
    try:
        base_url, token = tepp_http_config(environ)
    except TeppConfigError:
        return TeppClient()
    return TeppClient(transport=http_transport(base_url, token))
