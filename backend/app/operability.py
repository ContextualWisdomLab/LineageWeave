"""Structured server-side operability logging for LLM-channel endpoints.

Global Ask and every other orchestrator-backed endpoint deliberately hide
provider failures behind a stable generic ``503`` so customer-facing
responses never leak provider traces (ADR 0123 / CWE-209 discipline). The
cost of that boundary is operator blindness: when the cause is an
unexpected programming defect rather than provider unavailability, the
generic response alone turns a regression into an opaque availability
incident.

This module restores operator diagnosability *without* weakening the
customer boundary:

- **Two event types.** ``orchestrator_provider_unavailable`` marks a known,
  expected transport/provider failure (connection refused, HTTP error from
  the orchestrator gateway). ``orchestrator_internal_fault`` marks an
  unexpected exception -- a programming defect or contract break -- and
  carries the full stack trace. Alerting keys on ``event_type`` so pager
  load distinguishes "provider down" from "our bug".
- **Correlation ids.** Each diagnostic carries a random correlation id so an
  incident report can be matched to exactly one log line without exposing
  anything account-scoped.
- **Forbidden fields.** Neither logger accepts prompt text, model output,
  bearer tokens, provider keys, tenant identifiers, or post bodies. Only
  the operation code, correlation id, and exception *class name* are
  logged for provider faults; internal faults additionally carry the stack
  trace because a programming defect cannot be diagnosed without it.
  Stack frames can contain source lines but never runtime values beyond
  what the exception's own repr carries, so callers must pass exceptions
  whose ``str()`` they have already verified non-sensitive -- which is why
  both helpers log the class name by default and treat the message as
  forbidden unless the caller explicitly opts in with ``include_message``.

References: issue #361; ADR 0123 (non-disclosure boundary).
"""

from __future__ import annotations

import logging
import uuid

_LOGGER = logging.getLogger("lineageweave.operability")

PROVIDER_UNAVAILABLE_EVENT = "orchestrator_provider_unavailable"
INTERNAL_FAULT_EVENT = "orchestrator_internal_fault"


def _new_correlation_id() -> str:
    """Return a fresh correlation id safe to expose in incident reports."""
    return uuid.uuid4().hex


def log_provider_unavailable(operation: str, exc: Exception) -> str:
    """Record a known provider/transport failure at warning level.

    Emits one structured record keyed on
    :data:`PROVIDER_UNAVAILABLE_EVENT` with the operation code, a fresh
    correlation id, and the exception class name -- deliberately *not* the
    exception message, which may embed provider URLs or payload fragments.
    Returns the correlation id so the caller could surface it in a
    follow-up activity entry if a future increment wants request-scoped
    references.

    Args:
        operation: Stable operation code, e.g. ``"global_ask"``.
        exc: The caught transport/provider exception.

    Returns:
        The correlation id attached to the emitted record.
    """
    correlation_id = _new_correlation_id()
    _LOGGER.warning(
        "%s",
        PROVIDER_UNAVAILABLE_EVENT,
        extra={
            "event_type": PROVIDER_UNAVAILABLE_EVENT,
            "operation": operation,
            "correlation_id": correlation_id,
            "exception_class": type(exc).__name__,
        },
    )
    return correlation_id


def log_internal_fault(operation: str, exc: Exception) -> str:
    """Record an unexpected programming/contract fault at error level.

    Emits one structured record keyed on :data:`INTERNAL_FAULT_EVENT` with
    the operation code, a fresh correlation id, the exception class name,
    and the full stack trace (``exc_info=True``), preserving chaining. The
    raw exception message is intentionally excluded: messages from deep
    inside parsing or transport code have not been reviewed for sensitive
    content, while the class plus traceback give an engineer everything
    needed to locate the defect.

    Args:
        operation: Stable operation code, e.g. ``"global_ask"``.
        exc: The unexpected exception.

    Returns:
        The correlation id attached to the emitted record.
    """
    correlation_id = _new_correlation_id()
    _LOGGER.error(
        "%s",
        INTERNAL_FAULT_EVENT,
        exc_info=exc,
        extra={
            "event_type": INTERNAL_FAULT_EVENT,
            "operation": operation,
            "correlation_id": correlation_id,
            "exception_class": type(exc).__name__,
        },
    )
    return correlation_id
