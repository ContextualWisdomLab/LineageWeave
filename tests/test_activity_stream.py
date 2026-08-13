"""Valkey activity helpers -- no live stack required.

``publish_activity_event_sync`` is what ``make seed`` uses so Activity is
not empty after a ticket row exists in Postgres. A fake client is enough
to prove the shared field shape and the idempotent re-seed skip.
"""

from __future__ import annotations

from backend.app.activity_stream import (
    publish_activity_event_sync,
    ticket_created_summary,
    ticket_status_changed_summary,
)


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
