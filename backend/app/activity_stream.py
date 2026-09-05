"""Post activity as a real Valkey event queue -- not a cache, not a second
database. A ticket mutation ``XADD``s one event onto that post's own stream
(``activity:{post_id}``); the activity panel reads it back with
``XREVRANGE``. No consumer group, no background worker: the smallest slice
where Valkey is actually load-bearing rather than a container nobody
talks to (ponytail: one producer, one direct reader, add a consumer group
if a second reader ever needs at-least-once delivery).
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

import redis.asyncio as redis
from fastapi import Request
from redis.exceptions import WatchError

from lineageweave.observability import traced

_SYNC_ACTIVITY_WATCH_RETRY_LIMIT = 8
_MAX_ACTIVITY_READ_COUNT = 1000
_ACTIVITY_ALIAS_INDEX_WRITE_BATCH_SIZE = 128
_ACTIVITY_STREAM_PREFIX = "activity:"
_ACTIVITY_ALIAS_INDEX_PREFIX = "activity-aliases:"


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
    """Map one source-post identity to its stable activity-stream wire key.

    ``source_post.post_id`` is PostgreSQL ``uuid``. PostgreSQL accepts more than
    one textual spelling for the same UUID, so using raw request text as the
    Valkey suffix can fork one database identity into case- or format-variant
    streams. Syntactically valid UUID strings therefore converge on Python's
    canonical lowercase hyphenated representation before key construction.
    Non-UUID fixture/legacy strings retain exact spelling, and non-string values
    are still rejected rather than being stringified onto another identity.
    """
    if type(post_id) is not str:
        raise TypeError("post_id must be a string")
    try:
        canonical_post_id = str(UUID(post_id))
    except ValueError:
        canonical_post_id = post_id
    return f"{_ACTIVITY_STREAM_PREFIX}{canonical_post_id}"


def _activity_alias_index_key(post_id: str) -> str:
    """Return the durable legacy-alias index for one canonical post UUID."""
    return f"{_ACTIVITY_ALIAS_INDEX_PREFIX}{str(UUID(post_id))}"


async def _flush_activity_alias_index_writes(
    valkey_client: redis.Redis,
    writes: list[tuple[str, str]],
) -> int:
    """Persist one bounded batch of independent alias-index set insertions."""
    if not writes:
        return 0

    pipeline_factory = getattr(valkey_client, "pipeline", None)
    if pipeline_factory is None:
        indexed = 0
        for index_key, stream_key in writes:
            indexed += int(await valkey_client.sadd(index_key, stream_key))
        return indexed

    async with pipeline_factory(transaction=False) as write_pipeline:
        for index_key, stream_key in writes:
            write_pipeline.sadd(index_key, stream_key)
        results = await write_pipeline.execute()
    return sum(int(result) for result in results)


async def index_legacy_activity_stream_aliases(valkey_client: redis.Redis) -> int:
    """Index every existing UUID stream alias before canonical-only reads begin.

    PostgreSQL accepts UUID input spellings with braces, upper-case digits, and
    non-standard hyphen placement. Older routes used that raw spelling in the
    Valkey key, so enumerating a few common variants cannot preserve all valid
    history. Startup performs one cursor scan and records the finite aliases
    that actually exist. New writes remain canonical-only. Independent alias-set
    writes are flushed through bounded non-transactional pipeline batches so
    rollout readiness does not add one serial network wait per historical alias.
    """
    indexed = 0
    pending_writes: list[tuple[str, str]] = []
    async for raw_key in valkey_client.scan_iter(match=f"{_ACTIVITY_STREAM_PREFIX}*"):
        stream_key = raw_key.decode() if isinstance(raw_key, bytes) else raw_key
        if not isinstance(stream_key, str) or stream_key.startswith(_ACTIVITY_ALIAS_INDEX_PREFIX):
            continue
        raw_post_id = stream_key.removeprefix(_ACTIVITY_STREAM_PREFIX)
        try:
            canonical_post_id = str(UUID(raw_post_id))
        except ValueError:
            continue
        canonical_key = f"{_ACTIVITY_STREAM_PREFIX}{canonical_post_id}"
        if stream_key == canonical_key:
            continue
        pending_writes.append(
            (
                f"{_ACTIVITY_ALIAS_INDEX_PREFIX}{canonical_post_id}",
                stream_key,
            )
        )
        if len(pending_writes) >= _ACTIVITY_ALIAS_INDEX_WRITE_BATCH_SIZE:
            indexed += await _flush_activity_alias_index_writes(
                valkey_client,
                pending_writes,
            )
            pending_writes.clear()
    indexed += await _flush_activity_alias_index_writes(valkey_client, pending_writes)
    return indexed


async def _activity_read_stream_keys(
    valkey_client: redis.Redis,
    post_id: str,
) -> tuple[str, ...]:
    """Return the canonical stream plus bounded pre-canonical compatibility aliases.

    New writes converge on the canonical UUID key. Before that invariant existed,
    an uppercase UUID route spelling could create an independent raw stream. The
    startup alias index therefore supplies the finite UUID-equivalent stream keys
    that actually exist. The request never scans unrelated keys or guesses a
    subset of PostgreSQL's accepted UUID spellings. This is a read-only bridge:
    it does not create new alias streams.
    """
    canonical_key = _stream_key(post_id)
    if type(post_id) is not str:
        raise TypeError("post_id must be a string")
    try:
        UUID(post_id)
    except ValueError:
        return (canonical_key,)

    indexed_aliases: list[str] = []
    async for alias in valkey_client.sscan_iter(_activity_alias_index_key(post_id)):
        indexed_aliases.append(alias)
        if len(indexed_aliases) > _MAX_ACTIVITY_READ_COUNT - 1:
            raise RuntimeError("Activity history has too many retained compatibility streams")
    candidate_keys = (canonical_key, *sorted(indexed_aliases))
    return tuple(dict.fromkeys(candidate_keys))


async def _activity_canonical_entries_if_alias_free(
    valkey_client: redis.Redis,
    post_id: str,
    event_count: int,
) -> list[tuple[str, dict[str, str]]] | None:
    """Read alias admission and canonical events in one UUID-path network exchange.

    The retained-alias set exists only to bridge pre-canonical UUID spellings.
    A normal UUID read must not pay one network wait for that empty compatibility
    set and a second wait for the canonical stream. Redis pipelines preserve the
    two independent commands while sending them together. If the first bounded
    SSCAN page proves that the alias set is empty, its paired canonical XREVRANGE
    is the complete fast-path result. Any observed alias or nonzero scan cursor
    falls back to the bounded compatibility merger so retained history is never
    hidden merely to reduce latency.

    Minimal Redis-compatible test adapters without pipeline support return
    ``None`` and exercise the established fallback; production clients created
    by :func:`create_valkey_client` always provide the async pipeline contract.
    """
    canonical_key = _stream_key(post_id)
    try:
        UUID(post_id)
    except ValueError:
        return None

    pipeline_factory = getattr(valkey_client, "pipeline", None)
    if pipeline_factory is None:
        return None

    async with pipeline_factory(transaction=False) as read_pipeline:
        read_pipeline.sscan(
            _activity_alias_index_key(post_id),
            cursor=0,
            count=_MAX_ACTIVITY_READ_COUNT,
        )
        read_pipeline.xrevrange(canonical_key, count=event_count)
        with traced(
            "lineageweave.valkey.activity_read_pipeline",
            {
                "db.system": "redis",
                "db.operation.name": "pipeline",
                "lineageweave.stream.kind": "activity",
            },
        ):
            alias_page, canonical_entries = await read_pipeline.execute()

    alias_cursor, aliases = alias_page
    if int(alias_cursor) == 0 and not aliases:
        return canonical_entries
    return None


def _activity_stream_entry_order(entry_id: str) -> tuple[int, int]:
    """Parse one Valkey stream entry id into its stream-local numeric order."""
    milliseconds, separator, sequence = entry_id.partition("-")
    if separator != "-":
        raise ValueError("Valkey activity event id is malformed")
    try:
        return int(milliseconds), int(sequence)
    except ValueError as exc:
        raise ValueError("Valkey activity event id is malformed") from exc


def _activity_compatibility_merge_order(
    entry_id: str,
    stream_index: int,
) -> tuple[int, int, int]:
    """Order compatibility reads without inventing cross-stream sequence chronology.

    Redis stream sequence numbers are ordered only inside one stream. Historical
    alias streams can therefore contain the same millisecond with unrelated
    sequence counters. The millisecond remains comparable; an equal-millisecond
    tie uses the declared stream precedence (canonical first, then bounded legacy
    aliases), and the sequence number only orders entries that came from that
    same stream. This fallback is deterministic but deliberately does not claim
    to reconstruct unknowable sub-millisecond chronology across old streams.
    """
    milliseconds, sequence = _activity_stream_entry_order(entry_id)
    return milliseconds, -stream_index, sequence


def _activity_public_event_id(entry_id: str, stream_index: int) -> str:
    """Return an opaque event identity unique across bounded compatibility streams.

    Valkey stream IDs are unique only inside one stream, so a canonical stream and
    a historical alias can legitimately both contain ``600-0``. Canonical events
    keep their established public ID. Alias events receive a bounded stream-index
    namespace that contains no post identifier or raw stream key, preventing
    duplicate React/API identities without inventing event chronology or mutating
    persisted records.
    """
    if stream_index == 0:
        return entry_id
    return f"legacy-{stream_index}:{entry_id}"


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


def _activity_event_count(value: Any) -> int:
    """Validate one bounded buyer-facing activity-stream read count.

    Redis accepts integer-like values at a lower protocol layer, but the product
    read contract must not coerce booleans, floats, or strings into a request
    budget. The upper bound matches the retained stream window so callers cannot
    request work beyond the product's own retention contract.
    """
    if type(value) is not int:
        raise TypeError("event_count must be an integer")
    if not 1 <= value <= _MAX_ACTIVITY_READ_COUNT:
        raise ValueError(
            f"event_count must be between 1 and {_MAX_ACTIVITY_READ_COUNT}"
        )
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

    ``event_count`` is an exact 1..1000 buyer-facing read budget matching the
    retained stream window. Invalid values fail before Valkey access; this
    function does not broaden the query to other posts or reconstruct missing
    facts. UUID reads include a bounded compatibility bridge for historical
    UUID-equivalent alias streams recorded by startup while all current writers
    remain canonical-only. Cross-stream chronology is comparable at millisecond
    precision only; equal-millisecond historical ties use deterministic
    canonical-first stream precedence rather than pretending stream-local
    sequence counters form a global clock. The final buyer limit is applied
    only after this bounded merge. Canonical entries retain their historical
    public ``event_id``; alias entries are namespaced by bounded stream ordinal
    because Valkey stream IDs are not globally unique across independent keys.
    """
    bounded_event_count = _activity_event_count(event_count)
    pipelined_canonical_entries = await _activity_canonical_entries_if_alias_free(
        valkey_client,
        post_id,
        bounded_event_count,
    )
    if pipelined_canonical_entries is not None:
        return [
            {
                "event_id": entry_id,
                "event_type": activity_fields["event_type"],
                "actor_account_id": activity_fields["actor_account_id"],
                "summary": activity_fields["summary"],
            }
            for entry_id, activity_fields in pipelined_canonical_entries
        ]

    stream_keys = await _activity_read_stream_keys(valkey_client, post_id)

    if len(stream_keys) == 1:
        with traced(
            "lineageweave.valkey.activity_xrevrange",
            {
                "db.system": "redis",
                "db.operation.name": "xrevrange",
                "lineageweave.stream.kind": "activity",
            },
        ):
            canonical_entries = await valkey_client.xrevrange(
                stream_keys[0], count=bounded_event_count
            )
        return [
            {
                "event_id": entry_id,
                "event_type": activity_fields["event_type"],
                "actor_account_id": activity_fields["actor_account_id"],
                "summary": activity_fields["summary"],
            }
            for entry_id, activity_fields in canonical_entries
        ]

    next_entries: list[tuple[tuple[str, dict[str, str]], int]] = []
    stream_results: list[tuple[str, dict[str, str]] | None] = [None] * len(stream_keys)
    with traced(
        "lineageweave.valkey.activity_xrevrange",
        {"db.system": "redis", "db.operation.name": "xrevrange", "lineageweave.stream.kind": "activity"},
    ):
        first_pages = await asyncio.gather(
            *(valkey_client.xrevrange(stream_key, count=1) for stream_key in stream_keys)
        )
        for stream_index, page in enumerate(first_pages):
            if page:
                stream_results[stream_index] = page[0]

        while len(next_entries) < bounded_event_count:
            available = [
                (entry, stream_index)
                for stream_index, entry in enumerate(stream_results)
                if entry is not None
            ]
            if not available:
                break
            newest_entry, newest_stream_index = max(
                available,
                key=lambda item: _activity_compatibility_merge_order(item[0][0], item[1]),
            )
            next_entries.append((newest_entry, newest_stream_index))
            next_page = await valkey_client.xrevrange(
                stream_keys[newest_stream_index],
                max=f"({newest_entry[0]}",
                count=1,
            )
            stream_results[newest_stream_index] = next_page[0] if next_page else None
    return [
        {
            "event_id": _activity_public_event_id(entry_id, stream_index),
            "event_type": activity_fields["event_type"],
            "actor_account_id": activity_fields["actor_account_id"],
            "summary": activity_fields["summary"],
        }
        for (entry_id, activity_fields), stream_index in next_entries
    ]