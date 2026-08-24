"""Unit tests for the orchestrator failure boundary (issue #361).

The boundary is the seam between honest customer-facing 503s and operator
diagnosability. These tests prove, without a live orchestrator or database:

- known provider/transport/schema exceptions classify as
  ``orchestrator_provider_unavailable`` (warning level, no stack trace
  requirement) and raise one generic 503;
- unexpected exceptions (an injected ``AttributeError`` stands in for any
  programming defect) classify as ``orchestrator_internal_fault`` at error
  level *with* a stack trace and raise the same generic 503;
- the raw exception message never reaches the HTTP caller;
- exception chaining survives (``__cause__`` keeps the original error);
- log records carry operation code, correlation id, event name, and the
  exception class only -- never prompt text, response text, tokens, or keys;
- counters separate provider-unavailable from internal-fault events per
  operation, and stay bounded to the call sites actually used.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from backend.app.orchestrator_boundary import (
    EVENT_INTERNAL_FAULT,
    EVENT_PROVIDER_UNAVAILABLE,
    boundary_counters,
    new_correlation_id,
    orchestrator_boundary,
)
from lineageweave.http_client import HttpClientError


@pytest.fixture()
def _fresh_boundary_state():
    """Isolate correlation context and counters per test."""
    new_correlation_id("")
    from backend.app import orchestrator_boundary as module

    module._counters.clear()
    yield
    module._counters.clear()


def _raise(exc: Exception) -> None:
    raise exc


def test_known_provider_error_classifies_as_provider_unavailable(
    caplog: pytest.LogCaptureFixture, _fresh_boundary_state
) -> None:
    """An HttpClientError becomes a warning-level provider-unavailable 503."""
    with caplog.at_level(logging.WARNING):
        with pytest.raises(HTTPException) as excinfo:
            with orchestrator_boundary("global_ask", "Ask Agent is unavailable"):
                _raise(HttpClientError("provider socket reset mid-answer"))

    assert excinfo.value.status_code == 503
    # The raw exception message must not reach the caller.
    assert "socket reset" not in str(excinfo.value.detail)
    record = next(r for r in caplog.records if r.__dict__.get("event") == EVENT_PROVIDER_UNAVAILABLE)
    assert record.levelno == logging.WARNING
    assert record.operation_code == "global_ask"
    assert record.exception_class == "HttpClientError"


def test_unexpected_defect_classifies_as_internal_fault_with_stack(
    caplog: pytest.LogCaptureFixture, _fresh_boundary_state
) -> None:
    """An AttributeError-style defect gets an error-level trace + same 503."""
    with caplog.at_level(logging.ERROR):
        with pytest.raises(HTTPException) as excinfo:
            with orchestrator_boundary("global_ask", "Ask Agent is unavailable"):
                _raise(AttributeError("'NoneType' object has no attribute 'answer'"))

    assert excinfo.value.status_code == 503
    record = next(r for r in caplog.records if r.__dict__.get("event") == EVENT_INTERNAL_FAULT)
    assert record.levelno == logging.ERROR
    assert record.exc_info is not None, "internal faults must carry a stack trace"
    assert record.exception_class == "AttributeError"


def test_success_path_raises_nothing_and_logs_nothing(
    caplog: pytest.LogCaptureFixture, _fresh_boundary_state
) -> None:
    """A clean client call passes through untouched, without boundary events."""
    sentinel = MagicMock(return_value="answer")
    with caplog.at_level(logging.DEBUG):
        with orchestrator_boundary("global_ask", "Ask Agent is unavailable"):
            result = sentinel("q", [])
    assert result == "answer"
    sentinel.assert_called_once_with("q", [])
    assert not [r for r in caplog.records if hasattr(r, "event")]


def test_exception_chaining_is_preserved(_fresh_boundary_state) -> None:
    """``raise ... from exc`` semantics survive both classification paths."""
    original = HttpClientError("transport down")
    with pytest.raises(HTTPException) as excinfo:
        with orchestrator_boundary("global_ask", "unavailable"):
            _raise(original)
    assert excinfo.value.__cause__ is original


def test_log_records_exclude_sensitive_fields(
    caplog: pytest.LogCaptureFixture, _fresh_boundary_state
) -> None:
    """Prompt/response/token/key strings may never appear in boundary logs."""
    secret_prompt = "confidential question about tenant payroll"
    secret_token = "Bearer eyJhbGciOi-secret-value"
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(HTTPException):
            with orchestrator_boundary("global_ask", "Ask Agent is unavailable"):
                _raise(HttpClientError(f"request rejected carrying {secret_token}"))
    for record in caplog.records:
        rendered = record.getMessage() + " ".join(
            str(value) for key, value in record.__dict__.items() if key != "message"
        )
        assert secret_prompt not in rendered
        assert secret_token not in rendered
        assert "rejected carrying" not in rendered


def test_correlation_id_flows_into_records(
    caplog: pytest.LogCaptureFixture, _fresh_boundary_state
) -> None:
    """The installed correlation id lands on every boundary record."""
    new_correlation_id("corr-123")
    with caplog.at_level(logging.WARNING):
        with pytest.raises(HTTPException):
            with orchestrator_boundary("global_ask", "unavailable"):
                _raise(HttpClientError("down"))
    record = next(r for r in caplog.records if hasattr(r, "correlation_id"))
    assert record.correlation_id == "corr-123"


def test_counters_separate_events_per_operation(_fresh_boundary_state) -> None:
    """Provider-unavailable and internal-fault count independently."""
    for _ in range(3):
        with pytest.raises(HTTPException):
            with orchestrator_boundary("global_ask", "unavailable"):
                _raise(HttpClientError("down"))
    with pytest.raises(HTTPException):
        with orchestrator_boundary("global_ask", "unavailable"):
            _raise(AttributeError("unexpected defect"))

    snapshot = boundary_counters()
    assert snapshot[(EVENT_PROVIDER_UNAVAILABLE, "global_ask")] == 3
    assert snapshot[(EVENT_INTERNAL_FAULT, "global_ask")] == 1


def test_operation_code_vocabulary_stays_bounded(_fresh_boundary_state) -> None:
    """Only fixed call-site operation codes keep metric cardinality bounded."""
    allowed = {"global_ask", "post_chat"}
    for operation in sorted(allowed):
        with pytest.raises(HTTPException):
            with orchestrator_boundary(operation, "unavailable"):
                _raise(HttpClientError("down"))
    snapshot = boundary_counters()
    assert {operation for (_, operation) in snapshot} <= allowed
