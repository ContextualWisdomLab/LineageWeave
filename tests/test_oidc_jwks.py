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
                "n": "y",
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
        "n": "first",
        "e": "AQAB",
    }
    second = {**first, "n": "second"}
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


def test_rejects_non_verification_jwks_and_invalid_key_sets() -> None:
    token = _token({"alg": "RS256", "kid": "wanted"})
    rejected = [
        {"kid": "wanted", "kty": "EC"},
        {"kid": "wanted", "kty": "RSA", "alg": "RS512"},
        {"kid": "wanted", "kty": "RSA", "use": "enc"},
        {"kid": "wanted", "kty": "RSA", "key_ops": ["encrypt"]},
        {"kid": "wanted", "kty": "RSA", "key_ops": "verify"},
    ]

    for key in rejected:
        with pytest.raises(JwksKeySelectionError, match="no JWKS key matched"):
            select_rs256_signing_key({"keys": [key]}, token, jwk_loader=lambda _value: object())

    with pytest.raises(JwksKeySelectionError, match="no JWKS key matched"):
        select_rs256_signing_key({"keys": "not-a-list"}, token)


def test_hides_matching_jwk_parse_failures() -> None:
    token = _token({"alg": "RS256", "kid": "wanted"})
    key = {"kid": "wanted", "kty": "RSA", "alg": "RS256", "n": "bad", "e": "AQAB"}

    for failure in (ValueError("provider detail"), jwt.InvalidKeyError("provider detail")):
        def fail_loader(_value: str, *, _failure: Exception = failure) -> object:
            raise _failure

        with pytest.raises(JwksKeySelectionError) as error:
            select_rs256_signing_key({"keys": [key]}, token, jwk_loader=fail_loader)

        assert str(error.value) == "matching JWKS key is invalid"
        assert "provider detail" not in str(error.value)
