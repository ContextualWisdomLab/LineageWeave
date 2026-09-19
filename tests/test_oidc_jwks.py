"""Unit contracts for shared fail-closed OIDC JWKS key selection."""

from __future__ import annotations

import base64
import json

import jwt
import pytest

from lineageweave.oidc_jwks import JwksKeySelectionError, select_rs256_signing_key


def _segment(value: dict[str, object]) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _token(header: dict[str, object]) -> str:
    return f"{_segment(header)}.{_segment({'sub': 'subject'})}.c2ln"


def _rsa_modulus(bits: int = 2048, *, offset: int = 1) -> str:
    value = (1 << (bits - 1)) | offset
    raw = value.to_bytes((bits + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def test_selects_only_the_exact_rs256_verification_key() -> None:
    loaded: list[str] = []
    jwks = {
        "keys": [
            {"kid": "other", "kty": "RSA", "alg": "RS256", "n": "x", "e": "AQAB"},
            {
                "kid": "wanted",
                "kty": "RSA",
                "alg": "RS256",
                "use": "sig",
                "key_ops": ["verify"],
                "n": _rsa_modulus(),
                "e": "AQAB",
            },
        ]
    }

    selected = select_rs256_signing_key(
        jwks,
        _token({"alg": "RS256", "kid": "wanted"}),
        jwk_loader=lambda value: loaded.append(value) or "selected-key",
    )

    assert selected == "selected-key"
    assert len(loaded) == 1
    assert json.loads(loaded[0])["kid"] == "wanted"


def test_rejects_ambiguous_duplicate_verification_keys_before_loading() -> None:
    """A reused ``kid`` must not make provider key ordering security-significant."""
    token = _token({"alg": "RS256", "kid": "wanted"})
    first = {
        "kid": "wanted",
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "key_ops": ["verify"],
        "n": _rsa_modulus(offset=1),
        "e": "AQAB",
    }
    second = {**first, "n": _rsa_modulus(offset=3)}
    loaded: list[str] = []

    with pytest.raises(JwksKeySelectionError) as error:
        select_rs256_signing_key(
            {"keys": [first, second]},
            token,
            jwk_loader=lambda value: loaded.append(value) or object(),
        )

    assert str(error.value) == "multiple acceptable JWKS keys matched access-token kid"
    assert loaded == []


def test_rejects_malformed_token_header_without_leaking_parser_detail() -> None:
    with pytest.raises(JwksKeySelectionError) as error:
        select_rs256_signing_key({"keys": []}, "not-a-jwt")

    assert str(error.value) == "invalid access-token header"


def test_rejects_critical_extensions_even_if_declared_jwt_floor_accepts_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RFC 7515 critical extensions fail closed independent of PyJWT patch level."""
    header = {
        "alg": "RS256",
        "kid": "wanted",
        "crit": ["urn:lineageweave:test-policy"],
        "urn:lineageweave:test-policy": True,
    }
    monkeypatch.setattr(jwt, "get_unverified_header", lambda _token: header)
    key = {
        "kid": "wanted",
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "key_ops": ["verify"],
        "n": _rsa_modulus(),
        "e": "AQAB",
    }

    with pytest.raises(
        JwksKeySelectionError,
        match="critical JOSE header extensions are not supported",
    ):
        select_rs256_signing_key(
            {"keys": [key]},
            "parser-version-independent-token",
            jwk_loader=lambda _value: object(),
        )


@pytest.mark.parametrize(
    ("header", "message"),
    [
        ({"alg": "RS512", "kid": "wanted"}, "access token must use RS256"),
        ({"alg": "RS256"}, "access token must include a non-empty kid"),
        ({"alg": "RS256", "kid": ""}, "access token must include a non-empty kid"),
    ],
)
def test_rejects_unacceptable_token_headers(header: dict[str, object], message: str) -> None:
    with pytest.raises(JwksKeySelectionError, match=message):
        select_rs256_signing_key({"keys": []}, _token(header))


def test_rejects_rsa_modulus_below_rfc7518_minimum_before_loading() -> None:
    """RS256 verification must reject RSA keys shorter than RFC 7518's 2048-bit floor."""
    token = _token({"alg": "RS256", "kid": "wanted"})
    loaded: list[str] = []
    key = {
        "kid": "wanted",
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "key_ops": ["verify"],
        "n": _rsa_modulus(2047),
        "e": "AQAB",
    }

    with pytest.raises(JwksKeySelectionError, match="no JWKS key matched"):
        select_rs256_signing_key(
            {"keys": [key]},
            token,
            jwk_loader=lambda value: loaded.append(value) or object(),
        )

    assert loaded == []


def test_rejects_non_verification_jwks_and_invalid_key_sets() -> None:
    token = _token({"alg": "RS256", "kid": "wanted"})
    rejected = [
        {"kid": "wanted", "kty": "EC"},
        {"kid": "wanted", "kty": "RSA", "alg": "RS512"},
        {"kid": "wanted", "kty": "RSA", "use": "enc"},
        {"kid": "wanted", "kty": "RSA", "key_ops": ["encrypt"]},
        {"kid": "wanted", "kty": "RSA", "key_ops": "verify"},
        {
            "kid": "wanted",
            "kty": "RSA",
            "alg": "RS256",
            "use": "sig",
            "key_ops": ["verify"],
            "n": "",
            "e": "AQAB",
        },
        {
            "kid": "wanted",
            "kty": "RSA",
            "alg": "RS256",
            "use": "sig",
            "key_ops": ["verify"],
            "n": None,
            "e": "AQAB",
        },
        {
            "kid": "wanted",
            "kty": "RSA",
            "alg": "RS256",
            "use": "sig",
            "key_ops": ["verify"],
            "n": "*",
            "e": "AQAB",
        },
    ]

    for key in rejected:
        with pytest.raises(JwksKeySelectionError, match="no JWKS key matched"):
            select_rs256_signing_key({"keys": [key]}, token, jwk_loader=lambda _value: object())

    with pytest.raises(JwksKeySelectionError, match="no JWKS key matched"):
        select_rs256_signing_key({"keys": "not-a-list"}, token)


def test_hides_matching_jwk_parse_failures() -> None:
    token = _token({"alg": "RS256", "kid": "wanted"})
    key = {
        "kid": "wanted",
        "kty": "RSA",
        "alg": "RS256",
        "n": _rsa_modulus(),
        "e": "AQAB",
    }

    for failure in (ValueError("provider detail"), jwt.InvalidKeyError("provider detail")):
        def fail_loader(_value: str, *, _failure: Exception = failure) -> object:
            raise _failure

        with pytest.raises(JwksKeySelectionError) as error:
            select_rs256_signing_key({"keys": [key]}, token, jwk_loader=fail_loader)

        assert str(error.value) == "matching JWKS key is invalid"
        assert "provider detail" not in str(error.value)
