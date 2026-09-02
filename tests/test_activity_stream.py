"""Valkey activity helpers -- no live stack required.

``publish_activity_event_sync`` is what ``make seed`` uses so Activity is
not empty after a ticket row exists in Postgres. A fake client is enough
to prove the shared field shape and the idempotent re-seed skip.
"""

from __future__ import annotations

from inspect import signature

from backend.app.activity_stream import (
    create_valkey_client,
    publish_activity_event,
    publish_activity_event_sync,
    ticket_created_summary,
    ticket_status_changed_summary,
)
from lineageweave.observability import traced
from tests.test_observability import attach_inmemory_tracer


class _FakeStream:
    def __init__(self) -> None:
        self.entries: list[tuple[str, dict[str, str]]] = []

    def xrevrange(self, key: str, count: int = 50):
        del key
        return list(reversed(self.entries[-count:]))

    def xadd(self, key: str, fields: dict[str, str], maxlen=None, approximate=None):
        del key, maxlen, approximate
        entry_id = f"1-{len(self.entries)}"
        self.entries.append((entry_id, dict(fields)))
        return entry_id


def test_activity_stream_owned_parameters_use_semantic_names() -> None:
    """Organization-owned activity helpers expose bounded-context vocabulary."""
    assert list(signature(create_valkey_client).parameters) == ["valkey_url"]
    expected_event_parameters = [
        "valkey_client",
        "post_id",
        "event_type",
        "actor_account_id",
        "activity_summary",
    ]
    assert list(signature(publish_activity_event).parameters) == expected_event_parameters
    assert list(signature(publish_activity_event_sync).parameters) == expected_event_parameters


def test_ticket_created_summary_matches_the_live_api_wording() -> None:
    assert ticket_created_summary("Send Northridge Grid the revised quote") == (
        "Ticket created: Send Northridge Grid the revised quote"
    )


def test_ticket_status_changed_summary_uses_the_lookup_label() -> None:
    assert ticket_status_changed_summary("In progress") == (
        "Ticket status changed to In progress"
    )
    assert "in_progress" not in ticket_status_changed_summary("In progress")


def test_publish_activity_event_sync_skips_a_matching_summary() -> None:
    client = _FakeStream()
    first = publish_activity_event_sync(
        client,
        "post-1",
        "ticket_created",
        "acct-1",
        ticket_created_summary("Send Northridge Grid the revised quote"),
    )
    second = publish_activity_event_sync(
        client,
        "post-1",
        "ticket_created",
        "acct-1",
        ticket_created_summary("Send Northridge Grid the revised quote"),
    )
    assert first == "1-0"
    assert second is None
    assert len(client.entries) == 1
    assert client.entries[0][1]["event_type"] == "ticket_created"
    assert "Send Northridge Grid the revised quote" in client.entries[0][1]["summary"]


def test_valkey_child_span_shares_parent_trace_id(monkeypatch) -> None:
    """Same-process Valkey work inherits the parent TraceId."""
    from opentelemetry import trace

    attach_inmemory_tracer(monkeypatch)
    captured: dict[str, str] = {}

    class _Client(_FakeStream):
        def xadd(self, key: str, fields: dict[str, str], maxlen=None, approximate=None):
            span = trace.get_current_span()
            captured["trace_id"] = format(span.get_span_context().trace_id, "032x")
            captured["span_id"] = format(span.get_span_context().span_id, "016x")
            return super().xadd(key, fields, maxlen=maxlen, approximate=approximate)

    with traced("lineageweave.test.parent"):
        parent_context = trace.get_current_span().get_span_context()
        parent_trace_id = format(parent_context.trace_id, "032x")
        parent_span_id = format(parent_context.span_id, "016x")
        publish_activity_event_sync(
            _Client(),
            "post-1",
            "ticket_created",
            "acct-1",
            ticket_created_summary("Send Northridge Grid the revised quote"),
        )

    assert parent_trace_id != "0" * 32
    assert captured["trace_id"] == parent_trace_id
    assert captured["span_id"] != "0" * 16
    assert captured["span_id"] != parent_span_id
