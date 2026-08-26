"""ABAC-safe PostgreSQL projection for customer-facing project histories."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Protocol

from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave.project_history import build_project_history_projection, normalize_project_key

PROJECT_HISTORY_DEFAULT_LIMIT = 64
PROJECT_HISTORY_MAXIMUM_LIMIT = 128


class ProjectHistoryConnection(Protocol):
    """Minimal asynchronous query port required by this repository."""

    async def fetch(self, query: str, *args: object) -> Sequence[Mapping[str, Any]]:
        """Execute a bounded read query and return mapping-like rows."""

        pass


_ELIGIBILITY = SOURCE_POST_ELIGIBILITY_SQL.format(alias="post")
_PROJECT_MATCH = """
(
    lower(btrim(normalize(coalesce(post.source_project_code, ''), NFKC))) = $1
    or lower(btrim(normalize(coalesce(post.source_project_name, ''), NFKC))) = $1
    or exists (
        select 1
          from post_project_mention mention
         where mention.post_id = post.post_id
           and (
                lower(btrim(normalize(mention.project_key, NFKC))) = $1
                or lower(btrim(normalize(mention.project_name, NFKC))) = $1
           )
    )
)
"""
_EVENT_SQL = f"""
select post.post_id,
       post.post_title,
       post.created_at,
       post.event_occurred_at,
       post.voc_type_code,
       post.source_stage_code,
       post.source_detail_state_code
  from source_post post
 where (post.visibility_code = 'public'
    or (post.corporate_entity_id::text = any($2::text[])
        and (cardinality($3::text[]) = 0
             or post.process_unit_id::text = any($3::text[]))))
   and {_ELIGIBILITY}
   and post.created_at <= $4
   and {_PROJECT_MATCH}
 order by coalesce(post.event_occurred_at, post.created_at), post.created_at, post.post_id
 limit $5
"""
_FOCUS_SQL = f"""
select post.post_id,
       post.post_title,
       post.created_at,
       post.event_occurred_at,
       post.voc_type_code,
       post.source_stage_code,
       post.source_detail_state_code
  from source_post post
 where (post.visibility_code = 'public'
    or (post.corporate_entity_id::text = any($2::text[])
        and (cardinality($3::text[]) = 0
             or post.process_unit_id::text = any($3::text[]))))
   and {_ELIGIBILITY}
   and post.created_at <= $4
   and post.post_id = $5::uuid
   and {_PROJECT_MATCH}
 limit 1
"""
_MATCH_SQL = """
select post.post_id,
       'source_project_code'::text as match_kind_code,
       post.source_project_code as matched_value,
       null::numeric as confidence,
       null::text as ontology_iri,
       'source_post.source_project_code'::text as provenance
  from source_post post
 where post.post_id = any($1::uuid[])
   and lower(btrim(normalize(coalesce(post.source_project_code, ''), NFKC))) = $2
union all
select post.post_id,
       'source_project_name'::text,
       post.source_project_name,
       null::numeric,
       null::text,
       'source_post.source_project_name'::text
  from source_post post
 where post.post_id = any($1::uuid[])
   and lower(btrim(normalize(coalesce(post.source_project_name, ''), NFKC))) = $2
union all
select mention.post_id,
       'semantic_project_key'::text,
       mention.project_key,
       mention.confidence,
       mention.ontology_iri,
       'post_project_mention.project_key'::text
  from post_project_mention mention
 where mention.post_id = any($1::uuid[])
   and lower(btrim(normalize(mention.project_key, NFKC))) = $2
union all
select mention.post_id,
       'semantic_project_name'::text,
       mention.project_name,
       mention.confidence,
       mention.ontology_iri,
       'post_project_mention.project_name'::text
  from post_project_mention mention
 where mention.post_id = any($1::uuid[])
   and lower(btrim(normalize(mention.project_name, NFKC))) = $2
