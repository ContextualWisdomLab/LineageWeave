"""Persist and load the popup's Korean summary / key events / R&R.

ADR 0009 / 0019 / 0027: an R&R actor is not just per-post free text --
when it is a team, organization, or already-cataloged person, it is
resolved to a shared catalog identity (``cataloged_team`` /
``corporate_entity`` / ``cataloged_person``) stored on the role row and
a Knowledge Graph mention edge is written, so the same "설계팀" or
organization named across two posts becomes one linkable node. Fetch
never reconstructs that id by ``entity_name`` or ``person_name``; those
columns are not unique. A person actor is opportunistically joined to
an *existing* ``cataloged_person`` row by name when Keyman extraction
has already cataloged that name. The resolved ``cataloged_person_id``
is stored on the role so a later read does not rejoin by display name.
The R&R evidence is written to ``post_summary_person_mention`` rather
than Keyman's ``post_person_mention`` so either extractor can replace
its own result without leaving or deleting the other's evidence.

ADR 0010: an organization actor's name is resolved via
``get_or_create_corporate_entity`` -- similarity matching first, then
an LLM-proposed, search-corroborated hierarchy placement before
creating a real new row, so a real dataset's first mention of a
counterparty organization actually populates the corporate hierarchy
tree instead of staying permanently unresolved.  Inference,
verification, and the short advisory-lock creation transaction finish
before the summary-replacement transaction begins; slow external work
therefore cannot extend the lock or the atomic replacement window.
"""

from __future__ import annotations

from typing import Any

import asyncpg

from lineageweave.corporate_hierarchy_inference import (
    CorporateHierarchyInferenceClient,
    NullCorporateHierarchyInferenceClient,
)
from lineageweave.fixtures import fixture_thread_cast
from lineageweave.knowledge_graph import (
    NODE_CORPORATE_ENTITY,
    NODE_PERSON,
    NODE_TEAM,
)
from lineageweave.ontology import LW, ontology_annotations
from lineageweave.post_summary import (
    ACTOR_TYPE_ORGANIZATION,
    ACTOR_TYPE_PERSON,
    ACTOR_TYPE_TEAM,
    KeyEvent,
    PostSummary,
    POST_SUMMARY_CONTRACT_VERSION,
    normalize_project_key,
    RoleResponsibility,
)
from lineageweave.relation_verification import (
    NullRelationVerificationClient,
    RelationVerificationClient,
)

from .corporate_entity_ingestion import get_or_create_corporate_entity
from .keyman_ingestion import _load_corporate_entity_candidates
from .organization_name_resolution_ingestion import (
    load_corroborated_organization_name_aliases,
)
from .knowledge_graph import persist_edges_for_post
from .team_ingestion import upsert_team


SUMMARY_SOURCE_BODY_MISSING = (
    "Post summary is unavailable: the source post body is empty. "
    "Re-import the source record with its body before requesting a summary."
)


def require_summary_source_body(body: str | None) -> str:
    """Reject summary derivation when the evidence body was not imported."""
    if not isinstance(body, str) or not body.strip():
        raise ValueError(SUMMARY_SOURCE_BODY_MISSING)
    return body


