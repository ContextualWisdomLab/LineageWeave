"""Observability regressions for replay-safe Valkey activity reseeding."""

from __future__ import annotations

from opentelemetry.trace import StatusCode

from backend.app.activity_stream import (
    publish_activity_event_sync,
    ticket_created_summary,
)
from tests.test_activity_stream import _RaceInjectingStream
from tests.test_activity_stream_retry_limit import _ConflictStream
from tests.test_observability import attach_inmemory_tracer


def test_recoverable_watch_conflict_is_not_exported_as_failed_xadd(monkeypatch) -> None:
    """A successfully retried optimistic conflict must not become failure telemetry.

    ``WATCH`` conflicts are expected concurrency control for synchronous seed/admin
    replay. If another seed wins with the same activity fact, the loser retries,
    observes that fact, and returns successfully. The transient conflict therefore
    must not mark the Valkey XADD span as an operation failure or emit an exception
    event that can be mistaken for a buyer-visible/infrastructure incident.
    """
    exporter = attach_inmemory_tracer(monkeypatch)
    expected_fields = {
        "event_type": "ticket_created",
        "actor_account_id": "acct-1",
        "summary": ticket_created_summary("Send Northridge Grid the revised quote"),
    }
    client = _RaceInjectingStream(expected_fields)

    assert publish_activity_event_sync(
        client,
        "post-1",
        expected_fields["event_type"],
        expected_fields["actor_account_id"],
        expected_fields["summary"],
    ) is None

    xadd_spans = [
        span
        for span in exporter.get_finished_spans()
        if span.name == "lineageweave.valkey.activity_xadd"
    ]
    assert len(xadd_spans) == 1
    assert xadd_spans[0].status.status_code is StatusCode.UNSET
    assert all(event.name != "exception" for event in xadd_spans[0].events)


def test_exhausted_watch_conflict_marks_only_terminal_xadd_as_failure(monkeypatch) -> None:
    """Persistent contention must stay visible without flagging recoverable retries.

    Seven optimistic conflicts are normal retry attempts. The eighth exhausts the
    bounded operator contract and is therefore the one XADD attempt that should be
    exported as an error. Its exported exception data must stay limited to the safe
    RuntimeError type; the raw post-scoped stream key remains absent.
    """
    exporter = attach_inmemory_tracer(monkeypatch)
    client = _ConflictStream(conflict_attempts=8)

    try:
        publish_activity_event_sync(
            client,
            "post-1",
            "ticket_created",
            "acct-1",
            "Ticket created: bounded retry",
        )
    except RuntimeError as error:
        assert error.__cause__ is None
        assert error.__context__ is None
    else:  # pragma: no cover - persistent contention is required to fail closed
        raise AssertionError("persistent WATCH contention must fail closed")

    xadd_spans = [
        span
        for span in exporter.get_finished_spans()
        if span.name == "lineageweave.valkey.activity_xadd"
    ]
    assert len(xadd_spans) == 8
    assert all(
        span.status.status_code is StatusCode.UNSET for span in xadd_spans[:-1]
    )
    terminal_span = xadd_spans[-1]
    assert terminal_span.status.status_code is StatusCode.ERROR
    exception_events = [event for event in terminal_span.events if event.name == "exception"]
    assert len(exception_events) == 1
    assert exception_events[0].attributes["exception.type"] == "RuntimeError"
    assert "post-1" not in str(exception_events[0].attributes)
    assert "activity:post-1" not in str(exception_events[0].attributes)
