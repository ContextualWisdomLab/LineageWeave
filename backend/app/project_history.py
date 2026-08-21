"""ABAC-safe PostgreSQL projections for Buyer project histories."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave.project_history import (
    PROJECT_HISTORY_CONTRACT_VERSION,
    PROJECT_HISTORY_TIME_BASIS,
    _as_utc,
    build_project_history_projection,
    normalize_project_key,
)

PROJECT_HISTORY_DEFAULT_LIMIT = 64
PROJECT_HISTORY_MAXIMUM_LIMIT = 128
PROJECT_INDEX_DEFAULT_LIMIT = 100
PROJECT_INDEX_MAXIMUM_LIMIT = 200
PROJECT_INDEX_MINIMUM_SOURCE_POST_LIMIT = 1024
PROJECT_INDEX_STATEMENT_TIMEOUT_MILLISECONDS = 5000


class ProjectHistoryConnection(Protocol):
    """Minimal asynchronous query port required by this repository."""

    async def fetch(self, query: str, *args: object) -> Sequence[Mapping[str, Any]]:
        """Execute a bounded read query and return mapping-like rows."""

        raise NotImplementedError


_ELIGIBILITY = SOURCE_POST_ELIGIBILITY_SQL.format(alias="post")
_SOURCE_CODE = "nullif(btrim(post.source_project_code), '')"
_SOURCE_NAME = "nullif(btrim(post.source_project_name), '')"
_MENTION_KEY = "nullif(btrim(mention.project_key), '')"
_MENTION_NAME = "nullif(btrim(mention.project_name), '')"
_PROJECT_MATCH = f"""
(
    (
        {_SOURCE_CODE} is not null
        and lower(normalize({_SOURCE_CODE}, NFKC)) = $1
    )
    or (
        {_SOURCE_CODE} is null
        and {_SOURCE_NAME} is not null
        and lower(normalize({_SOURCE_NAME}, NFKC)) = $1
    )
    or exists (
        select 1
          from post_project_mention mention
         where mention.post_id = post.post_id
           and (
                (
                    {_MENTION_KEY} is not null
                    and lower(normalize({_MENTION_KEY}, NFKC)) = $1
                )
                or (
                    {_MENTION_KEY} is null
                    and {_MENTION_NAME} is not null
                    and lower(normalize({_MENTION_NAME}, NFKC)) = $1
                )
           )
    )
)
"""
_EVENT_SQL = f"""
select post.post_id,
       post.post_title,
       post.created_at,
       post.voc_type_code,
       post.source_stage_code,
       post.source_detail_state_code
  from source_post post
 where (post.visibility_code = 'public'
    or post.corporate_entity_id::text = any($2::text[]))
   and {_ELIGIBILITY}
   and post.created_at <= $3
   and {_PROJECT_MATCH}
 order by post.created_at, post.post_id
 limit $4
"""
_FOCUS_SQL = f"""
select post.post_id,
       post.post_title,
       post.created_at,
       post.voc_type_code,
       post.source_stage_code,
       post.source_detail_state_code
  from source_post post
 where (post.visibility_code = 'public'
    or post.corporate_entity_id::text = any($2::text[]))
   and {_ELIGIBILITY}
   and post.created_at <= $3
   and post.post_id = $4::uuid
   and {_PROJECT_MATCH}
 limit 1
"""
_MATCH_SQL = f"""
select post.post_id,
       'source_project_code'::text as match_kind_code,
       {_SOURCE_CODE} as identity_key,
       {_SOURCE_CODE} as matched_value,
       null::numeric as confidence,
       null::text as ontology_iri,
       'source_post.source_project_code'::text as provenance
  from source_post post
 where post.post_id = any($1::uuid[])
   and {_SOURCE_CODE} is not null
   and lower(normalize({_SOURCE_CODE}, NFKC)) = $2
union all
select post.post_id,
       'source_project_name'::text,
       coalesce({_SOURCE_CODE}, {_SOURCE_NAME}) as identity_key,
       {_SOURCE_NAME} as matched_value,
       null::numeric,
       null::text,
       'source_post.source_project_name'::text
  from source_post post
 where post.post_id = any($1::uuid[])
   and {_SOURCE_NAME} is not null
   and (
        ({_SOURCE_CODE} is not null and lower(normalize({_SOURCE_CODE}, NFKC)) = $2)
        or ({_SOURCE_CODE} is null and lower(normalize({_SOURCE_NAME}, NFKC)) = $2)
   )
union all
select mention.post_id,
       'semantic_project_key'::text,
       {_MENTION_KEY} as identity_key,
       {_MENTION_KEY} as matched_value,
       mention.confidence,
       mention.ontology_iri,
       'post_project_mention.project_key'::text
  from post_project_mention mention
 where mention.post_id = any($1::uuid[])
   and {_MENTION_KEY} is not null
   and lower(normalize({_MENTION_KEY}, NFKC)) = $2
