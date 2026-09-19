"""Shared fail-closed RSA signing-key selection for OIDC access tokens.

The product verifier and operator smoke use this module so their accepted JWT/JWK
shapes cannot drift. Provider discovery, caching, HTTP transport, issuer, audience,
and claim validation remain at their owning call sites.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
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

    canonical = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    if canonical != value:
        return None
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
    if len(key_ops) != len(set(key_ops)):
        return False
    operations = set(key_ops)
    return "verify" in operations and operations <= {"sign", "verify"}


def _canonical_x5c_certificate(member: object) -> tuple[x509.Certificate, bytes] | None:
    """Decode one canonical ordinary-Base64 DER certificate from an x5c chain."""
    if not isinstance(member, str) or not member:
        return None
    try:
        encoded = member.encode("ascii")
        der = base64.b64decode(encoded, validate=True)
        if base64.b64encode(der).decode("ascii") != member:
            return None
        return x509.load_der_x509_certificate(der), der
    except (binascii.Error, UnicodeEncodeError, ValueError):
        return None


def _canonical_base64url_digest(member: object, digest_size: int) -> bytes | None:
    """Decode one fixed-width canonical unpadded Base64url digest."""
    if not isinstance(member, str) or not member or "=" in member:
        return None
    try:
        encoded = member.encode("ascii")
        raw = base64.b64decode(
            encoded + b"=" * (-len(encoded) % 4),
            altchars=b"-_",
            validate=True,
        )
    except (binascii.Error, UnicodeEncodeError, ValueError):
        return None
    if len(raw) != digest_size:
        return None
    canonical = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    if canonical != member:
        return None
    return raw


def _certificate_thumbprints_match(
    key: dict[str, Any], leaf_der: bytes | None
) -> bool:
    """Validate RFC 7517 certificate thumbprints and compare them when x5c is present."""
    for member, algorithm, digest_size in (
        ("x5t", "sha1", 20),
        ("x5t#S256", "sha256", 32),
    ):
        if member not in key:
            continue
        advertised = _canonical_base64url_digest(key[member], digest_size)
        if advertised is None:
            return False
        if leaf_der is not None and advertised != hashlib.new(algorithm, leaf_der).digest():
            return False
    return True


def _certificate_allows_signature_verification(certificate: x509.Certificate) -> bool:
    """Honor an X.509 KeyUsage restriction when the embedded leaf declares one."""
    try:
        key_usage = certificate.extensions.get_extension_for_class(x509.KeyUsage).value
    except x509.ExtensionNotFound:
        return True
    return key_usage.digital_signature or key_usage.content_commitment


def _x509_metadata_matches_rsa_public_key(
    key: dict[str, Any], modulus: int, exponent: int
) -> bool:
    """Validate RFC 7517 certificate metadata and match embedded x5c to JWK RSA."""
    if "x5c" not in key:
        return _certificate_thumbprints_match(key, None)

    chain = key["x5c"]
    if not isinstance(chain, list) or not chain:
        return False

    certificates: list[x509.Certificate] = []
    certificate_ders: list[bytes] = []
    for member in chain:
        parsed = _canonical_x5c_certificate(member)
        if parsed is None:
            return False
        certificate, der = parsed
        certificates.append(certificate)
        certificate_ders.append(der)

    leaf = certificates[0]
    leaf_der = certificate_ders[0]
    if not _certificate_thumbprints_match(key, leaf_der):
        return False
    public_key = leaf.public_key()
    if not isinstance(public_key, rsa.RSAPublicKey):
        return False
    numbers = public_key.public_numbers()
    return (
        numbers.n == modulus
        and numbers.e == exponent
        and _certificate_allows_signature_verification(leaf)
    )


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
    RFC 7517 ``x5u`` certificate URLs are rejected because this selector does not
    retrieve and validate the remote certificate resource; accepting the metadata
    would leave RFC-required consistency with the JWK public key unverified.
    When an RFC 7517 ``x5c`` certificate chain is present, it must be a non-empty
    array whose every member is canonical ordinary-Base64 DER for a valid X.509
    certificate; its first certificate must contain an RSA public key, exactly match
    the JWK ``n`` / ``e`` public key, and, when X.509 KeyUsage is present, permit
    verification of ordinary digital signatures. Optional RFC 7517 ``x5t`` and
    ``x5t#S256`` members must be canonical unpadded Base64url SHA-1/SHA-256 digests
    of the RFC-defined width; when ``x5c`` is present they must exactly match the
    first certificate's DER bytes. RFC 7517 requires certificate metadata to remain
    semantically consistent with the JWK; RFC 5280 section 4.2.1.3 makes an
    encryption-only leaf incompatible with this RS256 verifier. RFC 7518 section
    6.3.2 private RSA members are rejected before candidate counting: this verifier
    consumes public signing material and must never admit leaked private exponents,
    prime factors, CRT parameters, or multi-prime private information. RFC 7518
    section 3.3 requires RSA keys used with RS256 to be at least 2048 bits. RFC 8017
    section 3.1 defines the modulus as a product of distinct odd primes, so an RSA
    modulus is odd, and requires the public exponent to be between three and ``n -
    1``. Even exponents are invalid because the exponent must also be coprime to the
    modulus factors' Carmichael value. RFC 7517 section 4.3 forbids duplicate
    ``key_ops`` entries and warns against unrelated operation pairs, so an advertised
    operation set may contain only the related sign/verify pair and must include
    ``verify``. LineageWeave implements no JWS critical-header extensions, so any
    ``crit`` declaration fails closed as required by RFC 7515 section 4.1.11.
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
        if "x5u" in key:
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
        if not _x509_metadata_matches_rsa_public_key(key, modulus, exponent):
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
