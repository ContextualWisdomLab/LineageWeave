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
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm


class JwksKeySelectionError(ValueError):
    """Raised when a token header or matching JWKS verification key is unacceptable."""


_BASE64URL_UINT = re.compile(r"^[A-Za-z0-9_-]+$")
_RSA_PRIVATE_MEMBERS = frozenset({"d", "p", "q", "dp", "dq", "qi", "oth"})


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

    # RFC 4648 canonical Base64url requires every unused terminal pad bit to be
    # zero. Python's decoder accepts equivalent spellings with nonzero pad bits,
    # so round-trip the decoded bytes before the key can enter candidate counting.
    canonical = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    if canonical != value:
        return None

    # RFC 7518 Base64urlUInt uses the minimum unsigned big-endian octet
    # sequence. A leading zero therefore makes every multi-octet value
    # noncanonical; zero itself is the one-octet sequence b"\x00" ("AA").
    if len(raw) > 1 and raw[0] == 0:
        return None
    return int.from_bytes(raw, "big")


def _optional_string_member_equals(
    key: dict[str, Any], member: str, expected: str
) -> bool:
    """Accept an omitted optional JWK string member or its exact expected value."""
    if member not in key:
        return True
    value = key[member]
    return isinstance(value, str) and value == expected


def _key_ops_allow_rs256_verification(key_ops: object) -> bool:
    """Return whether present RFC 7517 key operations fit this verify-only use."""
    if not isinstance(key_ops, list):
        return False
    if any(not isinstance(operation, str) for operation in key_ops):
        return False
    # RFC 7517 section 4.3 forbids duplicate operation values and warns against
    # unrelated operations on one key. sign+verify is the related signature pair.
    if len(key_ops) != len(set(key_ops)):
        return False
    operations = set(key_ops)
    return "verify" in operations and operations <= {"sign", "verify"}


def _canonical_x5c_certificate(member: object) -> x509.Certificate | None:
    """Decode one canonical ordinary-Base64 DER certificate from an x5c chain."""
    if not isinstance(member, str) or not member:
        return None
    try:
        encoded = member.encode("ascii")
        der = base64.b64decode(encoded, validate=True)
        # RFC 7517 x5c uses ordinary RFC 4648 Base64, not Base64url. Re-encode
        # every member so nonzero pad bits and alternate spellings fail closed.
        if base64.b64encode(der).decode("ascii") != member:
            return None
        return x509.load_der_x509_certificate(der)
    except (binascii.Error, UnicodeEncodeError, ValueError):
        return None


def _x5c_leaf_matches_rsa_public_key(
    key: dict[str, Any], modulus: int, exponent: int
) -> bool:
    """Validate an RFC 7517 x5c chain and match its leaf to the JWK RSA key."""
    if "x5c" not in key:
        return True

    chain = key["x5c"]
    if not isinstance(chain, list) or not chain:
        return False

    certificates: list[x509.Certificate] = []
    for member in chain:
        certificate = _canonical_x5c_certificate(member)
        if certificate is None:
            return False
        certificates.append(certificate)

    public_key = certificates[0].public_key()
    if not isinstance(public_key, rsa.RSAPublicKey):
        return False
    numbers = public_key.public_numbers()
    return numbers.n == modulus and numbers.e == exponent


def select_rs256_signing_key(
    jwks: object,
    token: str,
    *,
    jwk_loader: Callable[[str], object] | None = None,
) -> object:
    """Return the unique RFC 7518-conformant RSA key selected by JWT ``kid``.

    Selection is deliberately narrower than merely finding a key whose signature
    happens to verify: the token must declare RS256 and a non-empty ``kid``; exactly
    one matching JWK must be a public RSA signing/verification key whose advertised
    algorithm, use, key operations, modulus, and public exponent do not contradict
    RS256 verification. The JWKS itself must be a JSON object; malformed provider
    JSON fails through this shared authentication boundary rather than escaping as
    an implementation exception. Optional ``alg``, ``use``, and ``key_ops`` members
    are optional only by absence: if present, their RFC 7517 JSON types must be valid.
    Both ``n`` and ``e`` must be canonical unpadded Base64urlUInt values using the
    minimum unsigned big-endian octet sequence and RFC 4648 canonical zero pad bits.
    When an RFC 7517 ``x5c`` certificate chain is present, it must be a non-empty
    array whose every member is canonical ordinary-Base64 DER for a valid X.509
    certificate; its first certificate must contain an RSA public key and exactly
    match the JWK ``n`` / ``e`` public key before the JWK can enter candidate
    counting. RFC 7518 section 6.3.2 private RSA members are rejected before
    candidate counting: this verifier consumes public signing material and must
    never admit leaked private exponents, prime factors, CRT parameters, or
    multi-prime private information. RFC 7518 section 3.3 requires RSA keys used
    with RS256 to be at least 2048 bits. RFC 8017 section 3.1 defines the modulus
    as a product of distinct odd primes, so an RSA modulus is odd, and requires the
    public exponent to be between three and ``n - 1``. Even exponents are invalid
    because the exponent must also be coprime to the modulus factors' Carmichael
    value. RFC 7517 section 4.3 forbids duplicate ``key_ops`` entries and warns
    against unrelated operation pairs, so an advertised operation set may contain
    only the related sign/verify pair and must include ``verify``. LineageWeave
    implements no JWS critical-header extensions, so any ``crit`` declaration fails
    closed as required by RFC 7515 section 4.1.11.
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

    if not isinstance(jwks, dict):
        raise JwksKeySelectionError("JWKS must be a JSON object")

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
        if _RSA_PRIVATE_MEMBERS.intersection(key):
            continue
        if not _optional_string_member_equals(key, "alg", "RS256"):
            continue
        if not _optional_string_member_equals(key, "use", "sig"):
            continue
        if "key_ops" in key and not _key_ops_allow_rs256_verification(
            key["key_ops"]
        ):
            continue
        modulus = _base64url_uint_value(key.get("n"))
        if (
            modulus is None
            or modulus.bit_length() < 2048
            or modulus % 2 == 0
        ):
            continue
        exponent = _base64url_uint_value(key.get("e"))
        if (
            exponent is None
            or exponent < 3
            or exponent % 2 == 0
            or exponent >= modulus
        ):
            continue
        if not _x5c_leaf_matches_rsa_public_key(key, modulus, exponent):
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
