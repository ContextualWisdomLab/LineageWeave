"""Structured diagnostics at the contextual-orchestrator failure boundary.

Customer-facing orchestrator-backed endpoints deliberately return one stable,
generic ``503`` regardless of what went wrong behind it, so provider traces,
exception text, prompts, responses, credentials, and tenant data never reach
the caller. The cost of that honest boundary is diagnosability: without extra
structure, an unexpected programming defect looks identical to a provider
outage and becomes an opaque availability incident (issue #361).

This module restores operator-side diagnosability without weakening the
customer-facing contract:

- Known provider/transport/schema failures (:class:`HttpClientError`,
  ``KeyError``, ``OSError``, ``ValueError``) log a bounded
  ``orchestrator_provider_unavailable`` event, bump the matching in-process
  counter, and raise the generic ``503``.
- Any *unexpected* exception logs ``orchestrator_internal_fault`` with the
  operation code, correlation id, exception class, and full stack trace
  (via :meth:`logging.Logger.exception`), bumps the distinct
  internal-fault counter, and raises the same generic ``503``.

Forbidden content -- prompt text, model output, bearer tokens, provider keys,
source-post bodies -- is never passed to this module, so it can never leak
into logs or traces through it. Exception chaining (``raise ... from exc``)
is always preserved.

Counters are plain process-local integers keyed by ``(event, operation_code)``;
``operation_code`` values come from a fixed call-site vocabulary, so metric
cardinality stays bounded. Alerting keys on the two event names: a rising
``orchestrator_provider_unavailable`` rate is an upstream availability signal,
while any ``orchestrator_internal_fault`` is a page-the-owner programming
defect.

References (APA 7th):

- OpenTelemetry Community. (2024). *A semantic approach to error handling in
  telemetry*. https://opentelemetry.io/docs/specs/semconv/ -- error-type
  attributes must stay low-cardinality and class-based, which is why only the
  exception class name (never its message) is recorded as a field.
- Python Software Foundation. (2025). *The logging module: Logger.exception*.
  https://docs.python.org/3/library/logging.html#logging.Logger.exception --
  ``Logger.exception`` inside an except block records the stack trace while
  preserving normal exception propagation.
"""

from __future__ import annotations

import contextvars
import logging
import threading
from collections import defaultdict
from contextlib import contextmanager
from typing import Iterator

from fastapi import HTTPException
from lineageweave.http_client import HttpClientError

_logger = logging.getLogger(__name__)

#: Exceptions that mean "the orchestrator/provider transport or its payload
#: failed". Anything else reaching this boundary is an unexpected programming
#: defect and gets the louder internal-fault treatment.
KNOWN_ORCHESTRATOR_EXCEPTIONS = (HttpClientError, KeyError, OSError, ValueError)

#: Event names emitted on every boundary trip. Alerting should treat these
#: differently: provider-unavailable is upstream capacity, internal-fault is
#: a defect in this service.
EVENT_PROVIDER_UNAVAILABLE = "orchestrator_provider_unavailable"
EVENT_INTERNAL_FAULT = "orchestrator_internal_fault"

_request_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "orchestrator_boundary_correlation_id", default=""
)

_counters_lock = threading.Lock()
_counters: defaultdict[tuple[str, str], int] = defaultdict(int)


def new_correlation_id(correlation_id: str) -> str:
    """Install and return a fresh correlation id for this request/task.

    Callers generate the value (a short ``uuid4`` hex works well) so request
    handlers stay the single owner of identity; the boundary only carries it
    into log fields. An empty string means "not set" and simply omits the
    field rather than emitting noise.
    """
    token_value = str(correlation_id).strip()
    _request_correlation_id.set(token_value)
    return token_value


def current_correlation_id() -> str:
    """Return the correlation id installed for this context, if any."""
    return _request_correlation_id.get()


def boundary_counters() -> dict[tuple[str, str], int]:
    """Return a snapshot of ``(event, operation_code)`` counters.

    Tests assert against this snapshot; operators can expose it through a
    health/metrics surface without adding a metrics dependency to the
    backend install set.
    """
    with _counters_lock:
        return {key: value for key, value in _counters.items()}


def _bump(event: str, operation_code: str) -> None:
    with _counters_lock:
        _counters[(event, operation_code)] += 1


@contextmanager
def orchestrator_boundary(operation_code: str, generic_detail: str) -> Iterator[None]:
    """Translate orchestrator failures into one generic customer-facing 503.

    Wrap the narrowest span that calls into an orchestrator-backed client::

        with orchestrator_boundary("global_ask", "Ask Agent is unavailable"):
            answer = await asyncio.to_thread(client.answer, question, sources)

    Known provider/transport/schema exceptions become a warning-level
    ``orchestrator_provider_unavailable`` event. Any other exception becomes
    an error-level ``orchestrator_internal_fault`` event *with stack trace*
    (``Logger.exception``). Both paths raise :class:`~fastapi.HTTPException`
    with status 503 and exactly ``generic_detail`` -- never the underlying
    exception message -- and both preserve exception chaining via
    ``raise ... from exc``.
    """
    try:
        yield
    except KNOWN_ORCHESTRATOR_EXCEPTIONS as exc:
        _bump(EVENT_PROVIDER_UNAVAILABLE, operation_code)
        _logger.warning(
            "%s",
            EVENT_PROVIDER_UNAVAILABLE,
            extra={
                "event": EVENT_PROVIDER_UNAVAILABLE,
                "operation_code": operation_code,
                "correlation_id": current_correlation_id(),
                "exception_class": type(exc).__name__,
            },
        )
        raise HTTPException(503, generic_detail) from exc
    except Exception as exc:
        _bump(EVENT_INTERNAL_FAULT, operation_code)
        _logger.exception(
            "%s",
            EVENT_INTERNAL_FAULT,
            extra={
                "event": EVENT_INTERNAL_FAULT,
                "operation_code": operation_code,
                "correlation_id": current_correlation_id(),
                "exception_class": type(exc).__name__,
            },
        )
        raise HTTPException(503, generic_detail) from exc
