"""Nominate Global Ask posts from persisted semantic and KG evidence."""

from __future__ import annotations

from datetime import date

import asyncpg

from .post_eligibility import SOURCE_POST_ELIGIBILITY_SQL


async def semantic_candidate_post_ids(
    conn: asyncpg.Connection,
    question: str,
    *,
    maximum_candidates: int,
    authorized_corporate_entity_ids: list[str],
    authorized_process_unit_ids: list[str],
    date_from: date | None,
    date_to: date | None,
) -> list[str]:
    """Return bounded post IDs whose persisted semantic evidence matches.

    Nomination grants no access and returns no evidence text. The caller must
    apply the ordinary source-post RBAC/ABAC, eligibility, and time boundary
    before reading any nominated row.
    """

    if maximum_candidates <= 0 or not question.strip():
        return []
    rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        f"""
        with search_query as (
            select websearch_to_tsquery('simple', $1) as value
        ), candidate_post as (
            select mention.post_id, post.created_at
              from post_project_mention mention
              join source_post post on post.post_id = mention.post_id
             cross join search_query
             where to_tsvector(
                       'simple',
                       coalesce(mention.project_key, '') || ' ' ||
                       coalesce(mention.project_name, '') || ' ' ||
                       coalesce(mention.evidence_text, '') || ' ' ||
                       coalesce(mention.ontology_iri, '')
                   ) @@ search_query.value
            union all
            select role.post_id, post.created_at
              from post_summary_role role
              join source_post post on post.post_id = role.post_id
             cross join search_query
             where to_tsvector(
                       'simple',
                       coalesce(role.actor_name, '') || ' ' ||
                       coalesce(role.responsibility, '') || ' ' ||
                       coalesce(role.affiliated_organization_name, '')
                   ) @@ search_query.value
            union all
            select mention.post_id, post.created_at
              from post_person_mention mention
              join cataloged_person person on person.person_id = mention.person_id
              join source_post post on post.post_id = mention.post_id
             cross join search_query
             where to_tsvector(
                       'simple', coalesce(person.person_name, '') || ' ' ||
                                 coalesce(person.last_known_job_title, '')
                   ) @@ search_query.value
            union all
            select mention.post_id, post.created_at
              from post_person_mention mention
              join source_post post on post.post_id = mention.post_id
              cross join search_query
             where to_tsvector('simple', coalesce(mention.mention_context, ''))
                   @@ search_query.value
            union all
            select mention.post_id, post.created_at
              from post_organization_mention mention
              join corporate_entity entity
                on entity.corporate_entity_id = mention.corporate_entity_id
              join source_post post on post.post_id = mention.post_id
              cross join search_query
             where to_tsvector('simple', entity.entity_name) @@ search_query.value
            union all
            select mention.post_id, post.created_at
              from post_team_mention mention
              join cataloged_team team on team.team_id = mention.team_id
              join source_post post on post.post_id = mention.post_id
             cross join search_query
             where to_tsvector(
                       'simple',
                       coalesce(team.team_name, '') || ' ' ||
                       coalesce(team.affiliated_organization_name, '')
                   ) @@ search_query.value
            union all
            select evidence.evidence_post_id, post.created_at
              from knowledge_graph_edge edge
              join knowledge_graph_edge_evidence evidence
                on evidence.knowledge_graph_edge_id = edge.knowledge_graph_edge_id
              join source_post post on post.post_id = evidence.evidence_post_id
             cross join search_query
             where to_tsvector(
                       'simple',
                       replace(coalesce(edge.edge_type_code, '') || ' ' ||
                               coalesce(edge.source_node_type_code, '') || ' ' ||
                               coalesce(edge.target_node_type_code, ''), '_', ' ')
                   ) @@ search_query.value
        )
        select candidate.post_id::text as post_id
          from candidate_post candidate
          join source_post post on post.post_id = candidate.post_id
         where (post.visibility_code = 'public'
            or (post.corporate_entity_id::text = any($3::text[])
                and (cardinality($4::text[]) = 0
                     or post.process_unit_id::text = any($4::text[]))))
           and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}
           and ($5::date is null or (coalesce(post.event_occurred_at, post.created_at) at time zone 'Asia/Seoul')::date >= $5)
           and ($6::date is null or (coalesce(post.event_occurred_at, post.created_at) at time zone 'Asia/Seoul')::date <= $6)
         group by candidate.post_id
         order by max(candidate.created_at) desc, candidate.post_id desc
         limit $2
        """,
        question,
        maximum_candidates,
        authorized_corporate_entity_ids,
        authorized_process_unit_ids,
        date_from,
        date_to,
    )
    return [str(row["post_id"]) for row in rows]
