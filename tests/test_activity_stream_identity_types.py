"""Fail-closed type and canonical-key boundaries for Valkey activity identity fields."""

from __future__ import annotations

import asyncio

import pytest

from backend.app.activity_stream import (
    publish_activity_event,
    publish_activity_event_sync,
    read_activity_events,
    ticket_created_summary,
)


class _UnexpectedValkeyAccess:
    """Fail if malformed identity reaches the synchronous Valkey boundary."""

    def pipeline(self):
        """Prove validation happens before any stream read or mutation."""
        raise AssertionError("malformed activity identity reached Valkey")


class _UnexpectedAsyncValkeyAccess:
    """Fail if malformed identity reaches the ordinary async append boundary."""

    async def xadd(self, *args, **kwargs):
        """Prove runtime publication validates identity before issuing XADD."""
        del args, kwargs
        raise AssertionError("malformed activity identity reached async Valkey")


class _RecordingAsyncValkey:
    """Record stream keys so equivalent source-post UUID spellings cannot split identity."""

    def __init__(self) -> None:
        """Start without observed Valkey keys."""
        self.keys: list[str] = []

    async def xadd(self, key: str, *args, **kwargs) -> str:
        """Capture the selected stream key and return a stable fake entry id."""
        del args, kwargs
        self.keys.append(key)
        return f"1-{len(self.keys) - 1}"


class _LegacyAliasReadValkey:
    """Expose canonical and pre-canonical UUID streams to the current reader."""

    def __init__(self, entries_by_key: dict[str, list[tuple[str, dict[str, str]]]]) -> None:
        """Keep immutable-looking fixtures and record each bounded read."""
        self.entries_by_key = entries_by_key
        self.reads: list[tuple[str, int]] = []

    async def xrevrange(self, key: str, *, count: int):
        """Return the newest fake entries for one exact requested stream key."""
        self.reads.append((key, count))
        return list(self.entries_by_key.get(key, ()))[:count]


def test_sync_activity_rejects_numeric_actor_identity_before_valkey_access() -> None:
    """A numeric actor id must not alias the canonical string identity ``\"7\"``."""
    with pytest.raises(TypeError, match="actor_account_id must be a string"):
        publish_activity_event_sync(
            _UnexpectedValkeyAccess(),
            "post-1",
            "ticket_created",
            7,  # type: ignore[arg-type]
            ticket_created_summary("Send Northridge Grid the revised quote"),
        )


def test_sync_activity_rejects_numeric_post_identity_before_valkey_access() -> None:
    """A numeric post id must not alias the canonical string stream identity ``\"7\"``."""
    with pytest.raises(TypeError, match="post_id must be a string"):
        publish_activity_event_sync(
            _UnexpectedValkeyAccess(),
            7,  # type: ignore[arg-type]
            "ticket_created",
            "acct-1",
            ticket_created_summary("Send Northridge Grid the revised quote"),
        )


def test_async_activity_rejects_numeric_actor_identity_before_xadd() -> None:
    """Ordinary runtime publication shares the exact actor-identity admission rule."""
    with pytest.raises(TypeError, match="actor_account_id must be a string"):
        asyncio.run(
            publish_activity_event(
                _UnexpectedAsyncValkeyAccess(),  # type: ignore[arg-type]
                "post-1",
                "ticket_created",
                7,  # type: ignore[arg-type]
                ticket_created_summary("Send Northridge Grid the revised quote"),
            )
        )


def test_activity_stream_key_collapses_equivalent_source_post_uuid_spellings() -> None:
    """One PostgreSQL UUID identity must never fork into case-variant Valkey streams."""
    client = _RecordingAsyncValkey()
    canonical_post_id = "550e8400-e29b-41d4-a716-446655440000"
    uppercase_post_id = canonical_post_id.upper()

    async def publish_both_spellings() -> None:
        await publish_activity_event(
            client,  # type: ignore[arg-type]
            canonical_post_id,
            "ticket_created",
            "acct-1",
            "Ticket created: canonical UUID",
        )
        await publish_activity_event(
            client,  # type: ignore[arg-type]
            uppercase_post_id,
            "ticket_created",
            "acct-1",
            "Ticket created: equivalent UUID spelling",
        )

    asyncio.run(publish_both_spellings())

    assert client.keys == [
        f"activity:{canonical_post_id}",
        f"activity:{canonical_post_id}",
    ]