union all
select mention.post_id,
       'semantic_project_name'::text,
       coalesce({_MENTION_KEY}, {_MENTION_NAME}) as identity_key,
       {_MENTION_NAME} as matched_value,
       mention.confidence,
       mention.ontology_iri,
       'post_project_mention.project_name'::text
  from post_project_mention mention
 where mention.post_id = any($1::uuid[])
   and {_MENTION_NAME} is not null
   and (
        ({_MENTION_KEY} is not null and lower(normalize({_MENTION_KEY}, NFKC)) = $2)
        or ({_MENTION_KEY} is null and lower(normalize({_MENTION_NAME}, NFKC)) = $2)
   )
order by post_id, match_kind_code, matched_value
"""
_ROLE_SQL = """
select post.post_id,
       coalesce(
           nullif(btrim(post.source_author_name), ''),
           nullif(btrim(post.source_author_code), '')
       ) as actor_name,
       'Source author'::text as responsibility,
       'prov_person'::text as actor_type_code,
       nullif(btrim(post.source_company_name), '') as affiliated_organization_name,
       null::uuid as cataloged_person_id,
       null::uuid as cataloged_team_id,
       null::uuid as cataloged_corporate_entity_id,
       'observed'::text as truth_status_code,
       'source_post.source_author'::text as provenance
  from source_post post
 where post.post_id = any($1::uuid[])
   and coalesce(
           nullif(btrim(post.source_author_name), ''),
           nullif(btrim(post.source_author_code), '')
       ) is not null
union all
select role.post_id,
       role.actor_name,
       role.responsibility,
       role.actor_type_code,
       role.affiliated_organization_name,
       role.cataloged_person_id,
       role.cataloged_team_id,
       role.cataloged_corporate_entity_id,
       'inferred'::text as truth_status_code,
       'post_summary_role'::text as provenance
  from post_summary_role role
 where role.post_id = any($1::uuid[])
order by post_id, truth_status_code, actor_type_code, actor_name, responsibility
"""
_EDGE_SQL = """
select edge.parent_post_id, edge.child_post_id, edge.fused_score
  from post_lineage_edge edge
 where edge.parent_post_id = any($1::uuid[])
   and edge.child_post_id = any($1::uuid[])
 order by edge.child_post_id, edge.parent_post_id
"""
_INDEX_SQL = f"""
with query_timeout as materialized (
    select set_config(
        'statement_timeout',
        '{PROJECT_INDEX_STATEMENT_TIMEOUT_MILLISECONDS}',
        true
    )
), recent_visible_post as materialized (
    select post.post_id,
           post.created_at,
           {_SOURCE_CODE} as source_project_code,
           {_SOURCE_NAME} as source_project_name
      from source_post post
      cross join query_timeout
     where (post.visibility_code = 'public'
        or post.corporate_entity_id::text = any($1::text[]))
       and {_ELIGIBILITY}
       and post.created_at <= $2
     order by post.created_at desc, post.post_id desc
     limit ($4 + 1)
), visible_post as materialized (
    select post_id, created_at, source_project_code, source_project_name
      from recent_visible_post
     order by created_at desc, post_id desc
     limit $4
), source_scan as (
    select count(*) > $4 as source_scan_truncated
      from recent_visible_post
), project_evidence as (
    select visible_post.post_id,
           visible_post.created_at,
           coalesce(visible_post.source_project_code, visible_post.source_project_name) as project_key,
           coalesce(visible_post.source_project_name, visible_post.source_project_code) as project_name,
           'observed'::text as truth_status_code,
           0::integer as truth_order
      from visible_post
     where coalesce(visible_post.source_project_code, visible_post.source_project_name) is not null
    union all
    select visible_post.post_id,
           visible_post.created_at,
           coalesce({_MENTION_KEY}, {_MENTION_NAME}) as project_key,
           coalesce({_MENTION_NAME}, {_MENTION_KEY}) as project_name,
           'inferred'::text as truth_status_code,
           1::integer as truth_order
      from visible_post
      join post_project_mention mention on mention.post_id = visible_post.post_id
     where coalesce({_MENTION_KEY}, {_MENTION_NAME}) is not null
), normalized_evidence as (
    select project_evidence.*,
           lower(normalize(project_evidence.project_key, NFKC)) as normalized_project_key
      from project_evidence
), ranked_evidence as (
    select normalized_evidence.*,
           row_number() over (
               partition by normalized_project_key
               order by truth_order, created_at, project_name, project_key, post_id
           ) as display_rank
      from normalized_evidence
), project_group as (
    select normalized_project_key,
           min(project_key) filter (where display_rank = 1) as project_key,
           min(project_name) filter (where display_rank = 1) as project_name,
           min(truth_status_code) filter (where display_rank = 1) as truth_status_code,
           count(distinct post_id) as event_count,
           max(created_at) as latest_event_at
      from ranked_evidence
     group by normalized_project_key
)
select normalized_project_key,
       project_key,
       project_name,
       truth_status_code,
       event_count,
       latest_event_at,
       source_scan.source_scan_truncated
  from project_group
  cross join source_scan
 order by latest_event_at desc, project_name, project_key, normalized_project_key
 limit $3
