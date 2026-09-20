"""Focused tests for the local backend integration OAuth helper."""

from __future__ import annotations

import pytest

from tests import integration_oauth_support as oauth


def test_viewer_machine_token_uses_client_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, str], float]] = []

    def fake_post_form(url: str, form: dict[str, str], *, timeout: float):
        calls.append((url, form, timeout))
        return {"access_token": "viewer-token"}

    monkeypatch.setattr(oauth, "post_form", fake_post_form)
    monkeypatch.setenv("KEYCLOAK_CLIENT_SECRET", "viewer-secret")

    assert oauth.fetch_viewer_machine_token("http://keycloak.test") == "viewer-token"
    assert calls == [
        (
            "http://keycloak.test/realms/lineageweave-demo/protocol/openid-connect/token",
            {
                "grant_type": "client_credentials",
                "client_id": "lineageweave-test-automation",
                "client_secret": "viewer-secret",
            },
            10,
        )
    ]


def test_admin_machine_token_is_a_distinct_client(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, str]] = []

    def fake_post_form(_url: str, form: dict[str, str], *, timeout: float):
        assert timeout == 10
        calls.append(form)
        return {"access_token": "admin-token"}

    monkeypatch.setattr(oauth, "post_form", fake_post_form)
    monkeypatch.setenv("KEYCLOAK_TEST_ADMIN_CLIENT_SECRET", "admin-secret")

    assert oauth.fetch_admin_machine_token() == "admin-token"
    assert calls == [
        {
            "grant_type": "client_credentials",
            "client_id": "lineageweave-test-admin",
            "client_secret": "admin-secret",
        }
    ]


def test_machine_token_rejects_a_missing_access_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(oauth, "post_form", lambda *_args, **_kwargs: {})

    with pytest.raises(RuntimeError, match="did not contain access_token"):
        oauth.fetch_viewer_machine_token()
