"""Executable contracts for RSA JWK exponent selection."""

from __future__ import annotations

import base64
import json
import unittest

from lineageweave.oidc_jwks import JwksKeySelectionError, select_rs256_signing_key


def _base64url(data: bytes) -> str:
    """Return canonical unpadded Base64url text."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _token(kid: str = "key-1") -> str:
    """Build a parseable unsigned JWT shape for unverified-header selection tests."""
    header = _base64url(
        json.dumps({"alg": "RS256", "kid": kid}, separators=(",", ":")).encode()
    )
    return f"{header}.{_base64url(b'{}')}.AA"


def _rsa_key(exponent: str | None) -> dict[str, object]:
    """Return one 2048-bit-shaped RSA JWK candidate for selector-boundary tests."""
    key: dict[str, object] = {
        "kid": "key-1",
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "key_ops": ["verify"],
        "n": _base64url(b"\x80" + b"\x00" * 254 + b"\x01"),
    }
    if exponent is not None:
        key["e"] = exponent
    return key


class RsaJwkExponentContractTests(unittest.TestCase):
    def test_missing_exponent_is_not_an_acceptable_candidate(self) -> None:
        """RSA candidates require the JWK ``e`` member before loader admission."""
        with self.assertRaisesRegex(JwksKeySelectionError, "no JWKS key matched"):
            select_rs256_signing_key(
                {"keys": [_rsa_key(None)]},
                _token(),
                jwk_loader=lambda value: value,
            )

    def test_padded_exponent_is_not_canonical_base64urluint(self) -> None:
        """Explicit Base64 padding on ``e`` must fail before a permissive loader."""
        with self.assertRaisesRegex(JwksKeySelectionError, "no JWKS key matched"):
            select_rs256_signing_key(
                {"keys": [_rsa_key("AQAB==")]},
                _token(),
                jwk_loader=lambda value: value,
            )

    def test_exponent_below_three_is_not_an_acceptable_rsa_public_key(self) -> None:
        """RSA public exponent one is excluded before duplicate-key counting."""
        with self.assertRaisesRegex(JwksKeySelectionError, "no JWKS key matched"):
            select_rs256_signing_key(
                {"keys": [_rsa_key("AQ")]},
                _token(),
                jwk_loader=lambda value: value,
            )

    def test_even_exponent_is_not_an_acceptable_rsa_public_key(self) -> None:
        """An even RSA public exponent is excluded before duplicate-key counting."""
        with self.assertRaisesRegex(JwksKeySelectionError, "no JWKS key matched"):
            select_rs256_signing_key(
                {"keys": [_rsa_key("BA")]},
                _token(),
                jwk_loader=lambda value: value,
            )

    def test_malformed_duplicate_does_not_poison_unique_valid_key(self) -> None:
        """A malformed same-kid exponent cannot create false duplicate ambiguity."""
        loaded = select_rs256_signing_key(
            {"keys": [_rsa_key("AQAB"), _rsa_key("AQAB==")]},
            _token(),
            jwk_loader=json.loads,
        )
        self.assertEqual(loaded["e"], "AQAB")


if __name__ == "__main__":
    unittest.main()
