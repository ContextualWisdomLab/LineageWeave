"""Shared fail-closed RSA signing-key selection for OIDC access tokens.

The product verifier and operator smoke use this module so their accepted JWT/JWK
shapes cannot drift. Provider discovery, caching, HTTP transport, issuer, audience,
and claim validation remain at their owning call sites.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
from collections.abc import Callable
from typing import Any

import jwt
from jwt.algorithms import RSAAlgorithm


class JwksKeySelectionError(ValueError):
    """Raised when a token header or matching JWKS verification key is unacceptable."""


_BASE64URL_UINT = re.compile(r"^[A-Za-z0-9_-]+$")


def _base64url_uint_value(value: object) -> int | None:
    """Decode one canonical minimal unpadded Base64urlUInt, or return ``None``."""
    if not isinstance(value, str) or _BASE64URL_UINT.fullmatch(value) is None:
        return None
    try:
        encoded = value.encode("ascii")
        raw = base64.b64decode(
            encoded + b"=" * (-len(encoded) % 4),
            altchars=b"-_",
            validate=True,
        )
    except (binascii.Error, ValueError):
        return None
    # RFC 7518 Base64urlUInt uses the minimum unsigned big-endian octet
    # sequence. A leading zero therefore makes every multi-octet value
    # noncanonical; zero itself is the one-octet sequence b"\x00" ("AA").
    if len(raw) > 1 and raw[0] == 0:
        return None
    return int.from_bytes(raw, "big")


def _rsa_modulus_bit_length(modulus: object) -> int | None:
    """Return an RSA JWK modulus bit length, or ``None`` for invalid Base64urlUInt."""
    value = _base64url_uint_value(modulus)
    return None if value is None else value.bit_length()


def select_rs256_signing_key(
    jwks: dict[str, Any],
    token: str,
    *,
    jwk_loader: Callable[[str], object] | None = None,
) -> object:
    """Return the unique RFC 7518-conformant RSA key selected by JWT ``kid``.

    Selection is deliberately narrower than merely finding a key whose signature
    happens to verify: the token must declare RS256 and a non-empty ``kid``; exactly
    one matching JWK must be an RSA signing/verification key whose advertised
    algorithm, use, key operations, modulus, and public exponent do not contradict
    RS256 verification. Both ``n`` and ``e`` must be canonical unpadded
    Base64urlUInt values using the minimum unsigned big-endian octet sequence.
    RFC 7518 section 3.3 requires RSA keys used with RS256 to be at least 2048 bits.
    The public exponent must also satisfy the basic RSA public-key constraints
    enforced by the downstream cryptography implementation: odd and at least three.
    LineageWeave implements no JWS critical-header extensions, so any ``crit``
    declaration fails closed as required by RFC 7515 section 4.1.11.
    """
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise JwksKeySelectionError("invalid access-token header") from exc

    if "crit" in header:
        raise JwksKeySelectionError(
            "critical JOSE header extensions are not supported"
        )

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
        modulus_bits = _rsa_modulus_bit_length(key.get("n"))
        if modulus_bits is None or modulus_bits < 2048:
            continue
        exponent = _base64url_uint_value(key.get("e"))
        if exponent is None or exponent < 3 or exponent % 2 == 0:
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
