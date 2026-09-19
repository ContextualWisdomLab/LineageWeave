"""Executable contract for embedded X.509 evidence on RSA verification JWKs."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import NameOID

from lineageweave.oidc_jwks import JwksKeySelectionError, select_rs256_signing_key


def _segment(value: dict[str, object]) -> str:
    """Encode one compact JWT segment for selector-only test tokens."""
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _token() -> str:
    """Return an unsigned-shaped token whose header selects the test key."""
    return f"{_segment({'alg': 'RS256', 'kid': 'wanted'})}.{_segment({'sub': 'subject'})}.c2ln"


def _base64url_uint(value: int) -> str:
    """Encode one positive integer as an unpadded minimal Base64urlUInt."""
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _public_jwk(private_key: rsa.RSAPrivateKey) -> dict[str, object]:
    """Build the public JWK members corresponding to ``private_key``."""
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


def _certificate_for_private_key(private_key: object) -> str:
    """Return one self-signed DER certificate encoded for an RFC 7517 ``x5c`` member."""
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "lineageweave-x5c-test")])
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
    return base64.b64encode(certificate.public_bytes(serialization.Encoding.DER)).decode()


@pytest.fixture(scope="module")
def rsa_keys() -> tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey]:
    """Generate two independent 2048-bit keys for matching and mismatch contracts."""
    return (
        rsa.generate_private_key(public_exponent=65537, key_size=2048),
        rsa.generate_private_key(public_exponent=65537, key_size=2048),
    )


def test_matching_x5c_leaf_is_accepted(
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
) -> None:
    """An embedded leaf certificate may accompany the same RSA public key."""
    signing_key, _ = rsa_keys
    key = {**_public_jwk(signing_key), "x5c": [_certificate_for_private_key(signing_key)]}

    selected = select_rs256_signing_key(
        {"keys": [key]},
        _token(),
        jwk_loader=lambda _encoded: "selected-key",
    )

    assert selected == "selected-key"


def test_mismatched_x5c_leaf_is_rejected_before_loading(
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
) -> None:
    """The first x5c certificate must carry the same public key as JWK n/e."""
    signing_key, unrelated_key = rsa_keys
    key = {
        **_public_jwk(signing_key),
        "x5c": [_certificate_for_private_key(unrelated_key)],
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
    "x5c",
    [
        [],
        ["not base64!"],
        ["AA=="],
        ["AB=="],
        "not-a-chain",
        [1],
    ],
)
def test_malformed_x5c_is_rejected_before_loading(
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
    x5c: object,
) -> None:
    """Malformed certificate-chain metadata cannot enter candidate counting."""
    signing_key, _ = rsa_keys
    key = {**_public_jwk(signing_key), "x5c": x5c}
    loaded: list[str] = []

    with pytest.raises(JwksKeySelectionError, match="no JWKS key matched"):
        select_rs256_signing_key(
            {"keys": [key]},
            _token(),
            jwk_loader=lambda encoded: loaded.append(encoded) or object(),
        )

    assert loaded == []


def test_non_string_x5c_tail_is_rejected_before_loading(
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
) -> None:
    """Every certificate-chain member must be a non-empty Base64 string."""
    signing_key, _ = rsa_keys
    key = {
        **_public_jwk(signing_key),
        "x5c": [_certificate_for_private_key(signing_key), 1],
    }

    with pytest.raises(JwksKeySelectionError, match="no JWKS key matched"):
        select_rs256_signing_key({"keys": [key]}, _token(), jwk_loader=lambda _encoded: object())


def test_non_rsa_x5c_leaf_is_rejected_before_loading(
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
) -> None:
    """An RSA JWK cannot cite a leaf certificate whose public key is EC."""
    signing_key, _ = rsa_keys
    ec_key = ec.generate_private_key(ec.SECP256R1())
    key = {
        **_public_jwk(signing_key),
        "x5c": [_certificate_for_private_key(ec_key)],
    }

    with pytest.raises(JwksKeySelectionError, match="no JWKS key matched"):
        select_rs256_signing_key({"keys": [key]}, _token(), jwk_loader=lambda _encoded: object())


def test_mismatched_x5c_duplicate_cannot_poison_public_key_uniqueness(
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPrivateKey],
) -> None:
    """Contradictory certificate metadata must not manufacture same-kid ambiguity."""
    signing_key, unrelated_key = rsa_keys
    public = _public_jwk(signing_key)
    contradictory = {
        **public,
        "x5c": [_certificate_for_private_key(unrelated_key)],
    }
    loaded: list[str] = []

    selected = select_rs256_signing_key(
        {"keys": [public, contradictory]},
        _token(),
        jwk_loader=lambda encoded: loaded.append(encoded) or "selected-key",
    )

    assert selected == "selected-key"
    assert len(loaded) == 1
    assert "x5c" not in json.loads(loaded[0])
