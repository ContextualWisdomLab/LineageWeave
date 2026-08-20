"""Authorized PostgreSQL read model for project lifecycle history.

Every event, relation, and responsibility assignment is backed by a source
post that passes the same publication and corporate-scope boundary as the
Buyer surface. Relations remain temporal or associative links; this module
never promotes them to causal facts.
"""

from __future__ import annotations

from typing import Any, Collection
import asyncpg

from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave.project_history import (
    ResponsibilityInterval,
    event_ontology_iri,
    responsibility_handover_gaps,
    serialize_rfc3339,
)

DEFAULT_PROJECT_HISTORY_LIMIT = 200
MAX_PROJECT_HISTORY_LIMIT = 500
MAX_PROJECT_HISTORY_RELATIONS = 2_000


def _bounded_limit(limit: int) -> int:
    """Clamp caller-provided event limits to the public contract."""

    return max(1, min(int(limit), MAX_PROJECT_HISTORY_LIMIT))


async def fetch_project_history(
    conn: asyncpg.Connection,
    project_key: str,
    corporate_entity_ids: Collection[str],
    *,
    limit: int = DEFAULT_PROJECT_HISTORY_LIMIT,
) -> dict[str, Any]:
    """Return one authorized, deterministic project lifecycle timeline.

    Hidden evidence removes its event or assignment. A relation is returned
    only when both endpoints and its own evidence post remain visible. Gaps are
    calculated from the union of the remaining assignment intervals, so hidden
    assignments cannot leak through derived dates.
    """

    normalized_key = project_key.strip()
    if not normalized_key:
        raise ValueError("project_key must not be empty")

    bounded = _bounded_limit(limit)
    relation_limit = min(MAX_PROJECT_HISTORY_RELATIONS, bounded * 8)
    scopes = sorted({str(value) for value in corporate_entity_ids})
    event_eligibility = SOURCE_POST_ELIGIBILITY_SQL.format(alias="post")

    event_rows = list(
        await conn.fetch(
            f"""
            select event.project_history_event_id,
                   event.project_key,
                   project.project_name,
                   event.event_type_code,
                   coalesce(event_type.lookup_label, event.event_type_code)
                       as event_type_label,
                   event.event_title,
                   event.event_start_at,
                   event.event_end_at,
                   event.evidence_post_id,
                   post.post_title as evidence_post_title
              from project_history_event event
              join project_history_project project
                on project.project_key = event.project_key
              join source_post post on post.post_id = event.evidence_post_id
              left join common_lookup_value event_type
                on event_type.lookup_category = 'project_event_type'
               and event_type.lookup_code = event.event_type_code
             where event.project_key = $1
               and (post.visibility_code = 'public'
                    or post.corporate_entity_id::text = any($2::text[]))
               and {event_eligibility}
             order by event.event_start_at, event.project_history_event_id
             limit $3
            """,
            normalized_key,
            scopes,
            bounded + 1,
        )
    )
    events_truncated = len(event_rows) > bounded
    visible_event_rows = event_rows[:bounded]
    visible_event_ids = [row["project_history_event_id"] for row in visible_event_rows]

    relation_rows: list[asyncpg.Record] = []
    relations_truncated = False
    if visible_event_ids:
        relation_rows = list(
            await conn.fetch(
                f"""
                select relation.source_project_history_event_id,
                       relation.target_project_history_event_id,
                       relation.relation_type_code,
                       coalesce(relation_type.lookup_label, relation.relation_type_code)
                           as relation_type_label,
                       relation.evidence_post_id,
                       evidence_post.post_title as evidence_post_title,
                       relation.relation_confidence
                  from project_event_relation relation
                  join source_post evidence_post
                    on evidence_post.post_id = relation.evidence_post_id
                  left join common_lookup_value relation_type
                    on relation_type.lookup_category = 'project_relation_type'
                   and relation_type.lookup_code = relation.relation_type_code
                 where relation.source_project_history_event_id = any($1::uuid[])
                   and relation.target_project_history_event_id = any($1::uuid[])
                   and (evidence_post.visibility_code = 'public'
                        or evidence_post.corporate_entity_id::text = any($2::text[]))
                   and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='evidence_post')}
                 order by relation.source_project_history_event_id,
                          relation.target_project_history_event_id,
                          relation.relation_type_code
                 limit $3
                """,
                visible_event_ids,
                scopes,
                relation_limit + 1,
            )
        )
        relations_truncated = len(relation_rows) > relation_limit
        relation_rows = relation_rows[:relation_limit]

    assignment_rows = list(
        await conn.fetch(
            f"""
            select assignment.project_responsibility_assignment_id,
                   assignment.project_key,
                   project.project_name,
                   assignment.cataloged_person_id,
                   person.person_name,
                   assignment.responsibility_role_code,
                   coalesce(role_type.lookup_label, assignment.responsibility_role_code)
                       as responsibility_role_label,
                   assignment.valid_from,
                   assignment.valid_to,
                   assignment.evidence_post_id,
                   evidence_post.post_title as evidence_post_title
              from project_responsibility_assignment assignment
              join project_history_project project
                on project.project_key = assignment.project_key
              join cataloged_person person
                on person.person_id = assignment.cataloged_person_id
              join source_post evidence_post
                on evidence_post.post_id = assignment.evidence_post_id
              left join common_lookup_value role_type
                on role_type.lookup_category = 'project_responsibility_role'
               and role_type.lookup_code = assignment.responsibility_role_code
             where assignment.project_key = $1
               and (evidence_post.visibility_code = 'public'
                    or evidence_post.corporate_entity_id::text = any($2::text[]))
               and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='evidence_post')}
             order by assignment.valid_from,
                      assignment.project_responsibility_assignment_id
             limit $3
            """,
            normalized_key,
            scopes,
            bounded + 1,
        )
    )
    assignments_truncated = len(assignment_rows) > bounded
    assignment_rows = assignment_rows[:bounded]

    intervals = [
        ResponsibilityInterval(
            assignment_id=str(row["project_responsibility_assignment_id"]),
            valid_from=row["valid_from"],
            valid_to=row["valid_to"],
        )
        for row in assignment_rows
    ]
    gaps = responsibility_handover_gaps(intervals)

    events = [
        {
            "project_history_event_id": str(row["project_history_event_id"]),
            "event_type_code": row["event_type_code"],
            "event_type_label": row["event_type_label"],
            "event_title": row["event_title"],
            "occurred_at": serialize_rfc3339(
                row["event_start_at"], field="event_start_at"
            ),
            "ended_at": serialize_rfc3339(
                row["event_end_at"], field="event_end_at"
            ),
            "evidence_post_id": str(row["evidence_post_id"]),
            "evidence_post_title": row["evidence_post_title"],
            "ontology_iri": event_ontology_iri(row["event_type_code"]),
            "evidence_count": 1,
        }
        for row in visible_event_rows
    ]
    relations = [
        {
            "source_project_history_event_id": str(
                row["source_project_history_event_id"]
            ),
            "target_project_history_event_id": str(
                row["target_project_history_event_id"]
            ),
            "relation_type_code": row["relation_type_code"],
            "relation_type_label": row["relation_type_label"],
            "evidence_post_id": str(row["evidence_post_id"]),
            "evidence_post_title": row["evidence_post_title"],
            "relation_confidence": (
                float(row["relation_confidence"])
                if row["relation_confidence"] is not None
                else None
            ),
            "causal": False,
        }
        for row in relation_rows
    ]
    assignments = [
        {
            "project_responsibility_assignment_id": str(
                row["project_responsibility_assignment_id"]
            ),
            "cataloged_person_id": str(row["cataloged_person_id"]),
            "person_name": row["person_name"],
            "responsibility_role_code": row["responsibility_role_code"],
            "responsibility_role_label": row["responsibility_role_label"],
            "valid_from": serialize_rfc3339(row["valid_from"], field="valid_from"),
            "valid_to": serialize_rfc3339(row["valid_to"], field="valid_to"),
            "evidence_post_id": str(row["evidence_post_id"]),
            "evidence_post_title": row["evidence_post_title"],
        }
        for row in assignment_rows
    ]
    handover_gaps = [
        {
            "previous_assignment_id": gap.previous_assignment_id,
            "next_assignment_id": gap.next_assignment_id,
            "gap_start": serialize_rfc3339(gap.gap_start, field="gap_start"),
            "gap_end": serialize_rfc3339(gap.gap_end, field="gap_end"),
            "gap_days": gap.gap_seconds / 86_400.0,
            "gap_basis": "visible_assignment_evidence",
        }
        for gap in gaps
    ]

    visible_name_rows = visible_event_rows or assignment_rows
    project_name = (
        str(visible_name_rows[0]["project_name"])
        if visible_name_rows
        else normalized_key
    )
    return {
        "project_key": normalized_key,
        "project_name": project_name,
        "events": events,
        "relations": relations,
        "responsibility_assignments": assignments,
        "handover_gaps": handover_gaps,
        "truncated": (
            events_truncated or relations_truncated or assignments_truncated
        ),
        "evidence_boundary": "authorized_source_posts_only",
    }
