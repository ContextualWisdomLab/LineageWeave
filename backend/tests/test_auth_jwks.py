"""Fail-closed JWT verification regressions that do not need live OIDC."""

from __future__ import annotations

import base64
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.app import auth
from lineageweave.http_client import HttpClientError


def _segment(value: dict) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unsigned_token(header: dict) -> str:
    return f"{_segment(header)}.{_segment({'sub': 'subject'})}.{_segment({'test': 'signature'})}"


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


def test_signing_key_rejects_non_rs256_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth.RSAAlgorithm, "from_jwk", lambda value: ("key", value))
    jwks = {"keys": [{"kid": "wanted", "kty": "RSA", "n": "y", "e": "AQAB"}]}

    with pytest.raises(HTTPException) as error:
        auth._signing_key_from_jwks(
            jwks, _unsigned_token({"alg": "RS512", "kid": "wanted"})
        )

    assert error.value.status_code == 401


def test_signing_key_requires_rsa_jwk_and_verification_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth.RSAAlgorithm, "from_jwk", lambda value: ("key", value))
    token = _unsigned_token({"alg": "RS256", "kid": "wanted"})

    rejected_keys = [
        {"kid": "wanted", "n": "x", "e": "AQAB"},
        {"kid": "wanted", "kty": "EC", "alg": "RS256"},
        {"kid": "wanted", "kty": "RSA", "alg": "RS512", "n": "x", "e": "AQAB"},
        {"kid": "wanted", "kty": "RSA", "use": "enc", "n": "x", "e": "AQAB"},
        {"kid": "wanted", "kty": "RSA", "key_ops": ["encrypt"], "n": "x", "e": "AQAB"},
        {"kid": "wanted", "kty": "RSA", "key_ops": "verify", "n": "x", "e": "AQAB"},
    ]

    for key in rejected_keys:
        with pytest.raises(HTTPException) as error:
            auth._signing_key_from_jwks({"keys": [key]}, token)
        assert error.value.status_code == 401

    accepted = {
        "kid": "wanted",
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "key_ops": ["verify"],
        "n": "x",
        "e": "AQAB",
    }
    assert auth._signing_key_from_jwks({"keys": [accepted]}, token)[0] == "key"


def test_signing_key_refreshes_jwks_once_for_rotated_kid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth.RSAAlgorithm, "from_jwk", lambda value: ("key", value))
    calls: list[bool] = []
    old_jwks = {
        "keys": [{"kid": "old", "kty": "RSA", "alg": "RS256", "n": "x", "e": "AQAB"}]
    }
    new_jwks = {
        "keys": [{"kid": "new", "kty": "RSA", "alg": "RS256", "n": "y", "e": "AQAB"}]
    }

    def fake_jwks(settings, *, force_refresh=False):
        calls.append(force_refresh)
        return new_jwks if force_refresh else old_jwks

    monkeypatch.setattr(auth, "_jwks", fake_jwks)
    token = _unsigned_token({"alg": "RS256", "kid": "new"})

    key = auth._signing_key(SimpleNamespace(), token)

    assert key[0] == "key"
    assert calls == [False, True]


def test_signing_key_does_not_refresh_for_invalid_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bool] = []

    def fake_jwks(settings, *, force_refresh=False):
        calls.append(force_refresh)
        return {"keys": []}

    monkeypatch.setattr(auth, "_jwks", fake_jwks)

    with pytest.raises(HTTPException) as error:
        auth._signing_key(
            SimpleNamespace(),
            _unsigned_token({"alg": "RS512", "kid": "unknown"}),
        )

    assert error.value.status_code == 401
    assert calls == [False]


