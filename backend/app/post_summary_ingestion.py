"""Persist and load the popup's Korean summary / key events / R&R."""

from __future__ import annotations

from typing import Any

import asyncpg

from lineageweave.fixtures import fixture_thread_cast
from lineageweave.ontology import ontology_annotations
from lineageweave.post_summary import ACTOR_TYPE_ORGANIZATION, PostSummary, RoleResponsibility


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
        "select actor_name, responsibility, actor_type_code, affiliated_organization_name "
        "from post_summary_role where post_id = $1 order by actor_name",
        post_id,
    )
    return {
        "post_id": post_id,
        "korean_summary": header["korean_summary"],
        "key_events": [row["event_text"] for row in events],
        "roles_and_responsibilities": [
            {
                "actor_name": row["actor_name"],
                "responsibility": row["responsibility"],
                "actor_type_code": row["actor_type_code"],
                "affiliated_organization_name": row["affiliated_organization_name"],
                **ontology_annotations(row["actor_type_code"]),
            }
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
            "insert into post_summary_role "
            "(post_id, actor_name, responsibility, actor_type_code, affiliated_organization_name) "
            "values ($1, $2, $3, $4, $5)",
            post_id,
            role.actor_name,
            role.responsibility,
            role.actor_type_code,
            role.affiliated_organization_name,
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
            RoleResponsibility(
                actor_name="Ada West",
                responsibility="일정 확인 후속",
                affiliated_organization_name="Demo Corp",
            ),
            RoleResponsibility(
                actor_name="Priya Nair",
                responsibility="고객 측 수신",
                affiliated_organization_name="Northridge Grid",
            ),
            RoleResponsibility(
                actor_name="당사",
                responsibility="출하 일정 확정",
                actor_type_code=ACTOR_TYPE_ORGANIZATION,
            ),
        ),
    )


def seeded_fixture_summary(post_title: str) -> PostSummary | None:
    """Synthetic Korean summary for a reconstruct/calendar fixture title.

    Not an LLM result. Returns None when the title is not a known seed
    fixture so a missing row still 503s instead of inventing prose.
    R&R names come from ``fixture_thread_cast`` -- rec-006 and the
    calendar commitment stay empty because they have no cast people.
    """
    summary = _FIXTURE_SUMMARIES.get(post_title)
    if summary is None:
        return None
    roles = _roles_for_fixture(post_title)
    if not roles:
        return summary
    return PostSummary(
        korean_summary=summary.korean_summary,
        key_events=summary.key_events,
        roles_and_responsibilities=roles,
    )


def _roles_for_fixture(post_title: str) -> tuple[RoleResponsibility, ...]:
    """Title-derived R&R for the fixture cast -- not an LLM judge."""
    cast = fixture_thread_cast(post_title)
    if cast is None or not cast.person_names:
        return ()
    return tuple(
        RoleResponsibility(
            actor_name=name,
            responsibility=responsibility,
            affiliated_organization_name=_FIXTURE_ROLE_AFFILIATION.get(name),
        )
        for name in cast.person_names
        if (responsibility := _FIXTURE_ROLE_RESPONSIBILITY.get(name))
    )


_FIXTURE_ROLE_RESPONSIBILITY = {
    "Ada West": "우리 측 후속",
    "Priya Nair": "고객 측 수신",
    "Jordan Hale": "사양 검토",
}

_FIXTURE_ROLE_AFFILIATION = {
    "Ada West": "Demo Corp",
    "Priya Nair": "Northridge Grid",
    "Jordan Hale": "Westfield Power",
}


def _summary(korean: str, *events: str) -> PostSummary:
    return PostSummary(korean_summary=korean, key_events=events)


_FIXTURE_SUMMARIES: dict[str, PostSummary] = {
    "Initial site visit and project scope discussion": _summary(
        "착수 전에 현장을 둘러보고 이번 일의 작업 범위를 맞추는 회의가 열렸다.",
        "초기 현장 방문",
        "프로젝트 범위 논의",
    ),
    "Pricing renegotiation follow-up": _summary(
        "초기 방문 이후 가격 재협상을 이어가는 후속 협의가 열렸다.",
        "가격 재협상 후속",
    ),
    "Pricing renegotiation: revised quote sent": _summary(
        "재협상 결과를 반영한 수정 견적이 상대에게 발송되었다.",
        "수정 견적 발송",
    ),
    "Delivery schedule question raised": _summary(
        "가격 논의와 별도로 납품 일정에 대한 질문이 올라왔다.",
        "납품 일정 질의",
    ),
    "Delivery schedule confirmed with logistics": _summary(
        "물류 담당과 확인한 뒤 납품 일정이 확정되었다.",
        "물류 확인",
        "납품 일정 확정",
    ),
    "Unrelated: annual account review": _summary(
        "연례 계정 검토가 진행되었다. 가격 재협상이나 납품 일정과는 주제가 다르다.",
        "연례 계정 검토",
    ),
    "Technical specification review meeting": _summary(
        "기술 사양을 점검하는 검토 회의가 열렸다.",
        "기술 사양 검토 회의",
    ),
    "Specification revision requested": _summary(
        "검토 결과에 따라 사양 수정이 요청되었다.",
        "사양 수정 요청",
    ),
    "Revised specification approved": _summary(
        "수정된 기술 사양이 승인되어 후속 작업 기준이 정해졌다.",
        "수정 사양 승인",
    ),
    "Follow-up on the Riverbend order confirmation": _summary(
        "리버벤드 주문은 이미 확인됐고, 수정 납품 일정을 다음 금요일까지 보내기로 했다.",
        "주문 확인 완료",
        "납품 일정 약속",
    ),
}
