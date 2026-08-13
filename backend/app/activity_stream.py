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


def create_valkey_client(url: str) -> redis.Redis:
    """One shared async client for the process, mirroring db.create_pool."""
    return redis.from_url(url, decode_responses=True)


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


def _activity_fields(event_type: str, actor_account_id: str, summary: str) -> dict[str, str]:
    return {
        "event_type": event_type,
        "actor_account_id": actor_account_id,
        "summary": summary,
    }


async def publish_activity_event(
    client: redis.Redis,
    post_id: str,
    event_type: str,
    actor_account_id: str,
    summary: str,
) -> str:
    """``XADD`` one event onto the post's stream. Returns the entry id.

    Approximately trimmed to the most recent 1000 entries (``maxlen``,
    ``approximate=True``) so one very active post's stream can't grow
    without bound -- the panel only ever shows the most recent 50 anyway.
    """
    return await client.xadd(
        _stream_key(post_id),
        _activity_fields(event_type, actor_account_id, summary),
        maxlen=1000,
        approximate=True,
    )


def publish_activity_event_sync(
    client: Any,
    post_id: str,
    event_type: str,
    actor_account_id: str,
    summary: str,
) -> str | None:
    """Sync ``XADD`` for ``make seed``. Returns None if ``summary`` is already on the stream."""
    key = _stream_key(post_id)
    existing = client.xrevrange(key, count=50)
    if any(fields.get("summary") == summary for _entry_id, fields in existing):
        return None
    return client.xadd(
        key,
        _activity_fields(event_type, str(actor_account_id), summary),
        maxlen=1000,
        approximate=True,
    )


async def read_activity_events(client: redis.Redis, post_id: str, count: int = 50) -> list[dict[str, Any]]:
    """The post's most recent events, newest first."""
    entries = await client.xrevrange(_stream_key(post_id), count=count)
    return [
        {
            "event_id": entry_id,
            "event_type": fields["event_type"],
            "actor_account_id": fields["actor_account_id"],
            "summary": fields["summary"],
        }
        for entry_id, fields in entries
    ]
