"""Settings parsing tests that do not need a live Postgres or Keycloak."""

from __future__ import annotations

from backend.app.config import load_settings


def test_frontend_origins_are_parsed_from_comma_separated_env(monkeypatch) -> None:
    """CORS allow-list is an explicit env CSV, never a wildcard default."""
    monkeypatch.setenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173, http://localhost:15173",
    )
    settings = load_settings()
    assert settings.frontend_origins == [
        "http://localhost:5173",
        "http://localhost:15173",
    ]


def test_frontend_origins_drop_blank_entries(monkeypatch) -> None:
    monkeypatch.setenv("FRONTEND_ORIGINS", "http://localhost:5173,,")
    assert load_settings().frontend_origins == ["http://localhost:5173"]


def test_oidc_clock_skew_is_bounded(monkeypatch) -> None:
    monkeypatch.setenv("OIDC_CLOCK_SKEW_SECONDS", "12")
    assert load_settings().oidc_clock_skew_seconds == 12

    monkeypatch.setenv("OIDC_CLOCK_SKEW_SECONDS", "61")
    try:
        load_settings()
    except ValueError as exc:
        assert "between 0 and 60" in str(exc)
    else:
        raise AssertionError("clock skew above the bound must be rejected")


def test_tepp_transport_url_defaults_empty_and_is_not_a_score(monkeypatch) -> None:
    """Missing TEPP_TRANSPORT_URL keeps the channel dropped."""
    monkeypatch.delenv("TEPP_TRANSPORT_URL", raising=False)
    assert load_settings().tepp_transport_url == ""
    monkeypatch.setenv("TEPP_TRANSPORT_URL", "https://tepp.example/v1/analysis-runs")
    assert load_settings().tepp_transport_url == "https://tepp.example/v1/analysis-runs"


def test_keyverse_issuer_overrides_local_keycloak_and_uses_oidc_discovery(monkeypatch) -> None:
    """Production Keyverse configuration is standard OIDC, not a local mock."""
    monkeypatch.setenv("KEYVERSE_ISSUER", "https://keyverse.example/tenant/acme")
    monkeypatch.setenv("KEYVERSE_CLIENT_ID", "lineageweave-production")
    monkeypatch.setenv("KEYVERSE_AUDIENCE", "lineageweave-api")
    monkeypatch.delenv("KEYVERSE_DISCOVERY_URI", raising=False)
    monkeypatch.delenv("KEYVERSE_JWKS_URI", raising=False)

    settings = load_settings()

    assert settings.oidc_issuer == "https://keyverse.example/tenant/acme"
    assert settings.oidc_client_id == "lineageweave-production"
    assert settings.oidc_discovery_uri == (
        "https://keyverse.example/tenant/acme/.well-known/openid-configuration"
    )
    assert settings.oidc_jwks_uri_override == ""


def test_local_keycloak_discovery_uses_backend_reachable_base_url(monkeypatch) -> None:
    """Compose discovery uses service DNS, not the browser's localhost issuer."""
    monkeypatch.delenv("KEYVERSE_ISSUER", raising=False)
    monkeypatch.delenv("OIDC_ISSUER", raising=False)
    monkeypatch.delenv("KEYVERSE_DISCOVERY_URI", raising=False)
    monkeypatch.delenv("OIDC_DISCOVERY_URI", raising=False)
    monkeypatch.setenv("KEYCLOAK_BASE_URL", "http://keycloak:8080")
    monkeypatch.setenv("KEYCLOAK_ISSUER", "http://localhost:18080/realms/lineageweave-demo")

    settings = load_settings()

    assert settings.oidc_issuer == "http://localhost:18080/realms/lineageweave-demo"
    assert settings.oidc_discovery_uri == (
        "http://keycloak:8080/realms/lineageweave-demo/.well-known/openid-configuration"
    )
    assert settings.oidc_jwks_uri_override == (
        "http://keycloak:8080/realms/lineageweave-demo/protocol/openid-connect/certs"
    )


def test_rankweave_disabled_defaults_off(monkeypatch) -> None:
    monkeypatch.delenv("RANKWEAVE_DISABLED", raising=False)
    assert load_settings().rankweave_disabled is False


def test_rankweave_disabled_flag_is_opt_in(monkeypatch) -> None:
    monkeypatch.setenv("RANKWEAVE_DISABLED", "1")
    assert load_settings().rankweave_disabled is True
