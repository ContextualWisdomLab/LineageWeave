"""Telemetry configuration paths that require endpoint/SDK fixtures.

``observability.configure_telemetry`` and the OTLP endpoint helpers have
environment-gated success branches the base suite cannot exercise without
risking provider teardown. This module monkeypatches the OpenTelemetry
provider setters and environment so every line of the configuration and
attribute-safety paths runs against synthetic values only.
"""

from __future__ import annotations

import logging

import pytest

import lineageweave.observability as observability


def _signal_endpoint(endpoint: str, signal: str) -> str:
    """Thin wrapper so callers pass one helper under test."""
    return observability._otlp_signal_endpoint(endpoint, signal)


def test_signal_endpoint_appends_default_signal_suffixes() -> None:
    """A bare base endpoint receives one explicit per-signal suffix."""
    assert _signal_endpoint("http://127.0.0.1:4318", "metrics") == (
        "http://127.0.0.1:4318/v1/metrics"
    )
    assert _signal_endpoint("http://127.0.0.1:4318", "logs") == (
        "http://127.0.0.1:4318/v1/logs"
    )
    assert _signal_endpoint("http://127.0.0.1:4318", "traces") == (
        "http://127.0.0.1:4318/v1/traces"
    )


def test_signal_endpoint_preserves_an_existing_signal_suffix() -> None:
    """A base that already names the signal is not suffixed twice."""
    assert _signal_endpoint("http://127.0.0.1:4318/v1/metrics", "metrics") == (
        "http://127.0.0.1:4318/v1/metrics"
    )
    assert _signal_endpoint("http://127.0.0.1:4318/v1/logs", "logs") == (
        "http://127.0.0.1:4318/v1/logs"
    )
    assert _signal_endpoint("http://127.0.0.1:4318/v1/traces", "traces") == (
        "http://127.0.0.1:4318/v1/traces"
    )
    # The suffix match is case-insensitive on the trailing path.
    assert _signal_endpoint("http://127.0.0.1:4318/V1/METRICS", "metrics") == (
        "http://127.0.0.1:4318/V1/METRICS"
    )


def test_signal_endpoint_handles_a_trailing_slash() -> None:
    """Trailing slashes are stripped before appending the signal suffix."""
    assert _signal_endpoint("http://127.0.0.1:4318/", "metrics") == (
        "http://127.0.0.1:4318/v1/metrics"
    )


def test_metric_and_log_endpoint_helpers_route_to_their_signals() -> None:
    """The typed helpers select metrics and logs respectively."""
    assert observability._otlp_metric_endpoint("http://127.0.0.1:4318") == (
        "http://127.0.0.1:4318/v1/metrics"
    )
    assert observability._otlp_log_endpoint("http://127.0.0.1:4318") == (
        "http://127.0.0.1:4318/v1/logs"
    )


def test_safe_attributes_skips_container_values_and_unknown_keys() -> None:
    """Composite and unlisted attribute values never reach a span."""
    sanitized = observability._safe_attributes(
        {
            "lineageweave.operation_code": "http_post_json",
            "lineageweave.session_id": "post-123",
            "nested": {"a": 1},
            "items": [1, 2, 3],
            "unlisted_key": "should-not-appear",
        }
    )
    assert sanitized["lineageweave.operation_code"] == "http_post_json"
    assert sanitized["lineageweave.session_id"] == "post-123"
    assert "nested" not in sanitized
    assert "items" not in sanitized
    assert "unlisted_key" not in sanitized


def test_safe_attributes_bounds_string_length_and_keeps_scalars() -> None:
    """Long strings truncate at 256 and numbers pass through unmodified."""
    long_value = "x" * 400
    sanitized = observability._safe_attributes(
        {
            "lineageweave.operation_code": long_value,
            "lineageweave.failure_outcome": "internal_error",
        }
    )
    assert len(sanitized["lineageweave.operation_code"]) == 256
    assert sanitized["lineageweave.failure_outcome"] == "internal_error"


def test_configure_telemetry_success_installs_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With an OTLP endpoint, all three signal providers are configured."""
    import opentelemetry._logs as otel_logs
    import opentelemetry.metrics as otel_metrics
    import opentelemetry.trace as otel_trace

    trace_providers: list[object] = []
    metric_providers: list[object] = []
    log_providers: list[object] = []

    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:9")
    monkeypatch.setattr(observability, "_CONFIGURED", False)
    monkeypatch.setattr(otel_trace, "set_tracer_provider", trace_providers.append)
    monkeypatch.setattr(otel_metrics, "set_meter_provider", metric_providers.append)
    monkeypatch.setattr(otel_logs, "set_logger_provider", log_providers.append)

    observability.configure_telemetry("services/synthetic")

    assert observability._CONFIGURED is True
    assert observability._TRACE_PROVIDER is not None
    assert trace_providers == [observability._TRACE_PROVIDER]
    assert metric_providers == [observability._METER_PROVIDER]
    assert log_providers == [observability._LOG_PROVIDER]
    assert isinstance(observability._LOG_HANDLER, logging.Handler)

    # Restore the module to a clean, unconfigured state for the rest of the suite.
    observability.shutdown_telemetry()
    monkeypatch.setattr(observability, "_CONFIGURED", False)
    monkeypatch.setattr(observability, "_TRACE_PROVIDER", None)
    monkeypatch.setattr(observability, "_METER_PROVIDER", None)
    monkeypatch.setattr(observability, "_LOG_PROVIDER", None)
    monkeypatch.setattr(observability, "_LOG_HANDLER", None)


def test_configure_telemetry_returns_when_sdk_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OTEL_SDK_DISABLED short-circuits without touching the providers."""
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:9")
    monkeypatch.setattr(observability, "_CONFIGURED", False)

    observability.configure_telemetry("services/synthetic")

    assert observability._CONFIGURED is False
    assert observability._TRACE_PROVIDER is None


def test_configure_telemetry_returns_without_an_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unset OTLP endpoint leaves telemetry unconfigured."""
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setattr(observability, "_CONFIGURED", False)

    observability.configure_telemetry("services/synthetic")

    assert observability._CONFIGURED is False
    assert observability._TRACE_PROVIDER is None


def test_shutdown_telemetry_removes_handler_and_nulls_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Shutdown detaches the log handler and resets the provider globals."""
    monkeypatch.setattr(observability, "_TRACE_PROVIDER", object())
    monkeypatch.setattr(observability, "_METER_PROVIDER", object())
    monkeypatch.setattr(observability, "_LOG_PROVIDER", object())
    fake_handler = logging.Handler()
    monkeypatch.setattr(observability, "_LOG_HANDLER", fake_handler)

    observability.shutdown_telemetry()

    assert observability._LOG_HANDLER is None
    assert observability._TRACE_PROVIDER is None
    assert observability._METER_PROVIDER is None
    assert observability._LOG_PROVIDER is None
    assert fake_handler not in logging.getLogger().handlers