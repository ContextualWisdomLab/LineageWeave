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
    """Create the process-wide async client for the configured Valkey endpoint.

    ``valkey_url`` is deployment configuration, not a per-request destination.
    Connection establishment stays lazy in redis-py; startup therefore owns the
    client lifecycle while request handlers only consume the stored client.
    """
    return redis.from_url(valkey_url, decode_responses=True)


def get_valkey(request: Request) -> redis.Redis:
    """Return the Valkey client installed on FastAPI application state.

    Startup is responsible for creating ``app.state.valkey``. This dependency
    deliberately does not construct a fallback client from request data or
    environment state because that would create a second connection authority.
    """
    return request.app.state.valkey


def _stream_key(post_id: str) -> str:
    """Map one canonical post id to its stable activity-stream wire key.

    The prefix is part of the persisted Valkey contract. Keep key construction
    centralized so producers and readers cannot silently diverge on namespace.
    """
    return f"activity:{post_id}"


def ticket_created_summary(ticket_title: str) -> str:
    """Build the stable human-readable summary for a ticket-created event.

    The summary is display text and only one field of reseed identity; callers
    must not use it alone to decide whether two activity facts are the same.
    """
    return f"Ticket created: {ticket_title}"


def ticket_status_changed_summary(status_label: str) -> str:
    """Build the stable summary for a ticket-status transition.

    ``status_label`` is the ``common_lookup_value`` label (Open, In progress,
    Closed), never the raw code. A missing lookup already fell back to the code
    in ``_attach_status_labels``; this helper does not invent a replacement.
    """
    return f"Ticket status changed to {status_label}"


def _activity_fields(
    event_type: str,
    actor_account_id: str,
    activity_summary: str,
) -> dict[str, str]:
    """Translate semantic activity values to the established Valkey wire shape.

    Internal names may become more specific, but the persisted ``summary`` key
    is compatibility-sensitive. This adapter is the only intentional mapping
    between the bounded-context name and that historical field name.
    """
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
    """Append one activity fact to the post stream and return its entry id.

    The ordinary runtime path never performs reseed deduplication: each accepted
    application event is appended once by its caller. Approximate trimming keeps
    one very active post from growing without bound while preserving the recent
    activity window consumed by the UI.
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
    """Append a seed/admin activity unless the same retained fact already exists.

    This synchronous path scans the retained stream because ``make seed`` must
    be replay-safe even after more than fifty newer events. Identity is the
    established tuple ``event_type`` + ``actor_account_id`` + ``summary``;
    summary text alone is insufficient because distinct facts can share text.
    Returns ``None`` only when that exact retained wire identity already exists.
    """
    stream_key = _stream_key(post_id)
    expected_fields = _activity_fields(
        event_type,
        str(actor_account_id),
        activity_summary,
    )
    with traced(
        "lineageweave.valkey.activity_xrevrange",
        {"db.system": "redis", "db.operation.name": "xrevrange", "lineageweave.stream.kind": "activity"},
    ):
        existing_entries = valkey_client.xrevrange(stream_key)
    if any(
        all(
            activity_fields.get(field_name) == expected_value
            for field_name, expected_value in expected_fields.items()
        )
        for _entry_id, activity_fields in existing_entries
    ):
        return None
    with traced(
        "lineageweave.valkey.activity_xadd",
        {"db.system": "redis", "db.operation.name": "xadd", "lineageweave.stream.kind": "activity"},
    ):
        return valkey_client.xadd(
            stream_key,
            expected_fields,
            maxlen=1000,
            approximate=True,
        )


async def read_activity_events(
    valkey_client: redis.Redis,
    post_id: str,
    event_count: int = 50,
) -> list[dict[str, Any]]:
    """Read the newest retained activity events for one post.

    ``event_count`` bounds the buyer-facing read; this function does not broaden
    the query to other posts or reconstruct missing facts. Returned dictionaries
    preserve the established event id/type/actor/summary wire fields.
    """
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
