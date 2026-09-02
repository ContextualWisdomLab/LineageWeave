"""Post activity as a real Valkey event queue -- not a cache, not a second
database. A ticket mutation ``XADD``s one event onto that post's own stream
(``activity:{post_id}``); the activity panel reads it back with
``XREVRANGE``. No consumer group, no background worker: the smallest slice
where Valkey is actually load-bearing rather than a container nobody
talks to (ponytail: one producer, one direct reader, add a consumer group
if a second reader ever needs at-least-once delivery).
"""

from __future__ import annotations

from typing import Any

import redis.asyncio as redis
from fastapi import Request

from lineageweave.observability import traced


def create_valkey_client(valkey_url: str) -> redis.Redis:
    """Create the shared async Valkey client for the process."""
    return redis.from_url(valkey_url, decode_responses=True)


def get_valkey(request: Request) -> redis.Redis:
    """FastAPI dependency: the client stored on ``app.state`` at startup."""
    return request.app.state.valkey


def _stream_key(post_id: str) -> str:
    return f"activity:{post_id}"


def ticket_created_summary(ticket_title: str) -> str:
    """The ``summary`` field ``ticket_created`` producers must share."""
    return f"Ticket created: {ticket_title}"


def ticket_status_changed_summary(status_label: str) -> str:
    """The ``summary`` field ``ticket_status_changed`` producers must share.

    ``status_label`` is the ``common_lookup_value`` label (Open, In
    progress, Closed), never the raw code. A missing lookup already
    fell back to the code in ``_attach_status_labels``; this helper
    does not invent a name.
    """
    return f"Ticket status changed to {status_label}"


def _activity_fields(
    event_type: str,
    actor_account_id: str,
    activity_summary: str,
) -> dict[str, str]:
    """Translate semantic activity values to the established Valkey wire fields."""
    return {
        "event_type": event_type,
        "actor_account_id": actor_account_id,
        "summary": activity_summary,
    }


async def publish_activity_event(
    valkey_client: redis.Redis,
    post_id: str,
    event_type: str,
    actor_account_id: str,
    activity_summary: str,
) -> str:
    """``XADD`` one event onto the post's stream. Returns the entry id.

    Approximately trimmed to the most recent 1000 entries (``maxlen``,
    ``approximate=True``) so one very active post's stream can't grow
    without bound -- the panel only ever shows the most recent 50 anyway.
    """
    with traced(
        "lineageweave.valkey.activity_xadd",
        {"db.system": "redis", "db.operation.name": "xadd", "lineageweave.stream.kind": "activity"},
    ):
        return await valkey_client.xadd(
            _stream_key(post_id),
            _activity_fields(event_type, actor_account_id, activity_summary),
            maxlen=1000,
            approximate=True,
        )


def publish_activity_event_sync(
    valkey_client: Any,
    post_id: str,
    event_type: str,
    actor_account_id: str,
    activity_summary: str,
) -> str | None:
    """Sync ``XADD`` for ``make seed``; skip an existing activity summary."""
    stream_key = _stream_key(post_id)
    with traced(
        "lineageweave.valkey.activity_xrevrange",
        {"db.system": "redis", "db.operation.name": "xrevrange", "lineageweave.stream.kind": "activity"},
    ):
        existing_entries = valkey_client.xrevrange(stream_key, count=50)
    if any(
        activity_fields.get("summary") == activity_summary
        for _entry_id, activity_fields in existing_entries
    ):
        return None
    with traced(
        "lineageweave.valkey.activity_xadd",
        {"db.system": "redis", "db.operation.name": "xadd", "lineageweave.stream.kind": "activity"},
    ):
        return valkey_client.xadd(
            stream_key,
            _activity_fields(event_type, str(actor_account_id), activity_summary),
            maxlen=1000,
            approximate=True,
        )


async def read_activity_events(
    valkey_client: redis.Redis,
    post_id: str,
    event_count: int = 50,
) -> list[dict[str, Any]]:
    """Read the post's most recent activity events, newest first."""
    with traced(
        "lineageweave.valkey.activity_xrevrange",
        {"db.system": "redis", "db.operation.name": "xrevrange", "lineageweave.stream.kind": "activity"},
    ):
        stream_entries = await valkey_client.xrevrange(
            _stream_key(post_id),
            count=event_count,
        )
    return [
        {
            "event_id": entry_id,
            "event_type": activity_fields["event_type"],
            "actor_account_id": activity_fields["actor_account_id"],
            "summary": activity_fields["summary"],
        }
        for entry_id, activity_fields in stream_entries
    ]
