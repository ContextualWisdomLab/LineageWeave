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


def test_rankweave_disabled_defaults_off(monkeypatch) -> None:
    monkeypatch.delenv("RANKWEAVE_DISABLED", raising=False)
    assert load_settings().rankweave_disabled is False


def test_rankweave_disabled_flag_is_opt_in(monkeypatch) -> None:
    monkeypatch.setenv("RANKWEAVE_DISABLED", "1")
    assert load_settings().rankweave_disabled is True
