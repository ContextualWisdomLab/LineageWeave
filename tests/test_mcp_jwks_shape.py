"""Regression tests for malformed issuer JWKS responses."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.app import auth


@pytest.mark.parametrize("jwks", [{}, {"keys": None}, {"keys": {}}, {"keys": "not-an-array"}])
def test_signing_key_rejects_a_non_array_jwks_key_set(jwks: dict[str, object]) -> None:
    """Malformed issuer metadata must fail closed instead of raising an untyped error."""
    token = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImsxIn0.e30.sig"
    with pytest.raises(HTTPException, match="keys is not an array") as exc_info:
        auth._signing_key_from_jwks(jwks, token)
    assert exc_info.value.status_code == 503