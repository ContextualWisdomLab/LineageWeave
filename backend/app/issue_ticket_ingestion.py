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
from datetime import date
from typing import Any

import asyncpg

from .knowledge_graph import labels_for_codes
from .post_eligibility import source_context_present_sql

_SOURCE_CONTEXT_PRESENT_SQL = source_context_present_sql("p")


def _parse_due_date(due_date: str | None) -> date | None:
    """``YYYY-MM-DD`` -> `date`, or `None` through unchanged. The column
    is a calendar `date`, not timestamptz -- a due day has no timezone,
    and midnight-in-session-TZ was an off-by-one. Raises `ValueError`
    for a malformed string, which callers surface as a 422, not a
    silent no-op or a 500.
    """
    return date.fromisoformat(due_date) if due_date is not None else None


@dataclass(frozen=True)
class IssueTicket:
    """One `issue_ticket` row, serialized shape."""

    issue_ticket_id: str
    post_id: str
    ticket_status_code: str
    ticket_title: str
    assigned_account_id: str | None
    due_date: str | None
    commitment_summary: str | None
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
        "due_date": row["due_date"].isoformat() if row["due_date"] is not None else None,
        "commitment_summary": row["commitment_summary"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


async def _attach_status_labels(
    conn: asyncpg.Connection, tickets: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Hydrate ``ticket_status_label`` from ``common_lookup_value``.

    A missing lookup falls back to the raw code -- never a guessed name.
    """
    labels = await labels_for_codes(conn, [row["ticket_status_code"] for row in tickets])
    for ticket in tickets:
        code = ticket["ticket_status_code"]
        ticket["ticket_status_label"] = labels.get(code, code)
    return tickets


async def list_tickets_for_post(conn: asyncpg.Connection, post_id: str) -> list[dict[str, Any]]:
    """Every ticket on `post_id`, newest first."""
    rows = await conn.fetch(
        "select issue_ticket_id, post_id, ticket_status_code, ticket_title, "
        "assigned_account_id, due_date, commitment_summary, created_at, updated_at "
        "from issue_ticket where post_id = $1 order by created_at desc",
        post_id,
    )
    return await _attach_status_labels(conn, [_serialize_ticket(row) for row in rows])


async def create_ticket(
    conn: asyncpg.Connection,
    post_id: str,
    ticket_title: str,
    ticket_status_code: str,
    assigned_account_id: str | None,
    due_date: str | None = None,
    commitment_summary: str | None = None,
) -> dict[str, Any]:
    """Insert one ticket. Raises `asyncpg.ForeignKeyViolationError` if
    `ticket_status_code` is not a real `common_lookup_value` row -- the
    database enforces the closed enum, this function does not re-validate
    it. Raises `ValueError` if `due_date` is not a well-formed
    `YYYY-MM-DD` string. `due_date`/`commitment_summary` are set when
    this ticket also registers as a calendar/to-do entry (see
    `POST /api/posts/{post_id}/derive-commitment`).
    """
    row = await conn.fetchrow(
        "insert into issue_ticket "
        "(post_id, ticket_status_code, ticket_title, assigned_account_id, due_date, commitment_summary) "
        "values ($1, $2, $3, $4, $5, $6) "
        "returning issue_ticket_id, post_id, ticket_status_code, ticket_title, "
        "assigned_account_id, due_date, commitment_summary, created_at, updated_at",
        post_id,
        ticket_status_code,
        ticket_title,
        assigned_account_id,
        _parse_due_date(due_date),
        commitment_summary,
    )
    labeled = await _attach_status_labels(conn, [_serialize_ticket(row)])
    return labeled[0]


async def fetch_upcoming_commitments(conn: asyncpg.Connection) -> list[dict[str, Any]]:
    """Every not-closed ticket with a `due_date`, across all posts,
    soonest first -- the calendar/to-do surface (`GET /api/calendar`).
    Closed tickets are finished work, not upcoming. Joins in the post's
    visibility fields so the caller can apply the same per-row ABAC
    filter every other cross-post endpoint uses; this function does not
    itself filter by account, since it has no account to check against.
    """
    rows = await conn.fetch(
        "select issue_ticket.issue_ticket_id, issue_ticket.post_id, "
        "issue_ticket.ticket_status_code, issue_ticket.ticket_title, "
        "issue_ticket.assigned_account_id, issue_ticket.due_date, "
        "issue_ticket.commitment_summary, issue_ticket.created_at, "
        "issue_ticket.updated_at, "
        "p.post_title, p.visibility_code, p.corporate_entity_id, p.process_unit_id, "
        f"({_SOURCE_CONTEXT_PRESENT_SQL}) as has_real_source_context "
        "from issue_ticket "
        "join source_post p on p.post_id = issue_ticket.post_id "
        "where issue_ticket.due_date is not null "
        "and issue_ticket.ticket_status_code <> 'closed' "
        "order by issue_ticket.due_date asc"
    )
    tickets = await _attach_status_labels(
        conn,
        [
            {
                **_serialize_ticket(row),
                "post_title": row["post_title"],
                "visibility_code": row["visibility_code"],
                "corporate_entity_id": str(row["corporate_entity_id"]),
                "process_unit_id": str(row["process_unit_id"]),
                "has_real_source_context": bool(row["has_real_source_context"]),
            }
            for row in rows
        ],
    )
    return tickets


async def upsert_commitment_ticket(
    conn: asyncpg.Connection,
    post_id: str,
    ticket_title: str,
    due_date: str | None,
    commitment_summary: str,
) -> dict[str, Any]:
    """Create or refresh the open LLM-derived commitment ticket on a post.

    Re-deriving the same post must not stack duplicate calendar rows --
    an existing open ticket with a commitment_summary is updated in place.
    A closed ticket is left alone so the buyer can keep the historical
    record and still derive a fresh open one.
    """
    existing = await conn.fetchrow(
        "select issue_ticket_id from issue_ticket "
        "where post_id = $1 and commitment_summary is not null "
        "and ticket_status_code <> 'closed' "
        "order by created_at desc limit 1",
        post_id,
    )
    if existing is None:
        return await create_ticket(
            conn,
            post_id,
            ticket_title,
            "open",
            None,
            due_date=due_date,
            commitment_summary=commitment_summary,
        )
    row = await conn.fetchrow(
        """
        update issue_ticket
        set ticket_title = $2,
            due_date = $3,
            commitment_summary = $4,
            updated_at = now()
        where issue_ticket_id = $1
        returning issue_ticket_id, post_id, ticket_status_code, ticket_title,
                  assigned_account_id, due_date, commitment_summary, created_at, updated_at
        """,
        existing["issue_ticket_id"],
        ticket_title,
        _parse_due_date(due_date),
        commitment_summary,
    )
    labeled = await _attach_status_labels(conn, [_serialize_ticket(row)])
    return labeled[0]


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
                  assigned_account_id, due_date, commitment_summary, created_at, updated_at
        """,
        issue_ticket_id,
        ticket_status_code,
        clear_assignment,
        assigned_account_id,
    )
    if row is None:
        return None
    labeled = await _attach_status_labels(conn, [_serialize_ticket(row)])
    return labeled[0]
