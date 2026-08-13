"""Persist and load the popup's Korean summary / key events / R&R."""

from __future__ import annotations

from typing import Any

import asyncpg

from lineageweave.post_summary import PostSummary, RoleResponsibility


async def fetch_persisted_summary(conn: asyncpg.Connection, post_id: str) -> dict[str, Any] | None:
    """Return the stored summary payload, or None when none has been written."""
    header = await conn.fetchrow(
        "select korean_summary from post_summary_result where post_id = $1",
        post_id,
    )
    if header is None:
        return None
    events = await conn.fetch(
        "select event_text from post_summary_event where post_id = $1 order by event_ordinal",
        post_id,
    )
    roles = await conn.fetch(
        "select person_name, responsibility from post_summary_role "
        "where post_id = $1 order by person_name",
        post_id,
    )
    return {
        "post_id": post_id,
        "korean_summary": header["korean_summary"],
        "key_events": [row["event_text"] for row in events],
        "roles_and_responsibilities": [
            {"person_name": row["person_name"], "responsibility": row["responsibility"]}
            for row in roles
        ],
    }


async def persist_post_summary(conn: asyncpg.Connection, post_id: str, summary: PostSummary) -> dict[str, Any]:
    """Replace the stored summary for ``post_id`` and return the public payload."""
    await conn.execute("delete from post_summary_result where post_id = $1", post_id)
    await conn.execute(
        "insert into post_summary_result (post_id, korean_summary) values ($1, $2)",
        post_id,
        summary.korean_summary,
    )
    for ordinal, event_text in enumerate(summary.key_events):
        await conn.execute(
            "insert into post_summary_event (post_id, event_ordinal, event_text) values ($1, $2, $3)",
            post_id,
            ordinal,
            event_text,
        )
    for role in summary.roles_and_responsibilities:
        await conn.execute(
            "insert into post_summary_role (post_id, person_name, responsibility) values ($1, $2, $3)",
            post_id,
            role.person_name,
            role.responsibility,
        )
    payload = await fetch_persisted_summary(conn, post_id)
    if payload is None:
        raise RuntimeError("persist_post_summary wrote no row")
    return payload


def seeded_demo_summary() -> PostSummary:
    """Synthetic Korean summary for the demo public post -- not an LLM result."""
    return PostSummary(
        korean_summary=(
            "에이다 웨스트가 데모 코프를 대표해 노스리지 그리드의 프리야 네어에게 "
            "지연된 출하 일정을 확인했다."
        ),
        key_events=("출하 지연 후속 연락",),
        roles_and_responsibilities=(
            RoleResponsibility(person_name="Ada West", responsibility="일정 확인 후속"),
            RoleResponsibility(person_name="Priya Nair", responsibility="고객 측 수신"),
        ),
    )
