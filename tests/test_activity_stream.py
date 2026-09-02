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
    read_activity_events,
    ticket_created_summary,
    ticket_status_changed_summary,
)
from lineageweave.observability import traced
from tests.test_observability import attach_inmemory_tracer


class _FakeStream:
    """Small in-memory stand-in for the Valkey stream methods under contract."""

    def __init__(self) -> None:
        """Start with no retained activity entries."""
        self.entries: list[tuple[str, dict[str, str]]] = []

    def xrevrange(self, key: str, count: int | None = None):
        """Return newest-first entries with the same optional count boundary."""
        del key
        entries = list(reversed(self.entries))
        return entries if count is None else entries[:count]

    def xadd(self, key: str, fields: dict[str, str], maxlen=None, approximate=None):
        """Append a copied wire record and return a deterministic fake entry id."""
        del key, maxlen, approximate
        entry_id = f"1-{len(self.entries)}"
        self.entries.append((entry_id, dict(fields)))
        return entry_id


class _RaceInjectingStream(_FakeStream):
    """Inject one concurrent seed after the caller reads its stale snapshot."""

    def __init__(self, concurrent_fields: dict[str, str]) -> None:
        """Remember the fact another seed execution will publish once."""
        super().__init__()
        self.concurrent_fields = dict(concurrent_fields)
        self.injected = False

    def xrevrange(self, key: str, count: int | None = None):
        """Return the old snapshot, then simulate another process appending it."""
        entries = super().xrevrange(key, count=count)
        if not self.injected:
            self.injected = True
            super().xadd(key, self.concurrent_fields)
        return entries


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
    assert list(signature(read_activity_events).parameters) == [
        "valkey_client",
        "post_id",
        "event_count",
    ]


def test_ticket_created_summary_matches_the_live_api_wording() -> None:
    """Ticket creation retains the wording consumed by the live Activity UI."""
    assert ticket_created_summary("Send Northridge Grid the revised quote") == (
        "Ticket created: Send Northridge Grid the revised quote"
    )


def test_ticket_status_changed_summary_uses_the_lookup_label() -> None:
    """Status activity uses the resolved label rather than leaking its raw code."""
    assert ticket_status_changed_summary("In progress") == (
        "Ticket status changed to In progress"
    )
    assert "in_progress" not in ticket_status_changed_summary("In progress")


def test_publish_activity_event_sync_skips_a_matching_activity_fact() -> None:
    """An exact retained event-type, actor, and summary tuple is replay-idempotent."""
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


def test_publish_activity_event_sync_keeps_distinct_events_with_same_summary() -> None:
    """Reseeding must not collapse different activity facts onto summary text."""
    client = _FakeStream()
    shared_summary = "Assignment updated"
    client.xadd(
        "activity:post-1",
        {
            "event_type": "ticket_status_changed",
            "actor_account_id": "acct-2",
            "summary": shared_summary,
        },
    )

    created = publish_activity_event_sync(
        client,
        "post-1",
        "ticket_created",
        "acct-1",
        shared_summary,
    )

    assert created == "1-1"
    assert len(client.entries) == 2
    assert client.entries[-1][1] == {
        "event_type": "ticket_created",
        "actor_account_id": "acct-1",
        "summary": shared_summary,
    }


def test_publish_activity_event_sync_keeps_same_event_type_for_different_actor() -> None:
    """Actor identity independently distinguishes otherwise equal reseed facts."""
    client = _FakeStream()
    shared_summary = "Assignment updated"
    client.xadd(
        "activity:post-1",
        {
            "event_type": "ticket_status_changed",
            "actor_account_id": "acct-2",
            "summary": shared_summary,
        },
    )

    created = publish_activity_event_sync(
        client,
        "post-1",
        "ticket_status_changed",
        "acct-1",
        shared_summary,
    )

    assert created == "1-1"
    assert client.entries[-1][1]["actor_account_id"] == "acct-1"


def test_publish_activity_event_sync_keeps_same_actor_for_different_event_type() -> None:
    """Event type independently distinguishes otherwise equal reseed facts."""
    client = _FakeStream()
    shared_summary = "Assignment updated"
    client.xadd(
        "activity:post-1",
        {
            "event_type": "ticket_status_changed",
            "actor_account_id": "acct-1",
            "summary": shared_summary,
        },
    )

    created = publish_activity_event_sync(
        client,
        "post-1",
        "ticket_created",
        "acct-1",
        shared_summary,
    )

    assert created == "1-1"
    assert client.entries[-1][1]["event_type"] == "ticket_created"


def test_publish_activity_event_sync_scans_the_retained_stream_for_reseed_idempotency() -> None:
    """A retained seed event stays idempotent after more than 50 newer events."""
    client = _FakeStream()
    seed_summary = ticket_created_summary("Send Northridge Grid the revised quote")
    assert publish_activity_event_sync(
        client,
        "post-1",
        "ticket_created",
        "acct-1",
        seed_summary,
    ) == "1-0"

    for index in range(51):
        client.xadd(
            "activity:post-1",
            {
                "event_type": "ticket_status_changed",
                "actor_account_id": "acct-1",
                "summary": f"newer activity {index}",
            },
        )

    entry_count = len(client.entries)
    assert publish_activity_event_sync(
        client,
        "post-1",
        "ticket_created",
        "acct-1",
        seed_summary,
    ) is None
    assert len(client.entries) == entry_count


def test_publish_activity_event_sync_retries_when_another_seed_wins_the_race() -> None:
    """Concurrent make-seed executions must not append the same activity twice."""
    expected_fields = {
        "event_type": "ticket_created",
        "actor_account_id": "acct-1",
        "summary": ticket_created_summary("Send Northridge Grid the revised quote"),
    }
    client = _RaceInjectingStream(expected_fields)

    created = publish_activity_event_sync(
        client,
        "post-1",
        expected_fields["event_type"],
        expected_fields["actor_account_id"],
        expected_fields["summary"],
    )

    assert created is None
    assert client.entries == [("1-0", expected_fields)]


def test_valkey_child_span_shares_parent_trace_id(monkeypatch) -> None:
    """Same-process Valkey work inherits the parent TraceId."""
    from opentelemetry import trace

    attach_inmemory_tracer(monkeypatch)
    captured: dict[str, str] = {}

    class _Client(_FakeStream):
        """Capture tracing identity at the fake Valkey append boundary."""

        def xadd(self, key: str, fields: dict[str, str], maxlen=None, approximate=None):
            """Record the current child span before delegating to the fake stream."""
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
