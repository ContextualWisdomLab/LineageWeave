"""Fail-closed JWT verification regressions that do not need live OIDC."""

from __future__ import annotations

import base64
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import backend.app.auth as auth


def _segment(value: dict) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unsigned_token(header: dict) -> str:
    return f"{_segment(header)}.{_segment({'sub': 'subject'})}.signature"


def test_signing_key_requires_nonempty_exact_kid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth.RSAAlgorithm, "from_jwk", lambda value: ("key", value))
    jwks = {
        "keys": [
            {"kid": "first", "kty": "RSA", "alg": "RS256", "n": "x", "e": "AQAB"},
            {"kid": "wanted", "kty": "RSA", "alg": "RS256", "n": "y", "e": "AQAB"},
        ]
    }

    key = auth._signing_key_from_jwks(
        jwks, _unsigned_token({"alg": "RS256", "kid": "wanted"})
    )
    assert key[0] == "key"
    assert '"kid": "wanted"' in key[1]

    with pytest.raises(HTTPException) as missing:
        auth._signing_key_from_jwks(jwks, _unsigned_token({"alg": "RS256"}))
    assert missing.value.status_code == 401

    with pytest.raises(HTTPException) as unknown:
        auth._signing_key_from_jwks(
            jwks, _unsigned_token({"alg": "RS256", "kid": "unknown"})
        )
    assert unknown.value.status_code == 401


def test_decode_requires_configured_resource_audience(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(auth, "_jwks", lambda settings: {"keys": []})
    monkeypatch.setattr(auth, "_signing_key_from_jwks", lambda jwks, token: "signing-key")

    def fake_decode(token, **kwargs):
        captured.update(kwargs)
        return {"sub": "subject-1"}

    monkeypatch.setattr(auth.jwt, "decode", fake_decode)
    settings = SimpleNamespace(
        oidc_issuer="https://id.example",
        oidc_audience="https://lineage.example/api",
        oidc_clock_skew_seconds=5,
    )

    claims = auth._decode_access_token("token", settings)

    assert claims["sub"] == "subject-1"
    assert captured["issuer"] == "https://id.example"
    assert captured["audience"] == "https://lineage.example/api"
    assert captured["algorithms"] == ["RS256"]
    assert "options" not in captured


def test_decode_rejects_missing_subject(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "_jwks", lambda settings: {"keys": []})
    monkeypatch.setattr(auth, "_signing_key_from_jwks", lambda jwks, token: "signing-key")
    monkeypatch.setattr(auth.jwt, "decode", lambda *args, **kwargs: {})
    settings = SimpleNamespace(
        oidc_issuer="https://id.example",
        oidc_audience="lineageweave-api",
        oidc_clock_skew_seconds=5,
    )

    with pytest.raises(HTTPException) as error:
        auth._decode_access_token("token", settings)
    assert error.value.status_code == 401