def test_activity_read_preserves_precanonical_uppercase_uuid_alias_events() -> None:
    """Canonical reads retain events written to the historical uppercase UUID key."""
    canonical_post_id = "550e8400-e29b-41d4-a716-446655440000"
    uppercase_post_id = canonical_post_id.upper()
    canonical_key = f"activity:{canonical_post_id}"
    legacy_key = f"activity:{uppercase_post_id}"
    client = _LegacyAliasReadValkey(
        {
            canonical_key: [
                (
                    "200-0",
                    {
                        "event_type": "ticket_status_changed",
                        "actor_account_id": "acct-1",
                        "summary": "Ticket status changed to Closed",
                    },
                )
            ],
            legacy_key: [
                (
                    "100-0",
                    {
                        "event_type": "ticket_created",
                        "actor_account_id": "acct-1",
                        "summary": "Ticket created: legacy uppercase route",
                    },
                )
            ],
        }
    )

    events = asyncio.run(
        read_activity_events(
            client,  # type: ignore[arg-type]
            canonical_post_id,
            event_count=10,
        )
    )

    assert [event["event_id"] for event in events] == ["200-0", "legacy-1:100-0"]
    assert client.reads == [(canonical_key, 10), (legacy_key, 10)]


def test_activity_read_does_not_compare_cross_stream_sequence_numbers() -> None:
    """Same-millisecond alias ties use deterministic stream precedence, not local sequence."""
    canonical_post_id = "550e8400-e29b-41d4-a716-446655440000"
    uppercase_post_id = canonical_post_id.upper()
    canonical_key = f"activity:{canonical_post_id}"
    legacy_key = f"activity:{uppercase_post_id}"
    client = _LegacyAliasReadValkey(
        {
            canonical_key: [
                (
                    "500-0",
                    {
                        "event_type": "ticket_status_changed",
                        "actor_account_id": "acct-1",
                        "summary": "Canonical current stream",
                    },
                )
            ],
            legacy_key: [
                (
                    "500-99",
                    {
                        "event_type": "ticket_created",
                        "actor_account_id": "acct-1",
                        "summary": "Historical alias stream",
                    },
                )
            ],
        }
    )

    events = asyncio.run(
        read_activity_events(
            client,  # type: ignore[arg-type]
            canonical_post_id,
            event_count=1,
        )
    )

    assert [event["summary"] for event in events] == ["Canonical current stream"]


def test_activity_read_namespaces_colliding_legacy_stream_entry_ids() -> None:
    """Independent Valkey streams must not emit duplicate buyer event identities."""
    canonical_post_id = "550e8400-e29b-41d4-a716-446655440000"
    uppercase_post_id = canonical_post_id.upper()
    canonical_key = f"activity:{canonical_post_id}"
    legacy_key = f"activity:{uppercase_post_id}"
    client = _LegacyAliasReadValkey(
        {
            canonical_key: [
                (
                    "600-0",
                    {
                        "event_type": "ticket_status_changed",
                        "actor_account_id": "acct-1",
                        "summary": "Canonical current stream",
                    },
                )
            ],
            legacy_key: [
                (
                    "600-0",
                    {
                        "event_type": "ticket_created",
                        "actor_account_id": "acct-1",
                        "summary": "Historical alias stream",
                    },
                )
            ],
        }
    )

    events = asyncio.run(
        read_activity_events(
            client,  # type: ignore[arg-type]
            canonical_post_id,
            event_count=2,
        )
    )

    assert [event["event_id"] for event in events] == [
        "600-0",
        "legacy-1:600-0",
    ]
    assert len({event["event_id"] for event in events}) == 2
