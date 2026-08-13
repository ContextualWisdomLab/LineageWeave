"""CRUD for `issue_ticket` rows tied to a `source_post`.

Deliberately not a pluggable-LLM channel like `keyman_ingestion.py` or
`entity_relationship_ingestion.py`: a ticket's status is a small closed
enum already modeled in `common_lookup_value` (category `ticket_status`),
and creating/updating a ticket is a direct user action, not something an
LLM derives from text. Ponytail: this is CRUD, not extraction -- adding a
pluggable client here would be an unrequested abstraction for a problem
that doesn't have one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import asyncpg


@dataclass(frozen=True)
class IssueTicket:
    """One `issue_ticket` row, serialized shape."""

    issue_ticket_id: str
    post_id: str
    ticket_status_code: str
    ticket_title: str
    assigned_account_id: str | None
    created_at: str
    updated_at: str


def _serialize_ticket(row: asyncpg.Record) -> dict[str, Any]:
    """Turn one ``issue_ticket`` row into the public JSON shape."""
    return {
        "issue_ticket_id": str(row["issue_ticket_id"]),
        "post_id": str(row["post_id"]),
        "ticket_status_code": row["ticket_status_code"],
        "ticket_title": row["ticket_title"],
        "assigned_account_id": (
            str(row["assigned_account_id"]) if row["assigned_account_id"] is not None else None
        ),
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


async def list_tickets_for_post(conn: asyncpg.Connection, post_id: str) -> list[dict[str, Any]]:
    """Every ticket on `post_id`, newest first."""
    rows = await conn.fetch(
        "select issue_ticket_id, post_id, ticket_status_code, ticket_title, "
        "assigned_account_id, created_at, updated_at "
        "from issue_ticket where post_id = $1 order by created_at desc",
        post_id,
    )
    return [_serialize_ticket(row) for row in rows]


async def create_ticket(
    conn: asyncpg.Connection,
    post_id: str,
    ticket_title: str,
    ticket_status_code: str,
    assigned_account_id: str | None,
) -> dict[str, Any]:
    """Insert one ticket. Raises `asyncpg.ForeignKeyViolationError` if
    `ticket_status_code` is not a real `common_lookup_value` row -- the
    database enforces the closed enum, this function does not re-validate
    it.
    """
    row = await conn.fetchrow(
        "insert into issue_ticket (post_id, ticket_status_code, ticket_title, assigned_account_id) "
        "values ($1, $2, $3, $4) "
        "returning issue_ticket_id, post_id, ticket_status_code, ticket_title, "
        "assigned_account_id, created_at, updated_at",
        post_id,
        ticket_status_code,
        ticket_title,
        assigned_account_id,
    )
    return _serialize_ticket(row)


async def fetch_ticket_post_id(conn: asyncpg.Connection, issue_ticket_id: str) -> str | None:
    """The owning post_id for `issue_ticket_id`, or `None` if it doesn't
    exist -- callers use this to run the same ABAC check every other
    post-scoped write already uses, before mutating a ticket.
    """
    row = await conn.fetchrow(
        "select post_id from issue_ticket where issue_ticket_id = $1", issue_ticket_id
    )
    return str(row["post_id"]) if row is not None else None


async def update_ticket(
    conn: asyncpg.Connection,
    issue_ticket_id: str,
    ticket_status_code: str | None,
    assigned_account_id: str | None,
    clear_assignment: bool,
) -> dict[str, Any] | None:
    """Partial update: only the fields actually provided change.
    `clear_assignment=True` explicitly unassigns (sets NULL) -- distinct
    from `assigned_account_id=None` meaning "leave it as is," since a
    partial-update endpoint needs both "don't touch this" and "set this
    to nothing" as different, expressible outcomes.
    """
    row = await conn.fetchrow(
        """
        update issue_ticket
        set ticket_status_code = coalesce($2, ticket_status_code),
            assigned_account_id = case when $3 then null else coalesce($4, assigned_account_id) end,
            updated_at = now()
        where issue_ticket_id = $1
        returning issue_ticket_id, post_id, ticket_status_code, ticket_title,
                  assigned_account_id, created_at, updated_at
        """,
        issue_ticket_id,
        ticket_status_code,
        clear_assignment,
        assigned_account_id,
    )
    return _serialize_ticket(row) if row is not None else None
