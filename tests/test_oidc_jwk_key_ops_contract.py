"""RFC 7517 key-operations contracts for shared OIDC JWK selection."""

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


def _key(key_ops: list[str]) -> dict[str, object]:
    return {
        "kid": "wanted",
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "key_ops": key_ops,
        "n": _rsa_modulus(),
        "e": "AQAB",
    }


@pytest.mark.parametrize(
    "key_ops",
    [
        ["verify", "verify"],
        ["verify", "encrypt"],
    ],
)
def test_rejects_nonconformant_key_operations_before_loading(
    key_ops: list[str],
) -> None:
    """Duplicate or unrelated operations cannot enter the RS256 candidate set."""
    loaded: list[str] = []

    with pytest.raises(JwksKeySelectionError, match="no JWKS key matched"):
        select_rs256_signing_key(
            {"keys": [_key(key_ops)]},
            _token(),
            jwk_loader=lambda value: loaded.append(value) or object(),
        )

    assert loaded == []


def test_invalid_key_operations_cannot_poison_same_kid_uniqueness() -> None:
    """A malformed duplicate must not manufacture candidate ambiguity."""
    valid = _key(["verify"])
    invalid = _key(["verify", "verify"])
    loaded: list[str] = []

    selected = select_rs256_signing_key(
        {"keys": [valid, invalid]},
        _token(),
        jwk_loader=lambda value: loaded.append(value) or "selected-key",
    )

    assert selected == "selected-key"
    assert len(loaded) == 1
    assert json.loads(loaded[0])["key_ops"] == ["verify"]


def test_permitted_signature_operation_pair_remains_acceptable() -> None:
    """RFC 7517 explicitly permits the related sign/verify operation pair."""
    selected = select_rs256_signing_key(
        {"keys": [_key(["sign", "verify"])]},
        _token(),
        jwk_loader=lambda _value: "selected-key",
    )

    assert selected == "selected-key"
