"""Load ABAC-visible posts for the RankWeave ranking port.

A hidden post is omitted from every channel. This module never invents
a fused score or a theta.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Callable, Mapping

from backend.app.post_eligibility import source_post_scope_sql

if TYPE_CHECKING:
    import asyncpg

__all__ = [
    "load_ranking_context_choices",
    "load_selected_ranking_rows",
    "load_visible_ranking_posts",
]


async def load_ranking_context_choices(
    conn: "asyncpg.Connection",
    corporate_entity_ids: Sequence[str],
    process_unit_ids: Sequence[str],
) -> list[dict[str, Any]]:
    """List persisted topic/context choices supported by an authorized post."""
    rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        f"""
        select distinct membership.topic_model_run_id::text,
               influence.topic_influence_run_id::text as influence_run_id,
               influence.topic_index, membership.dimension_code as dimension,
               membership.context_id as context, definition.context_label,
               post.visibility_code, post.corporate_entity_id, post.process_unit_id
          from topic_post_context_influence influence
          join topic_context_membership membership
            on membership.topic_model_run_id = influence.topic_model_run_id
           and membership.topic_context_membership_id = influence.topic_context_membership_id
          join topic_context_definition definition
            on definition.topic_model_run_id = membership.topic_model_run_id
           and definition.dimension_code = membership.dimension_code
           and definition.context_id = membership.context_id
         join source_post post on post.post_id = membership.source_post_id
         where influence.diagnostic_status_code = 'accepted'
           and {source_post_scope_sql('post')}
         order by membership.topic_model_run_id::text,
                  influence.topic_influence_run_id::text, influence.topic_index,
                  membership.dimension_code, membership.context_id
        """,
        list(corporate_entity_ids),
        list(process_unit_ids),
    )
    keys = (
        "topic_model_run_id", "influence_run_id", "topic_index",
        "dimension", "context", "context_label",
    )
    return [{key: row[key] for key in keys} for row in rows]


async def load_selected_ranking_rows(
    conn: "asyncpg.Connection",
    selection: Mapping[str, Any],
    corporate_entity_ids: Sequence[str],
    process_unit_ids: Sequence[str],
) -> list[dict[str, Any]]:
    """Load one exact accepted influence population before RankWeave fusion."""
    rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        f"""
        select post.post_id::text, post.post_title,
               coalesce(post.event_occurred_at, post.created_at) as event_time,
               post.visibility_code, post.corporate_entity_id, post.process_unit_id,
               influence.influence_value, influence.uncertainty_method_code,
               influence.uncertainty_lower_value, influence.uncertainty_upper_value,
               membership.evidence_sha256,
               membership.provenance_assertion_id::text as provenance_assertion_id
          from topic_post_context_influence influence
          join topic_context_membership membership
            on membership.topic_model_run_id = influence.topic_model_run_id
           and membership.topic_context_membership_id = influence.topic_context_membership_id
          join source_post post on post.post_id = membership.source_post_id
         where influence.topic_model_run_id = $3::uuid
           and influence.topic_influence_run_id = $4::uuid
           and influence.topic_index = $5
           and membership.dimension_code = $6
           and membership.context_id = $7
           and influence.diagnostic_status_code = 'accepted'
           and {source_post_scope_sql('post')}
        """,
        list(corporate_entity_ids), list(process_unit_ids),
        selection["topic_model_run_id"], selection["influence_run_id"],
        selection["topic_index"], selection["dimension"], selection["context"],
    )
    return [dict(row) for row in rows]


async def load_visible_ranking_posts(
    conn: "asyncpg.Connection",
    can_see_post: Callable[[Mapping[str, Any]], bool],
) -> list[dict[str, Any]]:
    """Read ``source_post`` rows the buyer may rank."""
    posts = await conn.fetch(
        "select post_id, post_title, created_at, visibility_code, "
        "corporate_entity_id, process_unit_id from source_post"
    )
    return [dict(row) for row in posts if can_see_post(row)]
