"""Source-post valid-time revisions for cutoff-known bodies (ADR 0025).

The analysis-run registry stays aggregates-only. Callers that need the
sentence a run knew must read ``source_post_revision`` through an
authorized post fetch with ``as_of``. A missing cover is omitted --
never a fabricated cutoff body or a TEPP theta.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import asyncpg


def _as_utc(timestamp_value: datetime) -> datetime:
    """Treat a naive clock as UTC so interval tests stay timezone-aware."""
    if timestamp_value.tzinfo is None:
        return timestamp_value.replace(tzinfo=UTC)
    return timestamp_value.astimezone(UTC)


def parse_as_of_clock(clock_text: str) -> datetime:
    """Parse an ISO-8601 as-of clock.

    Next action: pass the analysis-run cutoff, then compare ``known_at``
    with the live body. Empty or unparseable values raise ``ValueError``.
    """
    normalized_clock_text = clock_text.strip()
    if not normalized_clock_text:
        raise ValueError("as_of is empty")
    if normalized_clock_text.endswith("Z"):
        normalized_clock_text = normalized_clock_text[:-1] + "+00:00"
    parsed_clock = datetime.fromisoformat(normalized_clock_text)
    return _as_utc(parsed_clock)


def revision_covers_clock(
    written_at: datetime,
    superseded_at: datetime | None,
    as_of: datetime,
) -> bool:
    """True when this revision was current at ``as_of``.

    The interval is half-open: ``written_at <= as_of < superseded_at``.
    A null ``superseded_at`` means the revision is still current.
    """
    revision_start = _as_utc(written_at)
    query_clock = _as_utc(as_of)
    if revision_start > query_clock:
        return False
    if superseded_at is None:
        return True
    return _as_utc(superseded_at) > query_clock


def _iso_timestamp(timestamp_value: Any) -> str:
    """Serialize a timestamptz the same way post detail already does."""
    return (
        timestamp_value.isoformat()
        if hasattr(timestamp_value, "isoformat")
        else str(timestamp_value)
    )


async def fetch_known_at_revision(
    database_connection: asyncpg.Connection,
    post_id: str,
    as_of: datetime,
) -> dict[str, str] | None:
    """Return the title/body current at ``as_of``, or None when none exists.

    Does not invent a sentence. Does not return a live body under a
    cutoff label when no revision covers the clock.
    """
    source_post_revision_row = await database_connection.fetchrow(
        "select source_post_revision_id, post_title, post_body, written_at "
        "from source_post_revision "
        "where post_id = $1 "
        "and written_at <= $2 "
        "and (superseded_at is null or superseded_at > $2) "
        "order by written_at desc "
        "limit 1",
        post_id,
        as_of,
    )
    if source_post_revision_row is None:
        return None
    return {
        "source_post_revision_id": str(
            source_post_revision_row["source_post_revision_id"]
        ),
        "post_title": source_post_revision_row["post_title"],
        "post_body": source_post_revision_row["post_body"],
        "written_at": _iso_timestamp(source_post_revision_row["written_at"]),
        "as_of": _iso_timestamp(as_of),
    }


async def fetch_known_at_revisions(
    database_connection: asyncpg.Connection,
    post_ids: list[str],
    as_of: datetime,
) -> dict[str, dict[str, str]]:
    """Batch-load the retained revision covering ``as_of`` for each post.

    Missing covers are omitted so callers can report an honest historical-body
    limitation without substituting the live title or body.
    """

    if not post_ids:
        return {}
    source_post_revision_rows = await database_connection.fetch(
        "select distinct on (post_id) post_id, source_post_revision_id, "
        "post_title, post_body, written_at "
        "from source_post_revision "
        "where post_id = any($1::uuid[]) "
        "and written_at <= $2 "
        "and (superseded_at is null or superseded_at > $2) "
        "order by post_id, written_at desc",
        post_ids,
        as_of,
    )
    return {
        str(source_post_revision_row["post_id"]): {
            "source_post_revision_id": str(
                source_post_revision_row["source_post_revision_id"]
            ),
            "post_title": source_post_revision_row["post_title"],
            "post_body": source_post_revision_row["post_body"],
            "written_at": _iso_timestamp(source_post_revision_row["written_at"]),
            "as_of": _iso_timestamp(as_of),
        }
        for source_post_revision_row in source_post_revision_rows
    }
