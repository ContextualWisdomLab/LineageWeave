"""Shared fail-closed envelope. Never invents a measurement.

TEPP and orchestrator channels use the same shape so a missing service
and a confidently-negative result stay distinct. The payload has no
theta field and must not grow one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CHANNEL_TEPP = "tepp"
CHANNEL_ORCHESTRATOR = "orchestrator"

OUTCOME_ACCEPTED = "accepted"
OUTCOME_TEPP_NOT_AVAILABLE = "tepp_not_available"
OUTCOME_TEPP_TRANSPORT_FAILED = "tepp_transport_failed"
OUTCOME_ORCHESTRATOR_NOT_AVAILABLE = "orchestrator_not_available"

_FORBIDDEN_KEYS = frozenset({"theta", "theta_eap", "mean_theta", "score"})


@dataclass(frozen=True)
class FailClosedEnvelope:
    """Buyer-visible outcome for a channel that must not invent a value."""

    channel_code: str
    outcome_code: str
    next_action: str
    request: dict[str, Any] | None = None
    accepted: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        """Serialize without a theta. Extra keys on ``accepted`` are dropped
        when they look like a fabricated measurement.
        """
        payload: dict[str, Any] = {
            "channel_code": self.channel_code,
            "outcome_code": self.outcome_code,
            "next_action": self.next_action,
        }
        if self.request is not None:
            payload["request"] = {
                key: value for key, value in self.request.items() if key not in _FORBIDDEN_KEYS
            }
        if self.accepted is not None:
            payload["accepted"] = {
                key: value for key, value in self.accepted.items() if key not in _FORBIDDEN_KEYS
            }
        return payload


def tepp_unavailable_action() -> str:
    """Customer-actionable copy when TEPP is unset or crate-only."""
    return "Configure TEPP_BASE_URL to submit a real analysis run. No TEPP score was invented."


def tepp_transport_failed_action() -> str:
    return "TEPP did not accept this request. Retry when the service is reachable. No TEPP score was invented."


def tepp_accepted_action() -> str:
    return "Open the accepted TEPP run when that identity is ready. LineageWeave did not invent a theta."


def orchestrator_unavailable_action() -> str:
    return "Set ORCHESTRATOR_BASE_URL and ORCHESTRATOR_API_KEY. No answer was invented."