async def fetch_persisted_summary(
    conn: asyncpg.Connection,
    post_id: str,
    *,
    allow_stale: bool = False,
) -> dict[str, Any] | None:
    """Return the stored summary payload, or None when none is usable.

    ``catalog_node_id`` comes from the role row's catalog foreign keys
    (ADR 0019 / 0027). This function does not join ``corporate_entity``
    by ``entity_name``. Person chips read ``cataloged_person_id``. A stale
    row is returned only when ``allow_stale`` is explicit so a caller can
    preserve buyer continuity without presenting old semantics as current.
    """
    header = await conn.fetchrow(
        "select korean_summary, summary_contract_version "
        "from post_summary_result where post_id = $1",
        post_id,
    )
    if header is None:
        return None
    summary_contract_version = header["summary_contract_version"]
    if summary_contract_version != POST_SUMMARY_CONTRACT_VERSION and not allow_stale:
        return None
    events = await conn.fetch(
        """
        select event.event_text, event.project_key, mention.project_name
          from post_summary_event event
          left join post_project_mention mention
            on mention.post_id = event.post_id
           and mention.project_key = event.project_key
         where event.post_id = $1
         order by event.event_ordinal
        """,
        post_id,
    )
    roles = await conn.fetch(
        """
        select role.actor_name, role.responsibility, role.actor_type_code,
               role.affiliated_organization_name,
               role.cataloged_team_id,
               role.cataloged_corporate_entity_id,
               role.cataloged_person_id
          from post_summary_role role
         where role.post_id = $1
         order by role.actor_name
        """,
        post_id,
    )
    projects = await conn.fetch(
        """
        select project_key, project_name, evidence_text, confidence, ontology_iri,
               extraction_method
          from post_project_mention
         where post_id = $1
         order by project_name, project_key
        """,
        post_id,
    )
    actions = await conn.fetch(
        """
        select action.action_text, action.requester_actor_name,
               action.processor_actor_name, action.evidence_text,
               mention.project_name
          from post_summary_action action
          left join post_project_mention mention
            on mention.post_id = action.post_id
           and mention.project_key = action.project_key
         where action.post_id = $1
         order by action.action_ordinal
        """,
        post_id,
    )
    payload_roles: list[dict[str, Any]] = []
    for row in roles:
        catalog_node_id = None
        catalog_node_type_code = None
        if row["cataloged_team_id"] is not None:
            catalog_node_id = str(row["cataloged_team_id"])
            catalog_node_type_code = NODE_TEAM
        elif row["cataloged_corporate_entity_id"] is not None:
            catalog_node_id = str(row["cataloged_corporate_entity_id"])
            catalog_node_type_code = NODE_CORPORATE_ENTITY
        elif row["cataloged_person_id"] is not None:
            catalog_node_id = str(row["cataloged_person_id"])
            catalog_node_type_code = NODE_PERSON
        payload_roles.append(
            {
                "actor_name": row["actor_name"],
                "responsibility": row["responsibility"],
                "actor_type_code": row["actor_type_code"],
                "affiliated_organization_name": row["affiliated_organization_name"],
                "catalog_node_id": catalog_node_id,
                "catalog_node_type_code": catalog_node_type_code,
                **ontology_annotations(row["actor_type_code"]),
            }
        )
    return {
        "post_id": post_id,
        "korean_summary": header["korean_summary"],
        "summary_status": (
            "current"
            if summary_contract_version == POST_SUMMARY_CONTRACT_VERSION
            else "stale"
        ),
        "summary_contract_version": summary_contract_version,
        "key_events": [row["event_text"] for row in events],
        "key_event_details": [
            {
                "event_text": row["event_text"],
                "project_name": row.get("project_name"),
            }
            for row in events
        ],
        "roles_and_responsibilities": payload_roles,
        "major_event_actions": [
            {
                "action_text": row["action_text"],
                "requester_actor_name": row["requester_actor_name"],
                "processor_actor_name": row["processor_actor_name"],
                "evidence_text": row["evidence_text"],
                "project_name": row["project_name"],
            }
            for row in actions
        ],
        "project_mentions": [
            {
                "project_key": row["project_key"],
                "project_name": row["project_name"],
                "evidence": row["evidence_text"],
                "confidence": float(row["confidence"]),
                "ontology_iri": row["ontology_iri"],
                "extraction_method": row["extraction_method"],
            }
            for row in projects
        ],
    }


