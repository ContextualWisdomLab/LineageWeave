"""Persist ticket activity on the transactional outbox, then publish.

A hidden post is omitted from the buyer list. This module never invents
a Valkey entry id or a theta.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Mapping

from lineageweave.valkey_outbox import DELIVERY_DELIVERED, DELIVERY_PENDING

if TYPE_CHECKING:
    import asyncpg

__all__ = [
    "load_visible_outbox_rows",
    "mark_outbox_delivered",
    "persist_pending_outbox_event",
    "persist_pending_outbox_event_sync",
    "mark_outbox_delivered_sync",
]


_INSERT_PENDING = """
insert into activity_outbox_event (
    post_id, issue_ticket_id, event_type_code, actor_account_id,
    event_summary, delivery_status_code
) values ($1::uuid, $2::uuid, $3, $4::uuid, $5, $6)
on conflict (post_id, event_type_code, event_summary) do update
    set issue_ticket_id = coalesce(
        activity_outbox_event.issue_ticket_id, excluded.issue_ticket_id
    )
returning outbox_event_id, delivery_status_code, valkey_entry_id
"""

_MARK_DELIVERED = """
update activity_outbox_event
   set delivery_status_code = $2,
       valkey_entry_id = $3,
       delivered_at = now()
 where outbox_event_id = $1::uuid
   and delivery_status_code = $4
   and valkey_entry_id is null
"""

_LIST_ROWS = """
select
    outbox.outbox_event_id,
    outbox.post_id,
    post.post_title,
    post.visibility_code,
    post.corporate_entity_id,
    outbox.event_type_code,
    outbox.event_summary,
    outbox.delivery_status_code,
    outbox.valkey_entry_id,
    outbox.requested_at
  from activity_outbox_event as outbox
  join source_post as post on post.post_id = outbox.post_id
 order by outbox.requested_at desc, outbox.outbox_event_id
"""


async def persist_pending_outbox_event(
    conn: "asyncpg.Connection",
    post_id: str,
    event_type_code: str,
    actor_account_id: str,
    event_summary: str,
    issue_ticket_id: str | None = None,
) -> str:
    """Insert a pending row. Idempotent on (post, type, summary)."""
    row = await conn.fetchrow(
        _INSERT_PENDING,
        post_id,
        issue_ticket_id,
        event_type_code,
        actor_account_id,
        event_summary,
        DELIVERY_PENDING,
    )
    return str(row["outbox_event_id"])


async def mark_outbox_delivered(
    conn: "asyncpg.Connection",
    outbox_event_id: str,
    valkey_entry_id: str,
) -> None:
    """Record the Valkey stream id. No-op when already delivered."""
    entry = str(valkey_entry_id or "").strip()
    if not entry:
        return
    await conn.execute(
        _MARK_DELIVERED,
        outbox_event_id,
        DELIVERY_DELIVERED,
        entry,
        DELIVERY_PENDING,
    )


async def load_visible_outbox_rows(
    conn: "asyncpg.Connection",
    can_see_post: Callable[[Mapping[str, Any]], bool],
) -> list[dict[str, Any]]:
    """Read outbox rows the buyer may see. Hidden posts drop here."""
    rows = await conn.fetch(_LIST_ROWS)
    return [dict(row) for row in rows if can_see_post(row)]


def persist_pending_outbox_event_sync(
    cur: Any,
    post_id: str,
    event_type_code: str,
    actor_account_id: str,
    event_summary: str,
    issue_ticket_id: str | None = None,
) -> str:
    """psycopg2 twin of :func:`persist_pending_outbox_event` for ``make seed``."""
    cur.execute(
        """
        insert into activity_outbox_event (
            post_id, issue_ticket_id, event_type_code, actor_account_id,
            event_summary, delivery_status_code
        ) values (%s, %s, %s, %s, %s, %s)
        on conflict (post_id, event_type_code, event_summary) do update
            set issue_ticket_id = coalesce(
                activity_outbox_event.issue_ticket_id, excluded.issue_ticket_id
            )
        returning outbox_event_id
        """,
        (
            post_id,
            issue_ticket_id,
            event_type_code,
            actor_account_id,
            event_summary,
            DELIVERY_PENDING,
        ),
    )
    return str(cur.fetchone()[0])


def mark_outbox_delivered_sync(cur: Any, outbox_event_id: str, valkey_entry_id: str) -> None:
    """psycopg2 twin of :func:`mark_outbox_delivered` for ``make seed``."""
    entry = str(valkey_entry_id or "").strip()
    if not entry:
        return
    cur.execute(
        """
        update activity_outbox_event
           set delivery_status_code = %s,
               valkey_entry_id = %s,
               delivered_at = now()
         where outbox_event_id = %s
           and delivery_status_code = %s
           and valkey_entry_id is null
        """,
        (DELIVERY_DELIVERED, entry, outbox_event_id, DELIVERY_PENDING),
    )