order by post_id, match_kind_code, matched_value
"""
_ROLE_SQL = """
select role.post_id,
       role.actor_name,
       role.responsibility,
       role.actor_type_code,
       role.affiliated_organization_name,
       role.cataloged_person_id,
       role.cataloged_team_id,
       role.cataloged_corporate_entity_id
  from post_summary_role role
 where role.post_id = any($1::uuid[])
 order by role.post_id, role.actor_type_code, role.actor_name, role.responsibility
"""
_EDGE_SQL = """
select edge.parent_post_id, edge.child_post_id, edge.fused_score
  from post_lineage_edge edge
 where edge.parent_post_id = any($1::uuid[])
   and edge.child_post_id = any($1::uuid[])
 order by edge.child_post_id, edge.parent_post_id
"""


class ProjectHistoryNotFound(LookupError):
    """No authorized project history matched the requested identity."""


async def fetch_project_history_projection(
    conn: ProjectHistoryConnection,
    *,
    project_key: str,
    focus_post_id: str | None,
    knowledge_cutoff: datetime,
    corporate_entity_ids: Sequence[str],
    process_unit_ids: Sequence[str],
    limit: int = PROJECT_HISTORY_DEFAULT_LIMIT,
) -> dict[str, Any]:
    """Return a bounded project history from authorized PostgreSQL evidence.

    The query applies source eligibility, cutoff, and ABAC before selecting
    event IDs. All subsequent match, role, and lineage reads are constrained to
    that visible ID set, so hidden rows cannot affect counts, transitions, or
    prior-history paths. An authorized focus event remains in a truncated
    projection even when it falls beyond the earliest page.
    """

    if limit < 1 or limit > PROJECT_HISTORY_MAXIMUM_LIMIT:
        raise ValueError("project history limit is outside the supported bound")
    normalized_key = normalize_project_key(project_key)
    rows = list(
        await conn.fetch(
            _EVENT_SQL,
            normalized_key,
            list(corporate_entity_ids),
            list(process_unit_ids),
            knowledge_cutoff,
            limit + 1,
        )
    )
    truncated = len(rows) > limit
    event_rows = rows[:limit]
    transition_suppressed_event_ids: set[str] = set()
    if not event_rows:
        raise ProjectHistoryNotFound(project_key)
    visible_ids = [str(row["post_id"]) for row in event_rows]
    if focus_post_id is not None and focus_post_id not in set(visible_ids):
        focus_rows = list(
            await conn.fetch(
                _FOCUS_SQL,
                normalized_key,
                list(corporate_entity_ids),
                list(process_unit_ids),
                knowledge_cutoff,
                focus_post_id,
            )
        )
        if not focus_rows:
            raise ProjectHistoryNotFound(project_key)
        truncated = True
        event_rows = (event_rows[: limit - 1] if limit > 1 else []) + [focus_rows[0]]
        transition_suppressed_event_ids.add(str(focus_rows[0]["post_id"]))
        event_rows.sort(
            key=lambda row: (
                row.get("event_occurred_at") or row["created_at"],
                row["created_at"],
                str(row["post_id"]),
            )
        )
        visible_ids = [str(row["post_id"]) for row in event_rows]

    match_rows, role_rows, edge_rows = await _fetch_project_children(
        conn,
        visible_ids=visible_ids,
        normalized_key=normalized_key,
    )
    return build_project_history_projection(
        project_key=project_key,
        focus_event_id=focus_post_id,
        event_rows=event_rows,
        match_rows=match_rows,
        role_rows=role_rows,
        edge_rows=edge_rows,
        truncated=truncated,
        transition_suppressed_event_ids=transition_suppressed_event_ids,
    )


async def _fetch_project_children(
    conn: ProjectHistoryConnection,
    *,
    visible_ids: Sequence[str],
    normalized_key: str,
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    """Fetch only child evidence whose endpoints are already authorized."""

    matches = list(await conn.fetch(_MATCH_SQL, list(visible_ids), normalized_key))
    roles = list(await conn.fetch(_ROLE_SQL, list(visible_ids)))
    edges = list(await conn.fetch(_EDGE_SQL, list(visible_ids)))
    return matches, roles, edges
