"""Fail-closed Keyverse identity port.

Keyverse is the ecosystem IdP. LineageWeave consumes only the published
healthz envelope (GET /healthz) and never invents an issuer, account,
or token.
"""

from __future__ import annotations

import pytest

from lineageweave.http_client import HttpClientError
from lineageweave.keyverse_client import (
    HttpKeyverseTransport,
    KeyverseClient,
    KeyverseNotAvailable,
    parse_healthz,
)


def test_default_transport_fails_closed() -> None:
    client = KeyverseClient()
    with pytest.raises(KeyverseNotAvailable, match="keyverse_not_available"):
        client.probe_ready()


def test_default_payload_never_invents_an_identity() -> None:
    payload = KeyverseClient().as_api_payload()

    assert payload == {
        "port": "keyverse",
        "status": "unavailable",
        "status_reason": "keyverse_not_available",
        "ready": False,
    }
    assert "issuer" not in payload
    assert "accounts" not in payload
    assert "token" not in payload


def test_empty_base_url_factory_fails_closed() -> None:
    client = build_client("")
    payload = client.as_api_payload()
    assert payload["status"] == "unavailable"
    assert payload["ready"] is False


def build_client(base_url: str) -> KeyverseClient:
    from lineageweave.keyverse_client import build_keyverse_client

    return build_keyverse_client(base_url=base_url)


def test_parse_healthz_accepts_published_ok() -> None:
    identity = parse_healthz({"status": "ok", "issuer": "must-not-be-copied"})
    assert identity.ready is True
    assert not hasattr(identity, "issuer")


def test_parse_healthz_rejects_unknown_envelope() -> None:
    with pytest.raises(KeyverseNotAvailable, match="keyverse_not_available"):
        parse_healthz({"ready": True})


def test_parse_healthz_rejects_non_ok_status() -> None:
    with pytest.raises(KeyverseNotAvailable, match="keyverse_not_available"):
        parse_healthz({"status": "degraded"})


def test_injected_transport_returns_accepted_ready() -> None:
    payload = KeyverseClient(transport=lambda: {"status": "ok"}).as_api_payload()

    assert payload["status"] == "accepted"
    assert payload["status_reason"] is None
    assert payload["ready"] is True
    assert "issuer" not in payload


def test_http_transport_gets_published_healthz_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_get_json(url: str, *, headers: dict[str, str] | None = None, timeout: float) -> dict:
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return {"status": "ok"}

    monkeypatch.setattr("lineageweave.keyverse_client.get_json", fake_get_json)
    transport = HttpKeyverseTransport(base_url="https://keyverse.example")
    identity = KeyverseClient(transport=transport).probe_ready()

    assert captured["url"] == "https://keyverse.example/healthz"
    assert identity.ready is True


@pytest.mark.parametrize(
    "error",
    [
        HttpClientError("HTTP 503 from keyverse.example"),
        HttpClientError("HTTP 404 from keyverse.example"),
        TimeoutError("timed out"),
        OSError("network down"),
        ValueError("refusing non-http(s) URL scheme: 'file'"),
    ],
)
def test_http_transport_fail_closed_on_transport_errors(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    def boom(*_args: object, **_kwargs: object) -> dict:
        raise error

    monkeypatch.setattr("lineageweave.keyverse_client.get_json", boom)
    client = KeyverseClient(transport=HttpKeyverseTransport(base_url="https://keyverse.example"))
    with pytest.raises(KeyverseNotAvailable, match="keyverse_not_available"):
        client.probe_ready()
    assert client.as_api_payload()["ready"] is False
    assert client.as_api_payload()["status"] == "unavailable"
