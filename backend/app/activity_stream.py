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
from redis.exceptions import WatchError

from lineageweave.observability import traced

_SYNC_ACTIVITY_WATCH_RETRY_LIMIT = 8


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


def _activity_text(value: Any, field_name: str) -> str:
    """Require one exact string before it participates in activity identity.

    Valkey accepts several scalar types, so implicit coercion can collapse a
    malformed numeric identity such as ``7`` onto the distinct canonical string
    identity ``"7"``. Reject that alias before any stream read or mutation.
    """
    if type(value) is not str:
        raise TypeError(f"{field_name} must be a string")
    return value


def _activity_fields(
    event_type: str,
    actor_account_id: str,
    activity_summary: str,
) -> dict[str, str]:
    """Translate semantic activity values to the established Valkey wire shape.

    Internal names may become more specific, but the persisted ``summary`` key
    is compatibility-sensitive. This adapter is the only intentional mapping
    between the bounded-context name and that historical field name. Identity
    and display fields cross the Valkey boundary as exact strings rather than
    being coerced from other scalar types.
    """
    return {
        "event_type": _activity_text(event_type, "event_type"),
        "actor_account_id": _activity_text(actor_account_id, "actor_account_id"),
        "summary": _activity_text(activity_summary, "activity_summary"),
    }


def _matches_activity_fields(
    activity_fields: dict[str, str],
    expected_fields: dict[str, str],
) -> bool:
    """Return whether a retained wire record has the legacy reseed identity."""
    return all(
        activity_fields.get(field_name) == expected_value
        for field_name, expected_value in expected_fields.items()
    )


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
    """Append one replay-safe seed/admin activity with optimistic concurrency.

    ``make seed`` can run in more than one process. A plain ``XREVRANGE`` then
    ``XADD`` check is racy because two callers can read the same old snapshot
    and both append. The synchronous seed path therefore WATCHes the post stream,
    reads the retained identity tuple, and commits the append with MULTI/EXEC.
    A concurrent mutation invalidates the watched snapshot and retries against
    fresh stream state, but persistent contention fails after a bounded number
    of attempts rather than leaving an operator command spinning indefinitely.
    A recovered WATCH conflict is expected concurrency control, not a failed
    Valkey operation, so it does not leave the bounded XADD span in an error
    state. Exhausting the retry budget marks only the terminal XADD attempt as a
    safe RuntimeError failure span. Ordinary async event publication remains
    append-only. Contention failures identify the operation and retry limit
    without embedding the post-scoped Valkey key in exception text or an
    exception cause that may be exported by logging or telemetry.
    """
    stream_key = _stream_key(post_id)
    expected_fields = _activity_fields(
        event_type,
        actor_account_id,
        activity_summary,
    )
    watch_retry_exhausted = False

    for watch_attempt in range(1, _SYNC_ACTIVITY_WATCH_RETRY_LIMIT + 1):
        with valkey_client.pipeline() as transaction:
            try:
                transaction.watch(stream_key)
                with traced(
                    "lineageweave.valkey.activity_xrevrange",
                    {
                        "db.system": "redis",
                        "db.operation.name": "xrevrange",
                        "lineageweave.stream.kind": "activity",
                    },
                ):
                    existing_entries = transaction.xrevrange(stream_key)

                if any(
                    _matches_activity_fields(activity_fields, expected_fields)
                    for _entry_id, activity_fields in existing_entries
                ):
                    transaction.unwatch()
                    return None

                transaction.multi()
                transaction.xadd(
                    stream_key,
                    expected_fields,
                    maxlen=1000,
                    approximate=True,
                )
                watch_conflicted = False
                committed_entries: list[str] = []
                with traced(
                    "lineageweave.valkey.activity_xadd",
                    {
                        "db.system": "redis",
                        "db.operation.name": "xadd",
                        "lineageweave.stream.kind": "activity",
                    },
                ):
                    try:
                        committed_entries = transaction.execute()
                    except WatchError:
                        watch_conflicted = True
                    if (
                        watch_conflicted
                        and watch_attempt == _SYNC_ACTIVITY_WATCH_RETRY_LIMIT
                    ):
                        raise RuntimeError(
                            "Activity reseed exceeded "
                            f"{_SYNC_ACTIVITY_WATCH_RETRY_LIMIT} WATCH retries"
                        )

                if watch_conflicted:
                    continue
                return committed_entries[0]
            except WatchError:
                if watch_attempt == _SYNC_ACTIVITY_WATCH_RETRY_LIMIT:
                    watch_retry_exhausted = True
                    break

    if watch_retry_exhausted:
        raise RuntimeError(
            "Activity reseed exceeded "
            f"{_SYNC_ACTIVITY_WATCH_RETRY_LIMIT} WATCH retries"
        )

    raise RuntimeError(
        "Activity reseed exhausted its bounded WATCH retry loop"
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