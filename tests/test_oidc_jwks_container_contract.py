"""Fail-closed contract for malformed JWKS top-level containers."""

from __future__ import annotations

import base64
import json
from typing import Any, cast

import pytest

from lineageweave.oidc_jwks import JwksKeySelectionError, select_rs256_signing_key


def _rs256_header_token() -> str:
    """Return a parseable unsigned token shape with an RS256/kid JOSE header."""
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "RS256", "kid": "fixture-key"}, separators=(",", ":")).encode("utf-8")
    ).rstrip(b"=").decode("ascii")
    payload = base64.urlsafe_b64encode(b"{}").rstrip(b"=").decode("ascii")
    return f"{header}.{payload}.AA"


@pytest.mark.parametrize("jwks", [None, [], "not-an-object", 1])
def test_non_object_jwks_fails_closed_as_key_selection_error(jwks: object) -> None:
    """Malformed provider JSON must not escape the shared auth boundary as AttributeError."""
    with pytest.raises(JwksKeySelectionError, match="JWKS must be a JSON object"):
        select_rs256_signing_key(cast(Any, jwks), _rs256_header_token())
