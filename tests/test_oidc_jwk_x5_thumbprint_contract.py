"""RFC 7517 x5t/x5t#S256 consistency contract for RSA verification JWKs."""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from lineageweave.oidc_jwks import JwksKeySelectionError, select_rs256_signing_key


def _segment(value: dict[str, object]) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _token() -> str:
    return f"{_segment({'alg': 'RS256', 'kid': 'wanted'})}.{_segment({'sub': 'subject'})}.c2ln"


def _base64url_uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _public_jwk(private_key: rsa.RSAPrivateKey) -> dict[str, object]:
    numbers = private_key.public_key().public_numbers()
    return {
        "kid": "wanted",
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "key_ops": ["verify"],
        "n": _base64url_uint(numbers.n),
        "e": _base64url_uint(numbers.e),
    }


def _certificate(private_key: rsa.RSAPrivateKey) -> tuple[str, bytes]:
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "lineageweave-thumbprint-test")])
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(private_key, hashes.SHA256())
    )
    der = certificate.public_bytes(serialization.Encoding.DER)
    return base64.b64encode(der).decode(), der


def _thumbprint(der: bytes, algorithm: str) -> str:
    digest = hashlib.new(algorithm, der).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


@pytest.fixture(scope="module")
def key_material() -> tuple[dict[str, object], str, bytes]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    x5c, der = _certificate(private_key)
    return _public_jwk(private_key), x5c, der


def test_matching_sha1_and_sha256_thumbprints_are_accepted(
    key_material: tuple[dict[str, object], str, bytes],
) -> None:
    public, x5c, der = key_material
    key = {
        **public,
        "x5c": [x5c],
        "x5t": _thumbprint(der, "sha1"),
        "x5t#S256": _thumbprint(der, "sha256"),
    }

    assert (
        select_rs256_signing_key(
            {"keys": [key]},
            _token(),
            jwk_loader=lambda _encoded: "selected-key",
        )
        == "selected-key"
    )


@pytest.mark.parametrize(
    ("member", "algorithm", "digest_size"),
    [("x5t", "sha1", 20), ("x5t#S256", "sha256", 32)],
)
def test_thumbprint_must_match_embedded_leaf_certificate(
    key_material: tuple[dict[str, object], str, bytes],
    member: str,
    algorithm: str,
    digest_size: int,
) -> None:
    public, x5c, der = key_material
    wrong = bytes([hashlib.new(algorithm, der).digest()[0] ^ 1]) + bytes(digest_size - 1)
    key = {
        **public,
        "x5c": [x5c],
        member: base64.urlsafe_b64encode(wrong).rstrip(b"=").decode(),
    }
    loaded: list[str] = []

    with pytest.raises(JwksKeySelectionError, match="no JWKS key matched"):
        select_rs256_signing_key(
            {"keys": [key]},
            _token(),
            jwk_loader=lambda encoded: loaded.append(encoded) or object(),
        )

    assert loaded == []


@pytest.mark.parametrize(
    ("member", "value"),
    [
        ("x5t", ""),
        ("x5t", 1),
        ("x5t", "not+base64"),
        ("x5t", "AA=="),
        ("x5t", "AB"),
        ("x5t", "AA"),
        ("x5t#S256", "AA"),
        ("x5t#S256", "ré"),
    ],
)
def test_thumbprint_metadata_is_canonical_base64url_of_exact_digest_length(
    key_material: tuple[dict[str, object], str, bytes],
    member: str,
    value: object,
) -> None:
    public, _x5c, _der = key_material
    key = {**public, member: value}

    with pytest.raises(JwksKeySelectionError, match="no JWKS key matched"):
        select_rs256_signing_key(
            {"keys": [key]},
            _token(),
            jwk_loader=lambda _encoded: object(),
        )


def test_well_formed_thumbprints_do_not_require_an_embedded_x5c_chain(
    key_material: tuple[dict[str, object], str, bytes],
) -> None:
    public, _x5c, _der = key_material
    key = {
        **public,
        "x5t": base64.urlsafe_b64encode(bytes(range(20))).rstrip(b"=").decode(),
        "x5t#S256": base64.urlsafe_b64encode(bytes(range(32))).rstrip(b"=").decode(),
    }

    assert (
        select_rs256_signing_key(
            {"keys": [key]},
            _token(),
            jwk_loader=lambda _encoded: "selected-key",
        )
        == "selected-key"
    )


def test_contradictory_thumbprint_duplicate_cannot_poison_public_key_uniqueness(
    key_material: tuple[dict[str, object], str, bytes],
) -> None:
    public, x5c, der = key_material
    contradictory = {
        **public,
        "x5c": [x5c],
        "x5t#S256": base64.urlsafe_b64encode(bytes(32)).rstrip(b"=").decode(),
    }
    assert contradictory["x5t#S256"] != _thumbprint(der, "sha256")
    loaded: list[str] = []

    selected = select_rs256_signing_key(
        {"keys": [public, contradictory]},
        _token(),
        jwk_loader=lambda encoded: loaded.append(encoded) or "selected-key",
    )

    assert selected == "selected-key"
    assert len(loaded) == 1
    assert "x5c" not in json.loads(loaded[0])
