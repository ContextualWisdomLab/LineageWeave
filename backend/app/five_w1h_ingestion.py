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
    database_connection: asyncpg.Connection,
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
    persisted_summary = (
        await fetch_persisted_summary(
            database_connection,
            post_id,
            allow_stale=True,
        )
        or {}
    )
    persisted_evidence_claims = await database_connection.fetch(
        """
        select slot_code, value_text, evidence_text
          from post_summary_five_w1h
         where post_id = $1
         order by slot_code, value_ordinal
        """,
        post_id,
    )
    linked_post_ids = await find_linked_post_ids(database_connection, post_id)
    candidate_post_ids = sorted(linked_post_ids.direct | linked_post_ids.indirect)
    visible_linked_post_titles: list[str] = []
    if candidate_post_ids:
        linked_post_rows = await database_connection.fetch(
            "select post_id, post_title, visibility_code, corporate_entity_id, process_unit_id "
            "from source_post where post_id = any($1::uuid[])",
            candidate_post_ids,
        )
        visible_linked_post_titles = [
            linked_post_row["post_title"]
            for linked_post_row in linked_post_rows
            if can_see_post(linked_post_row)
        ]

    post_counterparty_rows = await fetch_post_counterparties(
        database_connection,
        post_id,
    )
    five_w1h_slots = assemble_five_w1h_slots(
        post_summary_roles=persisted_summary.get("roles_and_responsibilities", []),
        key_events=persisted_summary.get("key_events", []),
        counterparties=[
            post_counterparty_row["counterparty_entity_name"]
            for post_counterparty_row in post_counterparty_rows
        ],
        lineage_node_labels=visible_linked_post_titles,
        evidence_claims=[
            dict(persisted_evidence_claim)
            for persisted_evidence_claim in persisted_evidence_claims
        ],
    )
    return {"post_id": post_id, "slots": slots_payload(five_w1h_slots)}
