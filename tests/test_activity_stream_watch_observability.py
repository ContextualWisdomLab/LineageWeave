"""Observability regressions for replay-safe Valkey activity reseeding."""

from __future__ import annotations

from opentelemetry.trace import StatusCode

from backend.app.activity_stream import (
    publish_activity_event_sync,
    ticket_created_summary,
)
from tests.test_activity_stream import _RaceInjectingStream
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