async def persist_post_summary(
    conn: asyncpg.Connection,
    post_id: str,
    summary: PostSummary,
    *,
    post_body: str | None = None,
    hierarchy_inference_client: CorporateHierarchyInferenceClient | None = None,
    verification_client: RelationVerificationClient | None = None,
) -> dict[str, Any]:
    """Replace the stored summary for ``post_id`` and return the public payload.

    ``post_body`` is the context an organization-actor hierarchy proposal
    is inferred from (ADR 0010); it falls back to the summary's own Korean
    text when not given.  The pluggable clients default to unavailable Null
    clients, so an organization actor then only resolves against an existing
    ``corporate_entity``.

    Organization inference, verification, and any lock-protected catalog
    creation complete before the atomic summary transaction.  The catalog is
    an idempotent shared identity registry; keeping that enrichment separate
    prevents network latency and ``pg_advisory_xact_lock`` from extending the
    summary replacement transaction while all post-owned rows still commit or
    roll back together.
    """
    if post_body is not None:
        require_summary_source_body(post_body)

    hierarchy_inference_client = (
        hierarchy_inference_client or NullCorporateHierarchyInferenceClient()
    )
    verification_client = verification_client or NullRelationVerificationClient()

    context_text = post_body if post_body is not None else summary.korean_summary
    aliases = (
        await load_corroborated_organization_name_aliases(conn)
        if summary.roles_and_responsibilities
        else []
    )
    candidates = (
        await _load_corporate_entity_candidates(conn)
        if summary.roles_and_responsibilities
        else []
    )
    resolved_organization_ids: dict[int, str] = {}
    for role_index, role in enumerate(summary.roles_and_responsibilities):
        if role.actor_type_code != ACTOR_TYPE_ORGANIZATION:
            continue
        corporate_entity_id = await get_or_create_corporate_entity(
            conn,
            role.actor_name,
            context_text,
            hierarchy_inference_client,
            verification_client,
            candidates,
            aliases=aliases,
        )
        if corporate_entity_id is not None:
            resolved_organization_ids[role_index] = corporate_entity_id

    async with conn.transaction():
        await _replace_summary_projection(
            conn,
            post_id,
            summary,
            candidates,
            resolved_organization_ids,
        )

    payload = await fetch_persisted_summary(conn, post_id)
    if payload is None:
        raise RuntimeError("persist_post_summary wrote no row")
    return payload


async def _resolve_existing_cataloged_person_id(
    conn: asyncpg.Connection, person_name: str
) -> str | None:
    """Return the earliest existing catalog person id for ``person_name``.

    Lookup orders by ``created_at``, then ``person_id``. This function
    does not insert a ``cataloged_person`` row (ADR 0009). A missing
    catalog row stays unbound rather than inventing a person.
    """
    person_row = await conn.fetchrow(
        "select person_id from cataloged_person "
        "where person_name = $1 "
        "order by created_at, person_id limit 1",
        person_name,
    )
    if person_row is None:
        return None
    return str(person_row["person_id"])


