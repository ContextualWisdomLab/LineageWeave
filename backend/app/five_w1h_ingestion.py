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
    summary = await fetch_persisted_summary(conn, post_id) or {}
    linked = await find_linked_post_ids(conn, post_id)
    candidate_ids = sorted(linked.direct | linked.indirect)
    linked_titles: list[str] = []
    if candidate_ids:
        rows = await conn.fetch(
            "select post_id, post_title, visibility_code, corporate_entity_id "
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
    )
    return {"post_id": post_id, "slots": slots_payload(slots)}
