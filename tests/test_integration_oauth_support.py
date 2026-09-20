"""Focused tests for the local backend integration OAuth helper."""

from __future__ import annotations

import pytest

from backend.tests import integration_oauth_support as oauth


def test_viewer_machine_token_uses_client_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, str], float]] = []

    def fake_post_form(url: str, form: dict[str, str], *, timeout: float):
        calls.append((url, form, timeout))
        return {"access_token": "viewer-token"}

    monkeypatch.setattr(oauth, "post_form", fake_post_form)
    monkeypatch.setenv("KEYCLOAK_CLIENT_SECRET", "viewer-secret")

    assert oauth.fetch_viewer_machine_token("https://keycloak.test") == "viewer-token"
    assert calls == [
        (
            "https://keycloak.test/realms/lineageweave-demo/protocol/openid-connect/token",
            {
                "grant_type": "client_credentials",
                "client_id": "lineageweave-test-automation",
                "client_secret": "viewer-secret",
            },
            10,
        )
    ]


def test_default_keycloak_base_url_honors_integration_env(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_post_form(url: str, _form: dict[str, str], *, timeout: float):
        assert timeout == 10
        calls.append(url)
        return {"access_token": "viewer-token"}

    monkeypatch.setattr(oauth, "post_form", fake_post_form)
    monkeypatch.setenv("LINEAGEWEAVE_TEST_KEYCLOAK_BASE_URL", "https://keycloak.override")
    monkeypatch.setenv("KEYCLOAK_CLIENT_SECRET", "viewer-secret")

    assert oauth.fetch_viewer_machine_token() == "viewer-token"
    assert calls == [
        "https://keycloak.override/realms/lineageweave-demo/protocol/openid-connect/token"
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


def test_empty_secret_env_matches_local_compose_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """An explicitly empty local env must resolve like Compose's ``:-`` default."""
    calls: list[dict[str, str]] = []

    def fake_post_form(_url: str, form: dict[str, str], *, timeout: float):
        assert timeout == 10
        calls.append(form)
        return {"access_token": f"{form['client_id']}-token"}

    monkeypatch.setattr(oauth, "post_form", fake_post_form)
    monkeypatch.setenv("KEYCLOAK_CLIENT_SECRET", "")
    monkeypatch.setenv("KEYCLOAK_TEST_ADMIN_CLIENT_SECRET", "")

    assert oauth.fetch_viewer_machine_token() == "lineageweave-test-automation-token"
    assert oauth.fetch_admin_machine_token() == "lineageweave-test-admin-token"
    assert [call["client_secret"] for call in calls] == [
        "lineageweave_test_automation_dev_only",
        "lineageweave_test_admin_dev_only",
    ]


@pytest.mark.parametrize(
    ("fetch_token", "secret_env"),
    [
        (oauth.fetch_viewer_machine_token, "KEYCLOAK_CLIENT_SECRET"),
        (oauth.fetch_admin_machine_token, "KEYCLOAK_TEST_ADMIN_CLIENT_SECRET"),
    ],
)
def test_non_loopback_client_credentials_require_https(
    monkeypatch: pytest.MonkeyPatch,
    fetch_token,
    secret_env: str,
) -> None:
    """OAuth client credentials must not cross a non-loopback cleartext token endpoint."""
    monkeypatch.setenv(
        "LINEAGEWEAVE_TEST_KEYCLOAK_BASE_URL",
        "http://keycloak.remote.example",
    )
    monkeypatch.setenv(secret_env, "operator-secret")
    monkeypatch.setattr(
        oauth,
        "post_form",
        lambda *_args, **_kwargs: pytest.fail(
            "non-loopback cleartext OAuth endpoint must fail before token I/O"
        ),
    )

    with pytest.raises(RuntimeError, match="HTTPS"):
        fetch_token()


@pytest.mark.parametrize(
    ("fetch_token", "secret_env"),
    [
        (oauth.fetch_viewer_machine_token, "KEYCLOAK_CLIENT_SECRET"),
        (oauth.fetch_admin_machine_token, "KEYCLOAK_TEST_ADMIN_CLIENT_SECRET"),
    ],
)
@pytest.mark.parametrize("secret_state", ("unset", "empty"))
def test_dev_secret_fallback_is_loopback_only(
    monkeypatch: pytest.MonkeyPatch,
    fetch_token,
    secret_env: str,
    secret_state: str,
) -> None:
    """Synthetic local secrets must never be sent to a non-loopback issuer."""
    monkeypatch.setenv(
        "LINEAGEWEAVE_TEST_KEYCLOAK_BASE_URL",
        "https://keycloak.remote.example",
    )
    if secret_state == "unset":
        monkeypatch.delenv(secret_env, raising=False)
    else:
        monkeypatch.setenv(secret_env, "")
    monkeypatch.setattr(
        oauth,
        "post_form",
        lambda *_args, **_kwargs: pytest.fail(
            "remote Keycloak must not receive a synthetic local fallback secret"
        ),
    )

    with pytest.raises(RuntimeError, match=secret_env):
        fetch_token()
