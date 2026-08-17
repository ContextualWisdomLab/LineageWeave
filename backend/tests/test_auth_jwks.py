"""JWKS key selection must require a matching JWT kid."""

from __future__ import annotations

import json

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jwt.algorithms import RSAAlgorithm

from backend.app.auth import _signing_key_from_jwks


def _rsa_jwk_and_private_key(*, kid: str) -> tuple[dict, object]:
    """Return one JWKS RSA public key and the matching private key."""

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk["kid"] = kid
    public_jwk["use"] = "sig"
    public_jwk["alg"] = "RS256"
    return public_jwk, private_key


def test_signing_key_requires_kid_and_rejects_missing_or_unknown_kid() -> None:
    """A token without kid must not fall back to the first JWKS key."""

    first_jwk, first_private = _rsa_jwk_and_private_key(kid="first-key")
    second_jwk, _second_private = _rsa_jwk_and_private_key(kid="second-key")
    jwks = {"keys": [first_jwk, second_jwk]}

    matched = jwt.encode(
        {"sub": "demo-analyst"},
        first_private,
        algorithm="RS256",
        headers={"kid": "first-key"},
    )
    assert _signing_key_from_jwks(jwks, matched) is not None

    missing_kid = jwt.encode(
        {"sub": "demo-analyst"},
        first_private,
        algorithm="RS256",
        headers={},
    )
    with pytest.raises(HTTPException) as missing:
        _signing_key_from_jwks(jwks, missing_kid)
    assert missing.value.status_code == 401
    assert "missing kid" in missing.value.detail

    unknown_kid = jwt.encode(
        {"sub": "demo-analyst"},
        first_private,
        algorithm="RS256",
        headers={"kid": "unknown-key"},
    )
    with pytest.raises(HTTPException) as unknown:
        _signing_key_from_jwks(jwks, unknown_kid)
    assert unknown.value.status_code == 401
    assert "unknown-key" in unknown.value.detail
