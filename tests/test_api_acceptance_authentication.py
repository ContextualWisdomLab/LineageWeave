"""Keep authorized synthetic API acceptance independent of password grants."""

from backend.tests import test_api as api_tests

import pytest


def test_owned_token_does_not_request_password_grant(tmp_path, monkeypatch) -> None:
    """An approved sign-in token enters only the existing JWKS-verified API path."""
    token_file = tmp_path / "token"
    token_file.write_text(" synthetic-opaque-token\n", encoding="utf-8")
    monkeypatch.setenv("LINEAGEWEAVE_TEST_ACCESS_TOKEN_FILE", str(token_file))

    def forbidden_grant(*args, **kwargs):
        raise AssertionError("password grant must not be requested")

    monkeypatch.setattr(api_tests, "post_form", forbidden_grant)
    token = api_tests._fetch_demo_analyst_token()
    assert token == "synthetic-opaque-token"
    assert "synthetic-opaque-token" not in repr(token)


@pytest.mark.parametrize("content", [None, "", " \n", b"\xff"])
def test_unavailable_owned_token_never_falls_back(content, tmp_path, monkeypatch) -> None:
    """File failure stays a failed acceptance attempt without leaking file content."""
    token_file = tmp_path / "token"
    if content is not None:
        token_file.write_bytes(content if isinstance(content, bytes) else content.encode())
    monkeypatch.setenv("LINEAGEWEAVE_TEST_ACCESS_TOKEN_FILE", str(token_file))

    def forbidden_grant(*args, **kwargs):
        raise AssertionError("password grant must not be requested")

    monkeypatch.setattr(api_tests, "post_form", forbidden_grant)
    with pytest.raises(RuntimeError, match="^Synthetic acceptance token is unavailable; sign in again$"):
        api_tests._fetch_demo_analyst_token()


def test_explicit_synthetic_grant_remains_available(monkeypatch) -> None:
    """Without a supplied file, the separately enabled synthetic path is retained."""
    monkeypatch.delenv("LINEAGEWEAVE_TEST_ACCESS_TOKEN_FILE", raising=False)
    calls = []

    def granted_token(url, payload, **kwargs):
        calls.append(payload)
        return {"access_token": "synthetic-opaque-token"}

    monkeypatch.setattr(api_tests, "post_form", granted_token)
    assert api_tests._fetch_demo_analyst_token() == "synthetic-opaque-token"
    assert len(calls) == 1
    assert calls[0]["grant_type"] == "password"
    assert calls[0]["client_id"] == "lineageweave-frontend"
    assert calls[0]["username"] == "demo.analyst"