def test_decode_requires_configured_resource_audience(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(auth, "_signing_key", lambda settings, token: "signing-key")

    def fake_decode(token, **kwargs):
        captured.update(kwargs)
        return {"sub": "subject-1"}

    monkeypatch.setattr(auth.jwt, "decode", fake_decode)
    settings = SimpleNamespace(
        oidc_issuer="https://id.example",
        oidc_audience="https://lineage.example/api",
        oidc_clock_skew_seconds=5,
        keyverse_claim_binding_required=True,
    )

    claims = auth._decode_access_token("token", settings)

    assert claims["sub"] == "subject-1"
    assert captured["issuer"] == "https://id.example"
    assert captured["audience"] == "https://lineage.example/api"
    assert captured["algorithms"] == ["RS256"]
    assert captured["options"] == {"require": ["exp", "iat", "sub"]}


def test_decode_rejects_missing_subject(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "_signing_key", lambda settings, token: "signing-key")
    monkeypatch.setattr(auth.jwt, "decode", lambda *args, **kwargs: {})
    settings = SimpleNamespace(
        oidc_issuer="https://id.example",
        oidc_audience="lineageweave-api",
        oidc_clock_skew_seconds=5,
        keyverse_claim_binding_required=False,
    )

    with pytest.raises(HTTPException) as error:
        auth._decode_access_token("token", settings)
    assert error.value.status_code == 401


def test_local_decode_does_not_require_keyverse_issued_at_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(auth, "_signing_key", lambda settings, token: "signing-key")

    def fake_decode(token, **kwargs):
        captured.update(kwargs)
        return {"sub": "subject-1"}

    monkeypatch.setattr(auth.jwt, "decode", fake_decode)
    settings = SimpleNamespace(
        oidc_issuer="https://local.example",
        oidc_audience="lineageweave-api",
        oidc_clock_skew_seconds=5,
        keyverse_claim_binding_required=False,
    )

    auth._decode_access_token("token", settings)

    assert captured["options"] == {"require": ["exp", "sub"]}


@pytest.mark.parametrize(
    "claims",
    [
        {"workspace": "workspace-a", "role": ["member"]},
        {"org": "org-a", "role": ["member"]},
        {"org": "org-a", "workspace": "workspace-a", "role": "member"},
        {"org": "org-a", "workspace": "workspace-a", "role": ["member", "member"]},
        {"org": ["org-a"], "workspace": "workspace-a", "role": ["member"]},
    ],
)
def test_keyverse_account_claims_reject_partial_or_ambiguous_profiles(claims: dict) -> None:
    """Keyverse account claims are atomic and never delimiter-decoded."""
    with pytest.raises(HTTPException) as error:
        auth._keyverse_account_claims(claims)
    assert error.value.status_code == 401


def test_keyverse_account_claims_return_one_trimmed_scope() -> None:
    assert auth._keyverse_account_claims(
        {"org": "org-a", "workspace": "workspace-a", "role": ["member", "reviewer"]}
    ) == ("org-a", "workspace-a", ["member", "reviewer"])


def test_decode_hides_raw_jwt_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "_signing_key", lambda settings, token: "signing-key")

    def fail_decode(*args: object, **kwargs: object) -> dict:
        raise auth.jwt.InvalidTokenError("provider secret")

    monkeypatch.setattr(auth.jwt, "decode", fail_decode)
    settings = SimpleNamespace(
        oidc_issuer="https://id.example",
        oidc_audience="lineageweave-api",
        oidc_clock_skew_seconds=5,
        keyverse_claim_binding_required=False,
    )

    with pytest.raises(HTTPException) as error:
        auth._decode_access_token("token", settings)
    assert error.value.detail == "invalid access token"
    assert "provider secret" not in str(error.value.detail)


def test_jwks_hides_raw_identity_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        auth,
        "get_json",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            HttpClientError("identity provider secret")
        ),
    )
    settings = SimpleNamespace(
        oidc_issuer="https://id.example",
        oidc_discovery_uri="https://id.example/.well-known/openid-configuration",
        oidc_jwks_uri_override="",
    )

    with pytest.raises(HTTPException) as error:
        auth._jwks(settings)
    assert error.value.detail == "could not fetch OIDC JWKS: identity provider unavailable"
    assert "identity provider secret" not in str(error.value.detail)