"""


class ProjectHistoryNotFound(LookupError):
    """No authorized project history matched the requested identity."""


def _require_aware_cutoff(knowledge_cutoff: datetime) -> None:
    """Require an offset-aware cutoff before any database read."""

    if knowledge_cutoff.tzinfo is None or knowledge_cutoff.utcoffset() is None:
        raise ValueError("knowledge_cutoff must be offset-aware")


def _canonical_focus_post_id(focus_post_id: str | None) -> str | None:
    """Validate and canonicalize an optional UUID before PostgreSQL sees it."""

    if focus_post_id is None:
        return None
    try:
        return str(UUID(focus_post_id))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError("focus_post_id must be a UUID") from exc


async def fetch_project_history_index(
    conn: ProjectHistoryConnection,
    *,
    knowledge_cutoff: datetime,
    corporate_entity_ids: Sequence[str],
    limit: int = PROJECT_INDEX_DEFAULT_LIMIT,
) -> dict[str, Any]:
    """Return a bounded exact-identity index from authorized source evidence."""

    if limit < 1 or limit > PROJECT_INDEX_MAXIMUM_LIMIT:
        raise ValueError("project index limit is outside the supported bound")
    _require_aware_cutoff(knowledge_cutoff)
    source_post_limit = max(
        PROJECT_INDEX_MINIMUM_SOURCE_POST_LIMIT,
        (limit + 1) * PROJECT_HISTORY_DEFAULT_LIMIT,
    )
    rows = list(
        await conn.fetch(
            _INDEX_SQL,
            list(corporate_entity_ids),
            knowledge_cutoff,
            limit + 1,
            source_post_limit,
        )
    )
    truncated = len(rows) > limit or any(
        bool(row["source_scan_truncated"]) for row in rows
    )
    projects = [
        {
            "normalized_project_key": str(row["normalized_project_key"]),
            "project_key": str(row["project_key"]),
            "project_name": str(row["project_name"]),
            "truth_status_code": str(row["truth_status_code"]),
            "event_count": int(row["event_count"]),
            "latest_event_at": _as_utc(row["latest_event_at"]),
        }
        for row in rows[:limit]
    ]
    return {
        "contract_version": PROJECT_HISTORY_CONTRACT_VERSION,
        "time_basis_code": PROJECT_HISTORY_TIME_BASIS,
        "knowledge_cutoff": _as_utc(knowledge_cutoff),
        "project_count": len(projects),
        "truncated": truncated,
        "projects": projects,
    }


async def fetch_project_history_projection(
    conn: ProjectHistoryConnection,
    *,
    project_key: str,
    focus_post_id: str | None,
    knowledge_cutoff: datetime,
    corporate_entity_ids: Sequence[str],
    limit: int = PROJECT_HISTORY_DEFAULT_LIMIT,
) -> dict[str, Any]:
    """Return a bounded project history from authorized PostgreSQL evidence.

    The query applies source eligibility, cutoff, exact identity, and ABAC
    before selecting event IDs. Child evidence is constrained to that visible
    ID set, so hidden rows cannot affect counts, transitions, or relation paths.
    An authorized focus event remains included when the earliest page truncates.
    """

    canonical_focus_id = _canonical_focus_post_id(focus_post_id)
    _require_aware_cutoff(knowledge_cutoff)
    if limit < 1 or limit > PROJECT_HISTORY_MAXIMUM_LIMIT:
        raise ValueError("project history limit is outside the supported bound")
    normalized_key = normalize_project_key(project_key)
    rows = list(
        await conn.fetch(
            _EVENT_SQL,
            normalized_key,
            list(corporate_entity_ids),
            knowledge_cutoff,
            limit + 1,
        )
    )
    truncated = len(rows) > limit
    event_rows = rows[:limit]
    if not event_rows:
        raise ProjectHistoryNotFound(project_key)
    visible_ids = [str(row["post_id"]) for row in event_rows]
    if canonical_focus_id is not None and canonical_focus_id not in set(visible_ids):
        focus_rows = list(
            await conn.fetch(
                _FOCUS_SQL,
                normalized_key,
                list(corporate_entity_ids),
                knowledge_cutoff,
                canonical_focus_id,
            )
        )
        if not focus_rows:
            raise ProjectHistoryNotFound(project_key)
        truncated = True
        event_rows = (event_rows[: limit - 1] if limit > 1 else []) + [focus_rows[0]]
        event_rows.sort(key=lambda row: (row["created_at"], str(row["post_id"])))
        visible_ids = [str(row["post_id"]) for row in event_rows]

    match_rows, role_rows, edge_rows = await _fetch_project_children(
        conn,
        visible_ids=visible_ids,
        normalized_key=normalized_key,
    )
    projection = build_project_history_projection(
        project_key=project_key,
        focus_event_id=canonical_focus_id,
        event_rows=event_rows,
        match_rows=match_rows,
        role_rows=role_rows,
        edge_rows=edge_rows,
        truncated=truncated,
    )
    projection["knowledge_cutoff"] = _as_utc(knowledge_cutoff)
    projection["evidence_boundary_code"] = "authorized_visible_source_posts"
    return projection


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
