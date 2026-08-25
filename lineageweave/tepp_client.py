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

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable


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
        status_transport: Callable[[str], dict[str, Any]] = _no_status_transport,
    ) -> None:
        self._transport = transport
        self._status_transport = status_transport

    def submit_analysis_run(self, request: AnalysisRunRequest) -> dict[str, Any]:
        """Submit a request; returns TEPP's ``AnalysisRunAccepted`` envelope."""
        response = self._transport(request.to_json())
        if (
            isinstance(response, dict)
            and response.get("run_state") == "accepted"
            and not _valid_analysis_run_accepted(request, response)
        ):
            raise TeppInvalidResponse("TEPP analysis-run accepted response was invalid")
        return response

    def read_analysis_run_status(
        self, remote_run_id: str, request: AnalysisRunRequest
    ) -> dict[str, Any]:
        """Read and validate TEPP's request-bound status/result v1 payload."""
        response = self._status_transport(remote_run_id)
        if not _valid_analysis_run_status(remote_run_id, request, response):
            raise TeppInvalidResponse("TEPP analysis-run status response was invalid")
        return response


_SHA256 = re.compile(r"[0-9a-f]{64}")
_FAILURE_CODE = re.compile(r"[a-z][a-z0-9_]{0,63}")
_RFC3339 = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})"
)


def _valid_analysis_run_accepted(
    request: AnalysisRunRequest, response: object
) -> bool:
    """Mirror TEPP's bounded, strict accepted-response v1 contract."""
    if not isinstance(response, dict) or set(response) != {
        "contract_version",
        "run_id",
        "run_state",
        "idempotency_key",
    }:
        return False
    try:
        encoded = json.dumps(response, separators=(",", ":"), ensure_ascii=False).encode()
    except (TypeError, ValueError):
        return False
    return (
        len(encoded) <= 64 * 1024
        and response["contract_version"] == 1
        and response["run_state"] == "accepted"
        and response["idempotency_key"] == request.idempotency_key
        and _nonempty(response["run_id"])
        and _nonempty(response["idempotency_key"])
    )


def _nonempty(value: object) -> bool:
    """Return whether a wire string contains non-whitespace, non-control text."""
    return (
        isinstance(value, str)
        and bool(value.strip())
        and not any(unicodedata.category(char) == "Cc" for char in value)
    )


def _rfc3339(value: object) -> bool:
    """Accept a timezone-bearing RFC 3339 timestamp understood by Python."""
    if not isinstance(value, str) or _RFC3339.fullmatch(value) is None:
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
    except (TypeError, ValueError):
        return False
    if len(encoded) > 64 * 1024:
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
        or not _rfc3339(terminal["knowledge_cutoff"])
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
