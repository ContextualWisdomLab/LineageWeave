"""Ask Cubee answers from authorized source + lineage + ontology query."""

from __future__ import annotations

from typing import Any

import asyncpg

from lineageweave.board_search import classify_board_query
from lineageweave.five_w1h import ungrounded_question_next_action

from backend.app.five_w1h_ingestion import answer_authorized_lineage_question


async def answer_ask_cubee(
    conn: asyncpg.Connection,
    *,
    question: str,
    post_id: str | None,
    post_created_at: object | None,
    can_see_post: Any,
) -> dict[str, object]:
    """Grounded Ask Cubee. Missing post or unbound question fail-closes."""
    if post_id and post_created_at is not None:
        return await answer_authorized_lineage_question(
            conn,
            post_id,
            post_created_at,
            question,
            can_see_post,
        )
    people = await conn.fetch("select person_name from cataloged_person")
    orgs = await conn.fetch("select entity_name from corporate_entity")
    bind = classify_board_query(
        question,
        person_names=[row["person_name"] for row in people],
        organization_names=[row["entity_name"] for row in orgs],
    )
    if bind is None:
        return {
            "post_id": None,
            "question": question.strip(),
            "slot_code": None,
            "values": [],
            "grounded": False,
            "empty_next_action": ungrounded_question_next_action(),
            "who": [],
            "what_happened": [],
            "chronology": [],
            "show_lineage": False,
        }
    mentions = await conn.fetch(
        """
        select ppm.post_id, p.created_at, p.visibility_code, p.corporate_entity_id
        from post_person_mention ppm
        join cataloged_person cp on cp.person_id = ppm.person_id
        join source_post p on p.post_id = ppm.post_id
        where lower(cp.person_name) = lower($1)
        order by p.created_at desc
        """,
        str(bind.get("catalog_name") or ""),
    )
    for row in mentions:
        if can_see_post(row):
            return await answer_authorized_lineage_question(
                conn,
                str(row["post_id"]),
                row["created_at"],
                question,
                can_see_post,
            )
    return {
        "post_id": None,
        "question": question.strip(),
        "slot_code": None,
        "values": [],
        "grounded": False,
        "empty_next_action": ungrounded_question_next_action(),
        "who": [],
        "what_happened": [],
        "chronology": [],
        "show_lineage": False,
    }
