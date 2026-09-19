"""RFC 7517 optional-member shape contracts for shared OIDC JWK selection."""

from __future__ import annotations

import base64
import json

import pytest

from lineageweave.oidc_jwks import JwksKeySelectionError, select_rs256_signing_key


def _segment(value: dict[str, object]) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _token() -> str:
    return f"{_segment({'alg': 'RS256', 'kid': 'wanted'})}.{_segment({'sub': 'subject'})}.c2ln"


def _rsa_modulus() -> str:
    value = (1 << 2047) | 1
    raw = value.to_bytes(256, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _key() -> dict[str, object]:
    return {
        "kid": "wanted",
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "key_ops": ["verify"],
        "n": _rsa_modulus(),
        "e": "AQAB",
    }


@pytest.mark.parametrize("member", ["alg", "use", "key_ops"])
def test_present_null_optional_metadata_is_rejected_before_loading(member: str) -> None:
    """Present JWK members must keep their RFC-defined JSON types; null is not omission."""
    malformed = _key()
    malformed[member] = None
    loaded: list[str] = []

    with pytest.raises(JwksKeySelectionError, match="no JWKS key matched"):
        select_rs256_signing_key(
            {"keys": [malformed]},
            _token(),
            jwk_loader=lambda value: loaded.append(value) or object(),
        )

    assert loaded == []


@pytest.mark.parametrize("member", ["alg", "use", "key_ops"])
def test_present_null_metadata_cannot_poison_same_kid_uniqueness(member: str) -> None:
    """A null-valued duplicate cannot manufacture ambiguity for one valid matching key."""
    valid = _key()
    malformed = _key()
    malformed[member] = None
    loaded: list[str] = []

    selected = select_rs256_signing_key(
        {"keys": [valid, malformed]},
        _token(),
        jwk_loader=lambda value: loaded.append(value) or "selected-key",
    )

    assert selected == "selected-key"
    assert len(loaded) == 1
    assert json.loads(loaded[0])["alg"] == "RS256"
