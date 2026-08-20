"""OIDC resource-audience configuration regressions."""

import pytest

from backend.app.config import load_settings


def test_local_oidc_audience_defaults_to_backend_resource(monkeypatch) -> None:
    monkeypatch.delenv("KEYVERSE_ISSUER", raising=False)
    monkeypatch.delenv("OIDC_ISSUER", raising=False)
    monkeypatch.delenv("KEYVERSE_AUDIENCE", raising=False)
    monkeypatch.delenv("OIDC_AUDIENCE", raising=False)
    assert load_settings().oidc_audience == "lineageweave-api"


def test_keyverse_audience_is_explicitly_configurable(monkeypatch) -> None:
    monkeypatch.setenv("KEYVERSE_ISSUER", "https://keyverse.example/tenant/acme")
    monkeypatch.setenv("KEYVERSE_CLIENT_ID", "lineageweave-browser")
    monkeypatch.setenv("KEYVERSE_AUDIENCE", "https://lineage.example/api")
    assert load_settings().oidc_audience == "https://lineage.example/api"


def test_external_oidc_requires_explicit_resource_audience(monkeypatch) -> None:
    monkeypatch.delenv("KEYVERSE_ISSUER", raising=False)
    monkeypatch.setenv("OIDC_ISSUER", "https://id.example")
    monkeypatch.setenv("OIDC_CLIENT_ID", "lineageweave-browser")
    monkeypatch.delenv("KEYVERSE_AUDIENCE", raising=False)
    monkeypatch.delenv("OIDC_AUDIENCE", raising=False)

    with pytest.raises(ValueError, match="external OIDC requires"):
        load_settings()


def test_generic_external_oidc_accepts_explicit_resource_audience(monkeypatch) -> None:
    monkeypatch.delenv("KEYVERSE_ISSUER", raising=False)
    monkeypatch.setenv("OIDC_ISSUER", "https://id.example")
    monkeypatch.setenv("OIDC_CLIENT_ID", "lineageweave-browser")
    monkeypatch.setenv("OIDC_AUDIENCE", "https://lineage.example/api")

    settings = load_settings()

    assert settings.oidc_client_id == "lineageweave-browser"
    assert settings.oidc_audience == "https://lineage.example/api"
