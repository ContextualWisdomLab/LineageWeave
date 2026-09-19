"""Executable RFC 7518 Base64urlUInt minimal-encoding contracts."""

from __future__ import annotations

import base64
import json

import pytest

from lineageweave.oidc_jwks import JwksKeySelectionError, select_rs256_signing_key


def _segment(value: dict[str, object]) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _token(kid: str = "wanted") -> str:
    return f"{_segment({'alg': 'RS256', 'kid': kid})}.{_segment({'sub': 'subject'})}.c2ln"


def _base64url_uint(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _modulus_octets() -> bytes:
    value = (1 << 2047) | 1
    return value.to_bytes(256, "big")


def _valid_key() -> dict[str, object]:
    return {
        "kid": "wanted",
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "key_ops": ["verify"],
        "n": _base64url_uint(_modulus_octets()),
        "e": "AQAB",
    }


@pytest.mark.parametrize(
    ("field", "non_minimal_value"),
    [
        ("n", _base64url_uint(b"\x00" + _modulus_octets())),
        ("e", _base64url_uint(b"\x00\x01\x00\x01")),
    ],
)
def test_rejects_non_minimal_base64urluint_before_loading(
    field: str, non_minimal_value: str
) -> None:
    """Leading zero octets are not canonical Base64urlUInt representations."""
    loaded: list[str] = []
    key = {**_valid_key(), field: non_minimal_value}

    with pytest.raises(JwksKeySelectionError, match="no JWKS key matched"):
        select_rs256_signing_key(
            {"keys": [key]},
            _token(),
            jwk_loader=lambda value: loaded.append(value) or object(),
        )

    assert loaded == []


def test_non_minimal_same_kid_does_not_create_false_ambiguity() -> None:
    """A malformed duplicate must not poison selection of one canonical key."""
    valid = _valid_key()
    malformed = {
        **valid,
        "e": _base64url_uint(b"\x00\x01\x00\x01"),
    }
    loaded: list[str] = []

    selected = select_rs256_signing_key(
        {"keys": [valid, malformed]},
        _token(),
        jwk_loader=lambda value: loaded.append(value) or "selected-key",
    )

    assert selected == "selected-key"
    assert len(loaded) == 1
    assert json.loads(loaded[0])["e"] == "AQAB"
