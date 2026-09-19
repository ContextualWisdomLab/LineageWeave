"""Executable contract for X.509 KeyUsage on embedded RSA verification JWKs."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
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


def _certificate(
    private_key: rsa.RSAPrivateKey,
    key_usage: x509.KeyUsage | None,
) -> str:
    """Return a self-signed RSA leaf with the requested KeyUsage extension."""
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "lineageweave-key-usage-test")])
    now = datetime.now(timezone.utc)
    builder = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
    )
    if key_usage is not None:
        builder = builder.add_extension(key_usage, critical=True)
    certificate = builder.sign(private_key, hashes.SHA256())
    return base64.b64encode(certificate.public_bytes(serialization.Encoding.DER)).decode()


def _usage(*, digital_signature: bool = False, content_commitment: bool = False, key_encipherment: bool = False) -> x509.KeyUsage:
    """Build the narrow KeyUsage combinations relevant to JWT signature verification."""
    return x509.KeyUsage(
        digital_signature=digital_signature,
        content_commitment=content_commitment,
        key_encipherment=key_encipherment,
        data_encipherment=False,
        key_agreement=False,
        key_cert_sign=False,
        crl_sign=False,
        encipher_only=False,
        decipher_only=False,
    )


@pytest.fixture(scope="module")
def signing_key() -> rsa.RSAPrivateKey:
    """Generate one 2048-bit RSA key for certificate/JWK consistency tests."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.mark.parametrize(
    "key_usage",
    [None, _usage(digital_signature=True), _usage(content_commitment=True)],
)
def test_signature_capable_or_unspecified_leaf_key_usage_is_accepted(
    signing_key: rsa.RSAPrivateKey,
    key_usage: x509.KeyUsage | None,
) -> None:
    """Absent KeyUsage or a signature bit remains compatible with RS256 verification."""
    key = {**_public_jwk(signing_key), "x5c": [_certificate(signing_key, key_usage)]}

    selected = select_rs256_signing_key(
        {"keys": [key]},
        _token(),
        jwk_loader=lambda _encoded: "selected-key",
    )

    assert selected == "selected-key"


def test_encryption_only_leaf_key_usage_is_rejected_before_loading(
    signing_key: rsa.RSAPrivateKey,
) -> None:
    """An embedded certificate restricted to encryption cannot back an RS256 verifier."""
    key = {
        **_public_jwk(signing_key),
        "x5c": [_certificate(signing_key, _usage(key_encipherment=True))],
    }
    loaded: list[str] = []

    with pytest.raises(JwksKeySelectionError, match="no JWKS key matched"):
        select_rs256_signing_key(
            {"keys": [key]},
            _token(),
            jwk_loader=lambda encoded: loaded.append(encoded) or object(),
        )

    assert loaded == []


def test_encryption_only_x5c_duplicate_cannot_poison_public_key_uniqueness(
    signing_key: rsa.RSAPrivateKey,
) -> None:
    """A usage-incompatible same-kid certificate cannot manufacture ambiguity."""
    public = _public_jwk(signing_key)
    incompatible = {
        **public,
        "x5c": [_certificate(signing_key, _usage(key_encipherment=True))],
    }
    loaded: list[str] = []

    selected = select_rs256_signing_key(
        {"keys": [public, incompatible]},
        _token(),
        jwk_loader=lambda encoded: loaded.append(encoded) or "selected-key",
    )

    assert selected == "selected-key"
    assert len(loaded) == 1
    assert "x5c" not in json.loads(loaded[0])
