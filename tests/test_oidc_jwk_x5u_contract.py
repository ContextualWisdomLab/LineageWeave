"""Fail-closed RFC 7517 x5u contract for RSA verification JWKs."""

from __future__ import annotations

import base64
import json

import pytest

from lineageweave.oidc_jwks import JwksKeySelectionError, select_rs256_signing_key


# 2048-bit odd modulus and the standard RSA public exponent. The selector test
# uses an injected loader, so no private material belongs in this fixture.
_MODULUS = (1 << 2047) | 1


def _base64url_uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _segment(value: dict[str, object]) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _token() -> str:
    return f"{_segment({'alg': 'RS256', 'kid': 'wanted'})}.{_segment({'sub': 'subject'})}.c2ln"


def _public_jwk() -> dict[str, object]:
    return {
        "kid": "wanted",
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "key_ops": ["verify"],
        "n": _base64url_uint(_MODULUS),
        "e": _base64url_uint(65537),
    }


@pytest.mark.parametrize(
    "x5u",
    [
        "https://issuer.example.test/certs.pem",
        "http://issuer.example.test/certs.pem",
        "file:///tmp/certs.pem",
        "",
        1,
    ],
)
def test_unvalidated_x5u_metadata_is_rejected_before_key_loading(x5u: object) -> None:
    """The selector must not accept certificate URLs it never retrieves and validates."""
    loaded: list[str] = []
    key = {**_public_jwk(), "x5u": x5u}

    with pytest.raises(JwksKeySelectionError, match="no JWKS key matched"):
        select_rs256_signing_key(
            {"keys": [key]},
            _token(),
            jwk_loader=lambda encoded: loaded.append(encoded) or object(),
        )

    assert loaded == []


def test_x5u_bearing_duplicate_cannot_poison_verified_key_uniqueness() -> None:
    """Unsupported remote-certificate metadata must not create false key ambiguity."""
    public = _public_jwk()
    remote = {**public, "x5u": "https://issuer.example.test/certs.pem"}
    loaded: list[str] = []

    selected = select_rs256_signing_key(
        {"keys": [public, remote]},
        _token(),
        jwk_loader=lambda encoded: loaded.append(encoded) or "selected-key",
    )

    assert selected == "selected-key"
    assert len(loaded) == 1
    assert "x5u" not in json.loads(loaded[0])
