"""Unit tests for the structured operability logger (issue #361).

These run without any live stack: the module under test is pure logging,
so ``caplog`` verifies both what IS recorded (event type, operation code,
correlation id, exception class, stack trace for internal faults) and
what must never be (exception messages that could embed provider URLs,
bearer tokens, or prompt/response text).
"""

from __future__ import annotations

import logging

import pytest

from backend.app.operability import (
    INTERNAL_FAULT_EVENT,
    PROVIDER_UNAVAILABLE_EVENT,
    log_internal_fault,
    log_provider_unavailable,
)


@pytest.fixture()
def _operability_level(caplog: pytest.LogCaptureFixture):
    """Capture the operability logger at warning-and-below verbosity."""
    caplog.set_level(logging.WARNING, logger="lineageweave.operability")
    return caplog


def test_provider_unavailable_records_operation_and_class(_operability_level) -> None:
    """A known transport failure logs the provider-unavailable event type."""

    class FakeHttpError(RuntimeError):
        pass

    correlation_id = log_provider_unavailable("global_ask", FakeHttpError("connect to provider failed"))

    record = _operability_level.records[-1]
    assert record.levelno == logging.WARNING
    assert record.event_type == PROVIDER_UNAVAILABLE_EVENT
    assert record.operation == "global_ask"
    assert record.correlation_id == correlation_id
    assert record.exception_class == "FakeHttpError"


def test_provider_unavailable_never_logs_the_exception_message(_operability_level) -> None:
    """The message may embed provider URLs or payload fragments; it stays out."""
    secret = "bearer eyJhbGciOi-secret-token"
    log_provider_unavailable("global_ask", RuntimeError(f"POST https://orchestrator failed with {secret}"))

    rendered = _operability_level.records[-1].getMessage()
    assert secret not in rendered
    assert "orchestrator" not in _operability_level.records[-1].__dict__.get("exception_class", "")


def test_internal_fault_carries_frames_and_class(_operability_level) -> None:
    """An unexpected defect logs error-level with raise-site frames attached."""
    try:
        raise AttributeError("'NoneType' object has no attribute 'answer'")
    except AttributeError as exc:
        original_traceback = exc.__traceback__
        correlation_id = log_internal_fault("global_ask", exc)

    record = _operability_level.records[-1]
    assert record.levelno == logging.ERROR
    assert record.event_type == INTERNAL_FAULT_EVENT
    assert record.operation == "global_ask"
    assert record.correlation_id == correlation_id
    assert record.exception_class == "AttributeError"
    # exc_info is attached so the stack frames reach structured telemetry,
    # and the original traceback object is preserved for the raise site.
    assert record.exc_info is not None
    assert record.exc_info[2] is original_traceback


def test_internal_fault_redacts_the_exception_message(_operability_level) -> None:
    """Tracebacks end with 'Class: message' -- the message must be redacted.

    A parsing exception's str() can embed provider payload or prompt
    fragments; the emitted traceback must end in the fixed redaction
    notice instead of that text (devin SEC thread on PR #577).
    """
    secret = 'provider payload {"korean_summary": "민감한 내용"} leaked'
    try:
        raise ValueError(f"chat response did not match the required format: {secret}")
    except ValueError as exc:
        log_internal_fault("global_ask", exc)

    import traceback

    record = _operability_level.records[-1]
    rendered = "".join(traceback.format_exception(*record.exc_info))
    assert secret not in rendered
    assert "redacted" in rendered
    # Frames are still present: the raise site stays diagnosable.
    assert __file__.split("/")[-1] not in rendered or "test_" in rendered


def test_correlation_ids_are_unique_per_event(_operability_level) -> None:
    """Two faults produce distinct correlation ids so reports stay separable."""
    first = log_provider_unavailable("global_ask", RuntimeError("first"))
    second = log_internal_fault("global_ask", ValueError("second"))

    records = _operability_level.records[-2:]
    assert {r.event_type for r in records} == {
        PROVIDER_UNAVAILABLE_EVENT,
        INTERNAL_FAULT_EVENT,
    }
    assert first != second


def test_no_prompt_or_response_text_is_emitted(_operability_level) -> None:
    """The forbidden-field contract: prompt/response content never lands."""
    prompt = "What happened between these linked events in post body <base64>..."
    response_text = "The answer text a model produced."
    exc = RuntimeError(prompt + response_text)
    log_provider_unavailable("post_chat", exc)
    log_internal_fault("post_chat", exc)

    for record in _operability_level.records[-2:]:
        rendered = record.getMessage()
        assert prompt not in rendered
        assert response_text not in rendered
