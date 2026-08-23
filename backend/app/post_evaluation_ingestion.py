"""Persist one post's LLM-as-a-Judge IRT row (ADR 0003 slice 2)."""

from __future__ import annotations

from dataclasses import dataclass

import asyncpg

from lineageweave.post_evaluation import (
    RUBRIC_VERSION,
    PostEvaluationClient,
    irt_responses_from_result,
)


@dataclass(frozen=True)
class PersistedEvaluation:
    """One persisted per-criterion evaluation response for a post."""

    criterion_code: str
    criterion_label: str | None
    response_category: int
    rubric_version: str


async def ingest_post_evaluation(
    conn: asyncpg.Connection,
    client: PostEvaluationClient,
    post_id: str,
    post_title: str,
    post_body: str,
) -> list[PersistedEvaluation]:
    """Judge the post and upsert one row per criterion via ``to_irt_row``."""
    result = client.evaluate(post_title, post_body)
    responses = irt_responses_from_result(result)
    for response in responses:
        await conn.execute(
            """
            insert into post_evaluation_response
                (post_id, criterion_code, rubric_version, response_category)
            values ($1, $2, $3, $4)
            on conflict (post_id, criterion_code, rubric_version)
            do update set response_category = excluded.response_category,
                          judged_at = now()
            """,
            post_id,
            response.criterion_code,
            RUBRIC_VERSION,
            response.response_category,
        )
    return await fetch_post_evaluation(conn, post_id)


async def fetch_post_evaluation(conn: asyncpg.Connection, post_id: str) -> list[PersistedEvaluation]:
    """Load a post's persisted evaluations ordered by criterion code."""
    rows = await conn.fetch(
        """
        select e.criterion_code, v.lookup_label as criterion_label,
               e.response_category, e.rubric_version
        from post_evaluation_response e
        left join common_lookup_value v on v.lookup_code = e.criterion_code
        where e.post_id = $1
        order by e.criterion_code
        """,
        post_id,
    )
    return [
        PersistedEvaluation(
            criterion_code=row["criterion_code"],
            criterion_label=row["criterion_label"],
            response_category=row["response_category"],
            rubric_version=row["rubric_version"],
        )
        for row in rows
    ]
