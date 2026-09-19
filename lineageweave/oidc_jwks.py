"""Shared fail-closed RSA signing-key selection for OIDC access tokens.

The product verifier and operator smoke use this module so their accepted JWT/JWK
shapes cannot drift. Provider discovery, caching, HTTP transport, issuer, audience,
and claim validation remain at their owning call sites.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import jwt
from jwt.algorithms import RSAAlgorithm


class JwksKeySelectionError(ValueError):
    """Raised when a token header or matching JWKS verification key is unacceptable."""


def select_rs256_signing_key(
    jwks: dict[str, Any],
    token: str,
    *,
    jwk_loader: Callable[[str], object] | None = None,
) -> object:
    """Return the unique RSA verification key selected by a non-empty JWT ``kid``.

    Selection is deliberately narrower than merely finding a key whose signature
    happens to verify: the token must declare RS256 and a non-empty ``kid``; exactly
    one matching JWK must be an RSA signing/verification key whose advertised
    algorithm, use, and key operations do not contradict RS256 verification.
    """
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise JwksKeySelectionError("invalid access-token header") from exc

    if header.get("alg") != "RS256":
        raise JwksKeySelectionError("access token must use RS256")

    kid = header.get("kid")
    if not isinstance(kid, str) or not kid.strip():
        raise JwksKeySelectionError("access token must include a non-empty kid")

    keys = jwks.get("keys")
    if not isinstance(keys, list):
        keys = []
    load_jwk = RSAAlgorithm.from_jwk if jwk_loader is None else jwk_loader

    candidates: list[dict[str, Any]] = []
    for key in keys:
        if not isinstance(key, dict) or key.get("kid") != kid:
            continue
        if key.get("kty") != "RSA":
            continue
        if key.get("alg") not in (None, "RS256"):
            continue
        if key.get("use") not in (None, "sig"):
            continue
        key_ops = key.get("key_ops")
        if key_ops is not None and (
            not isinstance(key_ops, list) or "verify" not in key_ops
        ):
            continue
        candidates.append(key)

    if not candidates:
        raise JwksKeySelectionError(f"no JWKS key matched kid={kid!r}")
    if len(candidates) != 1:
        raise JwksKeySelectionError(
            "multiple acceptable JWKS keys matched access-token kid"
        )

    try:
        return load_jwk(json.dumps(candidates[0]))
    except (KeyError, TypeError, ValueError, jwt.PyJWTError) as exc:
        raise JwksKeySelectionError("matching JWKS key is invalid") from exc
