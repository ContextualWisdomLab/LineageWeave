"""Authorized read projection for the post detail 5W1H panel."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import asyncpg

from lineageweave.five_w1h import assemble_five_w1h_slots, slots_payload

from .entity_relationship_ingestion import fetch_post_counterparties
from .post_chat_ingestion import find_linked_post_ids
from .post_summary_ingestion import fetch_persisted_summary


async def load_five_w1h_slots(
    conn: asyncpg.Connection,
    post_id: str,
    can_see_post: Callable[[asyncpg.Record], bool],
) -> dict[str, Any]:
    """Build 5W1H from stored projections and visible lineage only."""
    # allow_stale=True: 5W1H never reads korean_summary or summary_status
    # from this payload, only roles_and_responsibilities/key_events, which
    # are valid person/org/event evidence regardless of contract version --
    # gating them on the same freshness check as the Korean summary text
    # silently emptied "who"/"what" for every post summarized before the
    # last contract bump, even though nothing about that data was stale.
    summary = await fetch_persisted_summary(conn, post_id, allow_stale=True) or {}
    evidence_claims = await conn.fetch(
        """
        select slot_code, value_text, evidence_text
          from post_summary_five_w1h
         where post_id = $1
         order by slot_code, value_ordinal
        """,
        post_id,
    )
    linked = await find_linked_post_ids(conn, post_id)
    candidate_ids = sorted(linked.direct | linked.indirect)
    linked_titles: list[str] = []
    if candidate_ids:
        rows = await conn.fetch(
            "select post_id, post_title, visibility_code, corporate_entity_id, process_unit_id "
            "from source_post where post_id = any($1::uuid[])",
            candidate_ids,
        )
        linked_titles = [row["post_title"] for row in rows if can_see_post(row)]

    counterparties = await fetch_post_counterparties(conn, post_id)
    slots = assemble_five_w1h_slots(
        roles=summary.get("roles_and_responsibilities", []),
        key_events=summary.get("key_events", []),
        counterparties=[row["counterparty_entity_name"] for row in counterparties],
        lineage_node_labels=linked_titles,
        evidence_claims=[dict(row) for row in evidence_claims],
    )
    return {"post_id": post_id, "slots": slots_payload(slots)}
