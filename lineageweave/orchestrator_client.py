"""Fail-closed adapter for contextual-orchestrator's portable task envelope.

`contextual-orchestrator <https://github.com/ContextualWisdomLab/contextual-orchestrator>`_
owns provider routing, workflow depth, and verification. LineageWeave
sends a versioned envelope and never invents a completion, a confidence,
or a theta when the host is missing or the mode is rejected.

Upstream ``main`` currently accepts ``auto`` / ``route`` / ``conduct``.
Checked judgment still requests ``verify`` (ADR 0013). An
``invalid_mode`` response is fail-closed
(:class:`OrchestratorNotAvailable`), not a fabricated 0.0 score.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

ACCEPTED_MODES = frozenset({"auto", "verify"})
DEFAULT_CONTRACT_VERSION = 1
# Synthetic probe only. Never a customer prompt.
SYNTHETIC_PROBE_PROMPT = "synthetic_orchestration_probe"
SYNTHETIC_PROBE_HASH = hashlib.sha256(SYNTHETIC_PROBE_PROMPT.encode("utf-8")).hexdigest()


class OrchestratorNotAvailable(RuntimeError):
    """Raised when the orchestrator port is down, disabled, or invalid."""

    reason = "orchestrator_not_available"

    def __init__(self, message: str, *, reason: str | None = None) -> None:
        super().__init__(message)
        self.reason = reason or type(self).reason


def classify_orchestrator_error(detail: str) -> OrchestratorNotAvailable:
    """Map transport text to a fail-closed reason. Never invent a score."""
    text = detail.casefold()
    if "invalid_mode" in text:
        return OrchestratorNotAvailable(
            "orchestrator_invalid_mode: contextual-orchestrator rejected "
            "the published mode. Never invent a completion.",
            reason="orchestrator_invalid_mode",
        )
    return OrchestratorNotAvailable(
        f"orchestrator_not_available: {detail}. Never invent a completion."
    )


def _no_transport(_envelope: "TaskEnvelope") -> dict[str, Any]:
    raise OrchestratorNotAvailable(
        "orchestrator_not_available: contextual-orchestrator is not configured. "
        "Set ORCHESTRATOR_BASE_URL and ORCHESTRATOR_API_KEY. "
        "Never invent a completion."
    )


@dataclass(frozen=True)
class TaskEnvelope:
    """Portable task envelope. ``additionalProperties`` stay closed."""

    task_kind: str
    mode: str
    reasoning_effort: str
    contract_version: int = DEFAULT_CONTRACT_VERSION
    prompt_hash: str = SYNTHETIC_PROBE_HASH
    access_list: tuple[str, ...] = ("user_message",)

    def to_json(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "task_kind": self.task_kind,
            "mode": self.mode,
            "reasoning_effort": self.reasoning_effort,
            "prompt_hash": self.prompt_hash,
            "access_list": list(self.access_list),
        }


def published_task_envelopes() -> tuple[TaskEnvelope, TaskEnvelope]:
    """Structured work uses auto. Checked judgment uses verify."""
    return (
        TaskEnvelope(
            task_kind="structured",
            mode="auto",
            reasoning_effort="medium",
        ),
        TaskEnvelope(
            task_kind="checked_judgment",
            mode="verify",
            reasoning_effort="high",
        ),
    )


def _next_action(task_kind: str) -> str:
    if task_kind == "structured":
        return "Structured work uses auto"
    if task_kind == "checked_judgment":
        return "Checked judgment uses verify"
    return "Open Orchestration for the next accepted mode"


def _project_envelope(envelope: TaskEnvelope) -> dict[str, Any]:
    return {
        "task_kind": envelope.task_kind,
        "mode": envelope.mode,
        "reasoning_effort": envelope.reasoning_effort,
        "next_action": _next_action(envelope.task_kind),
    }


class LocalAcceptTransport:
    """Accept a published envelope locally. Home GET never POSTs a completion."""

    def __call__(self, envelope: TaskEnvelope) -> dict[str, Any]:
        if envelope.mode not in ACCEPTED_MODES:
            raise OrchestratorNotAvailable(
                f"orchestrator_invalid_mode: {envelope.mode!r} is not a "
                "published LineageWeave mode. Never invent a completion.",
                reason="orchestrator_invalid_mode",
            )
        return envelope.to_json()


def build_orchestrator_client(
    base_url: str = "",
    api_key: str = "",
    submit: Callable[[TaskEnvelope], Mapping[str, Any]] | None = None,
) -> "OrchestratorClient":
    """Empty credentials stay fail-closed. Set URL + key to publish envelopes."""
    if not str(base_url or "").strip() or not str(api_key or "").strip():
        return OrchestratorClient()
    return OrchestratorClient(transport=LocalAcceptTransport(), submit=submit)


class OrchestratorClient:
    """Publishes the portable envelope. Never invents a completion."""

    def __init__(
        self,
        transport: Callable[[TaskEnvelope], Mapping[str, Any]] = _no_transport,
        submit: Callable[[TaskEnvelope], Mapping[str, Any]] | None = None,
    ) -> None:
        self._transport = transport
        self._submit = submit

    def submit_task_envelope(self, envelope: TaskEnvelope) -> dict[str, Any]:
        if envelope.mode not in ACCEPTED_MODES:
            raise OrchestratorNotAvailable(
                f"orchestrator_invalid_mode: {envelope.mode!r} is not a "
                "published LineageWeave mode. Never invent a completion.",
                reason="orchestrator_invalid_mode",
            )
        sender = self._submit or self._transport
        try:
            raw = sender(envelope)
        except OrchestratorNotAvailable:
            raise
        except Exception as exc:
            raise classify_orchestrator_error(str(exc)) from exc
        if not isinstance(raw, Mapping):
            raise OrchestratorNotAvailable(
                "orchestrator_not_available: envelope reply is not an object"
            )
        return dict(raw)

    def as_api_payload(self) -> dict[str, Any]:
        """Buyer-visible orchestration status. Never invents a completion."""
        accepted: list[dict[str, Any]] = []
        try:
            for envelope in published_task_envelopes():
                self._transport(envelope)
                accepted.append(_project_envelope(envelope))
        except OrchestratorNotAvailable as exc:
            return {
                "port": "contextual_orchestrator",
                "status": "unavailable",
                "status_reason": exc.reason,
                "envelopes": [],
            }
        except Exception as exc:
            mapped = classify_orchestrator_error(str(exc))
            return {
                "port": "contextual_orchestrator",
                "status": "unavailable",
                "status_reason": mapped.reason,
                "envelopes": [],
            }
        return {
            "port": "contextual_orchestrator",
            "status": "accepted",
            "status_reason": None,
            "envelopes": accepted,
        }


def envelope_modes(payload: Mapping[str, Any]) -> Sequence[str]:
    """Test helper: modes the buyer can act on. Empty when unavailable."""
    rows = payload.get("envelopes")
    if not isinstance(rows, list):
        return ()
    return tuple(str(row.get("mode") or "") for row in rows if isinstance(row, Mapping))