async def _replace_summary_projection(
    conn: asyncpg.Connection,
    post_id: str,
    summary: PostSummary,
    candidates: list[Any],
    resolved_organization_ids: dict[int, str],
) -> None:
    """Write one atomic replacement using pre-resolved shared identities."""
    # Summary replacement owns only R&R projections. Keyman mentions remain
    # independent and are combined only by the graph read/derivation view.
    # Product-to-project evidence belongs to the exact normalized project
    # target set. Invalidate it before replacing those targets so a deleted
    # relation cannot be mistaken for an already-complete analysis.
    await conn.execute("delete from post_product_analysis where post_id = $1", post_id)
    await conn.execute(
        "delete from post_summary_person_mention where post_id = $1",
        post_id,
    )
    await conn.execute("delete from post_team_mention where post_id = $1", post_id)
    await conn.execute("delete from post_organization_mention where post_id = $1", post_id)
    await conn.execute("delete from post_summary_five_w1h where post_id = $1", post_id)
    await conn.execute("delete from post_summary_action where post_id = $1", post_id)
    await conn.execute("delete from post_summary_result where post_id = $1", post_id)
    await conn.execute("delete from post_project_mention where post_id = $1", post_id)
    await conn.execute(
        "insert into post_summary_result "
        "(post_id, korean_summary, summary_contract_version) values ($1, $2, $3)",
        post_id,
        summary.korean_summary,
        POST_SUMMARY_CONTRACT_VERSION,
    )
    for project in summary.project_mentions:
        project_key = normalize_project_key(project.canonical_name)
        if not project_key:
            continue
        await conn.execute(
            """
            insert into post_project_mention
                (post_id, project_key, project_name, evidence_text, confidence,
                 ontology_iri, extraction_method)
            values ($1, $2, $3, $4, $5, $6, 'contextual_orchestrator_semantic')
            on conflict (post_id, project_key) do update set
                project_name = excluded.project_name,
                evidence_text = excluded.evidence_text,
                confidence = excluded.confidence,
                ontology_iri = excluded.ontology_iri,
                extraction_method = excluded.extraction_method
            """,
            post_id,
            project_key,
            project.project_name,
            project.evidence,
            project.confidence,
            str(LW.Project),
        )
    event_details = summary.key_event_details or tuple(
        KeyEvent(event_text=event_text) for event_text in summary.key_events
    )
    project_keys = {
        normalize_project_key(project.canonical_name)
        for project in summary.project_mentions
        if normalize_project_key(project.canonical_name)
    }
    for ordinal, event in enumerate(event_details):
        normalized_event_project_key = (
            normalize_project_key(event.project_key) if event.project_key else None
        )
        project_key = (
            normalized_event_project_key
            if normalized_event_project_key in project_keys
            else None
        )
        await conn.execute(
            "insert into post_summary_event (post_id, event_ordinal, event_text, project_key) "
            "values ($1, $2, $3, $4)",
            post_id,
            ordinal,
            event.event_text,
            project_key,
        )
    for ordinal, claim in enumerate(summary.five_w1h_evidence):
        await conn.execute(
            "insert into post_summary_five_w1h "
            "(post_id, slot_code, value_ordinal, value_text, evidence_text) "
            "values ($1, $2, $3, $4, $5)",
            post_id,
            claim.slot_code,
            ordinal,
            claim.value_text,
            claim.evidence_text,
        )
    # ADR 0009 / 0019 / 0027: resolve catalog identity before writing
    # the role row so fetch never reconstructs it by a non-unique name.
    for role_index, role in enumerate(summary.roles_and_responsibilities):
        cataloged_team_id = None
        cataloged_corporate_entity_id = None
        cataloged_person_id = None
        if role.actor_type_code == ACTOR_TYPE_TEAM:
            cataloged_team_id = await upsert_team(
                conn,
                role.actor_name,
                role.affiliated_organization_name,
                candidates,
            )
        elif role.actor_type_code == ACTOR_TYPE_ORGANIZATION:
            cataloged_corporate_entity_id = resolved_organization_ids.get(
                role_index
            )
        elif role.actor_type_code == ACTOR_TYPE_PERSON:
            cataloged_person_id = await _resolve_existing_cataloged_person_id(
                conn,
                role.actor_name,
            )
        await conn.execute(
            "insert into post_summary_role "
            "(post_id, actor_name, responsibility, actor_type_code, "
            "affiliated_organization_name, cataloged_team_id, "
            "cataloged_corporate_entity_id, cataloged_person_id) values "
            "($1, $2, $3, $4, $5, $6, $7, $8)",
            post_id,
            role.actor_name,
            role.responsibility,
            role.actor_type_code,
            role.affiliated_organization_name,
            cataloged_team_id,
            cataloged_corporate_entity_id,
            cataloged_person_id,
        )
        if cataloged_team_id is not None:
            await conn.execute(
                "insert into post_team_mention (post_id, team_id) values ($1, $2) "
                "on conflict do nothing",
                post_id,
                cataloged_team_id,
            )
        elif cataloged_corporate_entity_id is not None:
            await conn.execute(
                "insert into post_organization_mention "
                "(post_id, corporate_entity_id) values ($1, $2) "
                "on conflict do nothing",
                post_id,
                cataloged_corporate_entity_id,
            )
        elif cataloged_person_id is not None:
            await conn.execute(
                "insert into post_summary_person_mention (post_id, person_id) "
                "values ($1, $2) on conflict do nothing",
                post_id,
                cataloged_person_id,
            )
    role_names = {role.actor_name for role in summary.roles_and_responsibilities}
    project_keys = {
        normalize_project_key(project.canonical_name)
        for project in summary.project_mentions
        if normalize_project_key(project.canonical_name)
    }
    for ordinal, action in enumerate(summary.major_event_actions):
        actor_names = (action.requester_actor_name, action.processor_actor_name)
        if any(name is not None and name not in role_names for name in actor_names):
            continue
        normalized_action_project_key = (
            normalize_project_key(action.project_key) if action.project_key else None
        )
        project_key = (
            normalized_action_project_key
            if normalized_action_project_key in project_keys
            else None
        )
        await conn.execute(
            """
            insert into post_summary_action
                (post_id, action_ordinal, action_text, requester_actor_name,
                 processor_actor_name, evidence_text, project_key)
            values ($1, $2, $3, $4, $5, $6, $7)
            """,
            post_id,
            ordinal,
            action.action_text,
            action.requester_actor_name,
            action.processor_actor_name,
            action.evidence_text,
            project_key,
        )
    await persist_edges_for_post(conn, post_id)


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
    """Create one compact synthetic fixture summary."""
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
