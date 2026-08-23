"""Configuration contracts for MCP request-byte admission."""

from __future__ import annotations

import pytest

from backend.app.config import _bounded_int_setting, load_settings


def test_bounded_integer_setting_uses_default_and_explicit_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing value uses the safe default and a valid override is accepted."""
    monkeypatch.delenv("TEST_BOUNDED_INTEGER", raising=False)
    assert _bounded_int_setting(
        "TEST_BOUNDED_INTEGER",
        64,
        minimum=8,
        maximum=128,
    ) == 64
    monkeypatch.setenv("TEST_BOUNDED_INTEGER", "96")
    assert _bounded_int_setting(
        "TEST_BOUNDED_INTEGER",
        64,
        minimum=8,
        maximum=128,
    ) == 96


@pytest.mark.parametrize("raw_value", ["not-a-number", "8.5", ""])
def test_bounded_integer_setting_rejects_non_integer(
    monkeypatch: pytest.MonkeyPatch,
    raw_value: str,
) -> None:
    """Malformed values fail during settings construction rather than at runtime."""
    monkeypatch.setenv("TEST_BOUNDED_INTEGER", raw_value)
    with pytest.raises(ValueError, match="must be a base-10 integer"):
        _bounded_int_setting(
            "TEST_BOUNDED_INTEGER",
            64,
            minimum=8,
            maximum=128,
        )


@pytest.mark.parametrize("raw_value", ["7", "129"])
def test_bounded_integer_setting_rejects_out_of_range(
    monkeypatch: pytest.MonkeyPatch,
    raw_value: str,
) -> None:
    """A value outside the explicit resource envelope fails closed."""
    monkeypatch.setenv("TEST_BOUNDED_INTEGER", raw_value)
    with pytest.raises(ValueError, match="must be between 8 and 128"):
        _bounded_int_setting(
            "TEST_BOUNDED_INTEGER",
            64,
            minimum=8,
            maximum=128,
        )


def test_load_settings_exposes_validated_mcp_request_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The public environment contract reaches the immutable Settings object."""
    monkeypatch.setenv("MCP_MAX_REQUEST_BYTES", "32768")
    assert load_settings().mcp_max_request_bytes == 32768


def test_load_settings_exposes_validated_mcp_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_RATE_LIMIT_REQUESTS", "45")
    monkeypatch.setenv("MCP_RATE_LIMIT_WINDOW_SECONDS", "90")
    settings = load_settings()
    assert settings.mcp_rate_limit_requests == 45
    assert settings.mcp_rate_limit_window_seconds == 90


@pytest.mark.parametrize(
    ("name", "value"),
    [("MCP_RATE_LIMIT_REQUESTS", "0"), ("MCP_RATE_LIMIT_WINDOW_SECONDS", "3601")],
)
def test_load_settings_rejects_invalid_mcp_rate_limit(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError):
        load_settings()


@pytest.mark.parametrize("raw_value", ["8191", "1048577", "invalid"])
def test_load_settings_rejects_invalid_mcp_request_limit(
    monkeypatch: pytest.MonkeyPatch,
    raw_value: str,
) -> None:
    """Unsafe MCP limits prevent process startup rather than silently drifting."""
    monkeypatch.setenv("MCP_MAX_REQUEST_BYTES", raw_value)
    with pytest.raises(ValueError):
        load_settings()
