"""Authorized aggregate reads for source-preserving voice assertions."""

from __future__ import annotations

from typing import Any, Protocol


class _Connection(Protocol):
    async def fetchrow(self, query: str, *args: object) -> Any:
        """Fetch one aggregate row with bound parameters."""
        pass  # pragma: no cover - structural protocol declaration


async def load_voice_taxonomy_summary(
    conn: _Connection,
    *,
    authorized_corporate_entity_ids: tuple[str, ...],
    authorized_process_unit_ids: tuple[str, ...],
    date_from: Any = None,
    date_to: Any = None,
    corporate_entity_id: str | None = None,
    process_unit_id: str | None = None,
    team_id: str | None = None,
    person_id: str | None = None,
    product_catalog_id: str | None = None,
    project_key: str | None = None,
) -> dict[str, Any]:
    """Count overlapping voice memberships over one authorized denominator."""
    row = await conn.fetchrow(
        """
        with eligible as (
            select post.post_id
              from source_post post
             where post.corporate_entity_id = any($1::uuid[])
               and (post.visibility_code = 'public'
                    or post.process_unit_id is null
                    or post.process_unit_id = any($2::uuid[]))
               and ($3::timestamptz is null or coalesce(post.event_occurred_at, post.created_at) >= $3)
               and ($4::timestamptz is null or coalesce(post.event_occurred_at, post.created_at) < $4)
               and ($5::uuid is null or post.corporate_entity_id = $5)
               and ($6::uuid is null or post.process_unit_id = $6)
               and ($7::uuid is null or exists (
                    select 1 from post_team_mention team
                     where team.post_id = post.post_id and team.team_id = $7))
               and ($8::uuid is null or exists (
                    select 1 from post_person_mention person
                     where person.post_id = post.post_id and person.person_id = $8))
               and ($9::uuid is null or exists (
                    select 1 from post_product_mention product
                     where product.post_id = post.post_id and product.product_catalog_id = $9))
               and ($10::text is null or exists (
                    select 1 from post_project_mention project
                     where project.post_id = post.post_id and project.project_key = $10))
        ), memberships as (
            select assertion.post_id, assertion.assertion_status_code,
                   assertion.voice_concept_code
              from post_voice_classification_assertion assertion
              join eligible on eligible.post_id = assertion.post_id
             where assertion.valid_to is null
        ), per_post as (
            select eligible.post_id,
                   count(distinct memberships.voice_concept_code) as membership_count,
                   bool_or(memberships.assertion_status_code = 'source') as has_source,
                   bool_or(memberships.assertion_status_code = 'derived') as has_derived
              from eligible left join memberships on memberships.post_id = eligible.post_id
             group by eligible.post_id
        ), conflicts as (
            select distinct source.post_id
              from memberships source join memberships derived on derived.post_id = source.post_id
             where source.assertion_status_code = 'source'
               and derived.assertion_status_code = 'derived'
               and source.voice_concept_code <> derived.voice_concept_code
        ), categories as (
            select voice_concept_code, count(distinct post_id) as post_count
              from memberships group by voice_concept_code
        )
        select count(*) as total_eligible,
               count(*) filter (where membership_count = 1) as classified_unique,
               count(*) filter (where membership_count > 1) as multi_membership,
               count(*) filter (where coalesce(has_source, false)) as source_count,
               count(*) filter (where coalesce(has_derived, false)) as derived_count,
               count(*) filter (where membership_count = 0) as unavailable,
               (select count(*) from conflicts) as disagreement,
               coalesce((select jsonb_object_agg(voice_concept_code, post_count)
                           from categories), '{}'::jsonb) as category_post_counts
          from per_post
        """,
        list(authorized_corporate_entity_ids),
        list(authorized_process_unit_ids),
        date_from,
        date_to,
        corporate_entity_id,
        process_unit_id,
        team_id,
        person_id,
        product_catalog_id,
        project_key,
    )
    return dict(row)
