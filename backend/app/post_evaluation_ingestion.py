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
    """One persisted per-criterion LLM-as-a-Judge response for a post."""

    criterion_code: str
    criterion_label: str | None
    response_category: int
    rubric_version: str


async def ingest_post_evaluation(
    database_connection: asyncpg.Connection,
    post_evaluation_client: PostEvaluationClient,
    post_id: str,
    post_title: str,
    post_body: str,
) -> list[PersistedEvaluation]:
    """Judge the post and upsert one row per criterion via ``to_irt_row``."""
    judge_result = post_evaluation_client.evaluate(post_title, post_body)
    criterion_responses = irt_responses_from_result(judge_result)
    for criterion_response in criterion_responses:
        await database_connection.execute(
            """
            insert into post_evaluation_response
                (post_id, criterion_code, rubric_version, response_category)
            values ($1, $2, $3, $4)
            on conflict (post_id, criterion_code, rubric_version)
            do update set response_category = excluded.response_category,
                          judged_at = now()
            """,
            post_id,
            criterion_response.criterion_code,
            RUBRIC_VERSION,
            criterion_response.response_category,
        )
    return await fetch_post_evaluation(database_connection, post_id)


async def fetch_post_evaluation(
    database_connection: asyncpg.Connection, post_id: str
) -> list[PersistedEvaluation]:
    """Load this post's persisted per-criterion evaluation responses, ordered by criterion code."""
    persisted_evaluation_rows = await database_connection.fetch(
        """
        select evaluation_response.criterion_code,
               criterion_lookup.lookup_label as criterion_label,
               evaluation_response.response_category,
               evaluation_response.rubric_version
        from post_evaluation_response evaluation_response
        left join common_lookup_value criterion_lookup
          on criterion_lookup.lookup_code = evaluation_response.criterion_code
        where evaluation_response.post_id = $1
        order by evaluation_response.criterion_code
        """,
        post_id,
    )
    return [
        PersistedEvaluation(
            criterion_code=evaluation_row["criterion_code"],
            criterion_label=evaluation_row["criterion_label"],
            response_category=evaluation_row["response_category"],
            rubric_version=evaluation_row["rubric_version"],
        )
        for evaluation_row in persisted_evaluation_rows
    ]
