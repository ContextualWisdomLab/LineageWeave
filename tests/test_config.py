from __future__ import annotations

import pytest

from backend.app import config


def test_load_settings_prefers_gateway_environment(monkeypatch) -> None:
    monkeypatch.setenv("LLM_GATEWAY_URL", "https://gateway.example")
    monkeypatch.setenv("LLM_GATEWAY_API_KEY", "gateway-key")
    monkeypatch.setenv("ORCHESTRATOR_BASE_URL", "https://legacy.example")
    monkeypatch.setenv("ORCHESTRATOR_API_KEY", "legacy-key")

    settings = config.load_settings()

    assert settings.orchestrator_base_url == "https://gateway.example"
    assert settings.orchestrator_api_key == "gateway-key"


def test_load_settings_reads_gateway_values_from_home_dotenv(monkeypatch, tmp_path) -> None:
    for name in (
        "LLM_GATEWAY_URL",
        "LLM_GATEWAY_API_URL",
        "LLM_GATEWAY_API_KEY",
        "ORCHESTRATOR_BASE_URL",
        "ORCHESTRATOR_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    (tmp_path / ".env").write_text(
        'LLM_GATEWAY_API_URL="https://dotenv.example/v1"\n'
        "LLM_GATEWAY_API_KEY=dotenv-key\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config.Path, "home", lambda: tmp_path)

    settings = config.load_settings()

    assert settings.orchestrator_base_url == "https://dotenv.example/v1"
    assert settings.orchestrator_api_key == "dotenv-key"


def test_load_settings_applies_bounded_mcp_rate_limit_policy(monkeypatch) -> None:
    monkeypatch.setenv("MCP_GLOBAL_ASK_RATE_LIMIT", "7")
    monkeypatch.setenv("MCP_GLOBAL_ASK_RATE_WINDOW_SECONDS", "90")
    monkeypatch.setenv("MCP_RATE_LIMIT_UNAVAILABLE_RETRY_SECONDS", "11")

    settings = config.load_settings()

    assert settings.mcp_global_ask_rate_limit == 7
    assert settings.mcp_global_ask_rate_window_seconds == 90
    assert settings.mcp_rate_limit_unavailable_retry_seconds == 11


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("MCP_GLOBAL_ASK_RATE_LIMIT", "0"),
        ("MCP_GLOBAL_ASK_RATE_LIMIT", "10001"),
        ("MCP_GLOBAL_ASK_RATE_WINDOW_SECONDS", "0"),
        ("MCP_GLOBAL_ASK_RATE_WINDOW_SECONDS", "86401"),
        ("MCP_RATE_LIMIT_UNAVAILABLE_RETRY_SECONDS", "0"),
        ("MCP_RATE_LIMIT_UNAVAILABLE_RETRY_SECONDS", "301"),
        ("MCP_GLOBAL_ASK_RATE_LIMIT", "not-a-number"),
    ],
)
def test_invalid_mcp_rate_limit_policy_prevents_startup(monkeypatch, name: str, value: str) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=name):
        config.load_settings()
