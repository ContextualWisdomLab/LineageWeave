"""Fail-closed adapter for Keyverse's published admin-service healthz.

`Keyverse <https://github.com/ContextualWisdomLab/keyverse>`_ is the
ecosystem IdP (passwordless OIDC on Keycloak plus an account-unification
admin service). LineageWeave consumes only the published
``GET /healthz`` envelope (``{"status": "ok"}``) and never invents an
issuer, account, corp code, token, or client registration.

The default transport raises :class:`KeyverseNotAvailable` so a missing
Keyverse port is fail-closed, the same discipline as
:class:`lineageweave.tepp_client.TeppNotAvailable`. Wiring a live
HTTP(S) base URL is additive (``HttpKeyverseTransport``), not a
redesign. This port does not replace the synthetic demo Keycloak login.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from lineageweave.http_client import HttpClientError, get_json


class KeyverseNotAvailable(RuntimeError):
    """Raised when the Keyverse identity port is down or unconfigured."""

    reason = "keyverse_not_available"


def _no_transport() -> dict[str, Any]:
    raise KeyverseNotAvailable(
        "keyverse_not_available: Keyverse identity HTTP is not configured. "
        "Pass KEYVERSE_BASE_URL or a transport= callable. Never invent an identity."
    )


@dataclass(frozen=True)
class IdentityReady:
    """Accepted Keyverse readiness. No issuer, account, or token."""

    ready: bool

    def to_json(self) -> dict[str, Any]:
        return {"ready": self.ready}


def parse_healthz(payload: object) -> IdentityReady:
    """Accept Keyverse's published ``{status: "ok"}`` envelope.

    Unknown envelopes fail closed. Extra fields are dropped, never copied
    as an issuer or account.
    """
    if not isinstance(payload, dict) or payload.get("status") != "ok":
        raise KeyverseNotAvailable(
            "keyverse_not_available: healthz envelope is not the published {status: ok} shape"
        )
    return IdentityReady(ready=True)


class HttpKeyverseTransport:
    """GET ``{base_url}/healthz`` through the http(s)-only client."""

    def __init__(self, base_url: str, timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def __call__(self) -> dict[str, Any]:
        try:
            payload = get_json(
                f"{self.base_url}/healthz",
                timeout=self.timeout,
            )
        except (HttpClientError, OSError, TimeoutError, ValueError) as exc:
            raise KeyverseNotAvailable(
                f"keyverse_not_available: identity HTTP failed ({exc})"
            ) from exc
        if not isinstance(payload, dict):
            raise KeyverseNotAvailable(
                "keyverse_not_available: healthz HTTP did not return a JSON object"
            )
        return payload


def build_keyverse_client(base_url: str = "") -> "KeyverseClient":
    """Empty base URL keeps the default fail-closed transport."""
    if not base_url.strip():
        return KeyverseClient()
    return KeyverseClient(transport=HttpKeyverseTransport(base_url=base_url))


class KeyverseClient:
    """Probes Keyverse readiness through a pluggable transport."""

    def __init__(self, transport: Callable[[], dict[str, Any]] = _no_transport) -> None:
        self._transport = transport

    def probe_ready(self) -> IdentityReady:
        return parse_healthz(self._transport())

    def as_api_payload(self) -> dict[str, Any]:
        """Buyer-visible identity status. Never invents an identity."""
        try:
            identity = self.probe_ready()
        except KeyverseNotAvailable:
            return {
                "port": "keyverse",
                "status": "unavailable",
                "status_reason": KeyverseNotAvailable.reason,
                "ready": False,
            }
        return {
            "port": "keyverse",
            "status": "accepted",
            "status_reason": None,
            "ready": identity.ready,
        }
