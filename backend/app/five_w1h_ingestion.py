"""Assemble 5W1H slots from authorized post, summary, and lineage facts."""

from __future__ import annotations

from typing import Any

import asyncpg

from lineageweave.five_w1h import (
    answer_lineage_question,
    assemble_five_w1h_slots,
    slots_payload,
)

from backend.app.post_chat_ingestion import find_linked_post_ids
from backend.app.post_summary_ingestion import fetch_persisted_summary


async def load_five_w1h_slots(
    conn: asyncpg.Connection,
    post_id: str,
    created_at: object,
    can_see_post: Any,
) -> dict[str, object]:
    """Return buyer 5W1H slots for one authorized post.

    Missing summary, counterparties, or lineage neighbors leave those
    slots empty -- never a guessed sentence.
    """
    stored = await fetch_persisted_summary(conn, post_id)
    roles = stored["roles_and_responsibilities"] if stored is not None else []
    key_events = stored["key_events"] if stored is not None else []
    counterparties = await conn.fetch(
        "select counterparty_entity_name from post_counterparty_entity where post_id = $1",
        post_id,
    )
    linked = await find_linked_post_ids(conn, post_id)
    neighbor_ids = list(linked.direct | linked.indirect)
    lineage_labels: list[str] = []
    lineage_occurred: list[object] = []
    if neighbor_ids:
        rows = await conn.fetch(
            "select post_id, post_title, visibility_code, corporate_entity_id, created_at "
            "from source_post where post_id = any($1::uuid[])",
            neighbor_ids,
        )
        for row in rows:
            if not can_see_post(row):
                continue
            lineage_labels.append(row["post_title"])
            lineage_occurred.append(row["created_at"])
    slots = assemble_five_w1h_slots(
        roles=roles,
        key_events=key_events,
        created_at=created_at,
        lineage_occurred_at=lineage_occurred,
        counterparty_names=[row["counterparty_entity_name"] for row in counterparties],
        lineage_node_labels=lineage_labels,
    )
    return {"post_id": post_id, "slots": slots_payload(slots), "_slots": slots}


async def answer_authorized_lineage_question(
    conn: asyncpg.Connection,
    post_id: str,
    created_at: object,
    question: str,
    can_see_post: Any,
) -> dict[str, object]:
    payload = await load_five_w1h_slots(conn, post_id, created_at, can_see_post)
    answer = answer_lineage_question(question, payload["_slots"])
    return {
        "post_id": post_id,
        "question": answer["question"],
        "slot_code": answer["slot_code"],
        "values": answer["values"],
        "grounded": answer["grounded"],
        "empty_next_action": answer["empty_next_action"],
        "who": answer["who"],
        "what_happened": answer["what_happened"],
        "chronology": answer["chronology"],
        "show_lineage": True,
    }
