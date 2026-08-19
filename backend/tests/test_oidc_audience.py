"""OIDC resource-audience configuration regressions."""

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


def test_external_oidc_defaults_audience_to_client_id(monkeypatch) -> None:
    monkeypatch.delenv("KEYVERSE_ISSUER", raising=False)
    monkeypatch.setenv("OIDC_ISSUER", "https://id.example")
    monkeypatch.setenv("OIDC_CLIENT_ID", "lineageweave-resource")
    monkeypatch.delenv("OIDC_AUDIENCE", raising=False)
    assert load_settings().oidc_audience == "lineageweave-resource"
