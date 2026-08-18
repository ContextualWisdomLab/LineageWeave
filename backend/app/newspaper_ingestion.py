"""Persist a scheduled newspaper edition as a board post.

Called from ``make seed`` / a scheduler. Not an HTTP buyer route and
not a generate button. Ranks are read from already-persisted
``report_member_score`` rows (fast-mlsirm). Theta never leaves this
module.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from lineageweave.newspaper_edition import (
    EditionKind,
    assemble_newspaper_edition,
    edition_from_row,
    newspaper_thread_key,
    newspaper_title,
    render_newspaper_html,
)
from lineageweave.orgmetra_client import OrgmetraClient, OrgmetraGrain

_GRAINS: tuple[OrgmetraGrain, ...] = ("corporate", "process_unit", "team")
_GROUPING: dict[OrgmetraGrain, str | None] = {
    "corporate": "corporate_entity",
    "process_unit": "process_unit",
    "team": None,
}
# Same published rubric as ``lineageweave.post_evaluation.RUBRIC_VERSION``.
# Copied here so the scheduler does not import fast-mlsirm.
CONSUMED_RUBRIC_VERSION = "2026-08-13"


def consume_ranked_titles(
    cur: Any,
    grouping_kind: str,
    grouping_key: str,
    period_code: str,
) -> tuple[str, ...]:
    """Titles already ranked by persisted fast-mlsirm member score."""
    cur.execute(
        """
        select p.post_title
        from report_member_score m
        join source_post p on p.post_id = m.post_id
        where m.grouping_kind = %s
          and m.grouping_key = %s
          and m.period_code = %s
          and m.rubric_version = %s
        order by m.theta_eap desc
        """,
        (grouping_kind, grouping_key, period_code, CONSUMED_RUBRIC_VERSION),
    )
    return tuple(row[0] for row in cur.fetchall())


def publish_newspaper_edition(
    cur: Any,
    *,
    kind: EditionKind,
    period_code: str,
    orgmetra: OrgmetraClient,
    author_account_id: str,
    corporate_entity_id: str,
    process_unit_id: str,
    created_at: datetime,
) -> str:
    """Upsert one newspaper source_post. Returns the post id."""
    ranked: dict[tuple[OrgmetraGrain, str], tuple[str, ...]] = {}
    if orgmetra.available:
        for grain in _GRAINS:
            grouping = _GROUPING[grain]
            if grouping is None:
                continue
            for unit in orgmetra.list_units(grain):
                ranked[(grain, unit.unit_id)] = consume_ranked_titles(
                    cur,
                    grouping,
                    unit.unit_id,
                    period_code,
                )
    edition = assemble_newspaper_edition(
        kind=kind,
        period_code=period_code,
        orgmetra=orgmetra,
        ranked_titles_by_unit=ranked,
    )
    title = newspaper_title(kind, period_code)
    body = render_newspaper_html(edition)
    thread_key = newspaper_thread_key(kind)
    clock = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
    cur.execute(
        "select post_id from source_post where thread_group_key = %s and secondary_grouping_key = %s",
        (thread_key, period_code),
    )
    existing = cur.fetchone()
    if existing is not None:
        cur.execute(
            "update source_post set post_title = %s, post_body = %s, updated_at = %s where post_id = %s",
            (title, body, clock, existing[0]),
        )
        return str(existing[0])
    cur.execute(
        """
        insert into source_post (
            author_account_id, corporate_entity_id, process_unit_id,
            post_title, post_body, voc_type_code, visibility_code,
            thread_group_key, secondary_grouping_key, created_at, updated_at
        ) values (%s, %s, %s, %s, %s, 'voc', 'public', %s, %s, %s, %s)
        returning post_id
        """,
        (
            author_account_id,
            corporate_entity_id,
            process_unit_id,
            title,
            body,
            thread_key,
            period_code,
            clock,
            clock,
        ),
    )
    return str(cur.fetchone()[0])


__all__ = [
    "CONSUMED_RUBRIC_VERSION",
    "consume_ranked_titles",
    "edition_from_row",
    "publish_newspaper_edition",
]
