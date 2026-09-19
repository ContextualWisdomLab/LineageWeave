"""Executable contract for public-only RSA verification JWKs."""

from __future__ import annotations

import base64
import json

import pytest

from lineageweave.oidc_jwks import JwksKeySelectionError, select_rs256_signing_key


def _segment(value: dict[str, object]) -> str:
    """Encode one compact JWT segment for selector-only test tokens."""
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _token() -> str:
    """Return an unsigned-shaped token whose header selects the test key."""
    return f"{_segment({'alg': 'RS256', 'kid': 'wanted'})}.{_segment({'sub': 'subject'})}.c2ln"


def _public_key() -> dict[str, object]:
    """Return the minimal structurally admissible 2048-bit public RSA JWK."""
    modulus = ((1 << 2047) | 1).to_bytes(256, "big")
    return {
        "kid": "wanted",
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "key_ops": ["verify"],
        "n": base64.urlsafe_b64encode(modulus).rstrip(b"=").decode(),
        "e": "AQAB",
    }


@pytest.mark.parametrize(
    ("member", "value"),
    [
        ("d", "AQAB"),
        ("p", "AQAB"),
        ("q", "AQAB"),
        ("dp", "AQAB"),
        ("dq", "AQAB"),
        ("qi", "AQAB"),
        ("oth", [{"r": "AQAB", "d": "AQAB", "t": "AQAB"}]),
    ],
)
def test_verifier_rejects_rsa_private_key_members_before_loading(
    member: str,
    value: object,
) -> None:
    """A verification JWKS must never admit RFC 7518 private RSA parameters."""
    key = {**_public_key(), member: value}
    loaded: list[str] = []

    with pytest.raises(JwksKeySelectionError, match="no JWKS key matched"):
        select_rs256_signing_key(
            {"keys": [key]},
            _token(),
            jwk_loader=lambda encoded: loaded.append(encoded) or object(),
        )

    assert loaded == []


def test_private_material_duplicate_cannot_poison_public_key_uniqueness() -> None:
    """A leaked-private duplicate must not manufacture same-kid ambiguity."""
    public = _public_key()
    leaked_private = {**public, "d": "AQAB"}
    loaded: list[str] = []

    selected = select_rs256_signing_key(
        {"keys": [public, leaked_private]},
        _token(),
        jwk_loader=lambda encoded: loaded.append(encoded) or "selected-key",
    )

    assert selected == "selected-key"
    assert len(loaded) == 1
    assert "d" not in json.loads(loaded[0])
