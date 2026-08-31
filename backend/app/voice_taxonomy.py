"""Authorized aggregate reads for source-preserving voice assertions."""

from __future__ import annotations

from datetime import date
from typing import Any, Protocol

from backend.app.post_eligibility import source_post_eligibility_sql


class _Connection(Protocol):
    async def fetchrow(self, query: str, *args: object) -> Any:
        """Fetch one aggregate row with bound parameters."""
        pass  # pragma: no cover - structural protocol declaration


async def warm_voice_taxonomy_read_statements(conn: _Connection) -> None:
    """Prepare each exact read shape before the pool serves HTTP traffic."""
    common = {
        "authorized_corporate_entity_ids": (),
        "authorized_process_unit_ids": (),
        "source_context_required": True,
    }
    await load_voice_taxonomy_summary(conn, **common)
    await load_voice_taxonomy_summary(conn, **common, date_from=date.min)
    await load_voice_taxonomy_summary(
        conn,
        **common,
        team_id="00000000-0000-0000-0000-000000000000",
    )


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
    excluded_corporate_entity_ids: tuple[str, ...] = (),
    source_context_required: bool | None = None,
) -> dict[str, Any]:
    """Count overlapping voice memberships over one authorized denominator."""
    if source_context_required is not None and any(
        value is not None for value in (team_id, person_id, product_catalog_id, project_key)
    ):
        projection = await conn.fetchrow(
            """
            select count(*) as total_eligible,
                   count(*) filter (where membership_count = 1) as classified_unique,
                   count(*) filter (where membership_count > 1) as multi_membership,
                   count(*) filter (where has_source) as source_count,
                   count(*) filter (where has_derived) as derived_count,
                   count(*) filter (where membership_count = 0) as unavailable,
                   count(*) filter (where disagreement) as disagreement,
                   jsonb_strip_nulls(jsonb_build_object(
                       'voc', nullif(count(*) filter (where 'voc' = any(voice_concept_codes)), 0),
                       'vocc', nullif(count(*) filter (where 'vocc' = any(voice_concept_codes)), 0),
                       'voco', nullif(count(*) filter (where 'voco' = any(voice_concept_codes)), 0),
                       'vom', nullif(count(*) filter (where 'vom' = any(voice_concept_codes)), 0),
                       'vop', nullif(count(*) filter (where 'vop' = any(voice_concept_codes)), 0),
                       'vos', nullif(count(*) filter (where 'vos' = any(voice_concept_codes)), 0),
                       'voe', nullif(count(*) filter (where 'voe' = any(voice_concept_codes)), 0),
                       'vob', nullif(count(*) filter (where 'vob' = any(voice_concept_codes)), 0),
                       'vor', nullif(count(*) filter (where 'vor' = any(voice_concept_codes)), 0),
                       'voi', nullif(count(*) filter (where 'voi' = any(voice_concept_codes)), 0),
                       'voso', nullif(count(*) filter (where 'voso' = any(voice_concept_codes)), 0),
                       'vops', nullif(count(*) filter (where 'vops' = any(voice_concept_codes)), 0)
                   )) as category_post_counts,
                   coalesce(bool_or(next_transition_at <= current_timestamp), false)
                       as projection_stale
              from voice_taxonomy_post_read_projection projection
             where ($3::date is null or projection.event_date >= $3)
               and ($4::date is null or projection.event_date <= $4)
               and ($5::uuid is null or projection.corporate_entity_id = $5)
               and ($6::uuid is null or projection.process_unit_id = $6)
               and (projection.visibility_code = 'public'
                    or (projection.corporate_entity_id = any($1::uuid[])
                        and (cardinality($2::uuid[]) = 0
                             or projection.process_unit_id = any($2::uuid[]))))
               and not (projection.corporate_entity_id = any($11::uuid[]))
               and (not $12::boolean or projection.source_context_present)
               and ($7::uuid is null or exists (
                    select 1 from post_team_mention team
                     where team.post_id = projection.post_id and team.team_id = $7))
               and ($8::uuid is null or exists (
                    select 1 from post_person_mention person
                     where person.post_id = projection.post_id and person.person_id = $8))
               and ($9::uuid is null or exists (
                    select 1 from post_product_mention product
                     where product.post_id = projection.post_id
                       and product.product_catalog_id = $9))
               and ($10::text is null or exists (
                    select 1 from post_project_mention project
                     where project.post_id = projection.post_id and project.project_key = $10))
            """,
            list(authorized_corporate_entity_ids), list(authorized_process_unit_ids),
            date_from, date_to, corporate_entity_id, process_unit_id, team_id,
            person_id, product_catalog_id, project_key,
            list(excluded_corporate_entity_ids), source_context_required,
        )
        if not projection["projection_stale"]:
            return {
                key: value for key, value in dict(projection).items()
                if key != "projection_stale"
            }

    if (
        source_context_required is not None
        and team_id is None
        and person_id is None
        and product_catalog_id is None
        and project_key is None
    ):
        projection_relation = (
            "voice_taxonomy_month_read_projection"
            if date_from is None and date_to is None
            else "voice_taxonomy_day_read_projection"
        )
        date_predicate = (
            "$3::date is null and $4::date is null"
            if date_from is None and date_to is None
            else "($3::date is null or projection.event_date >= $3) "
                 "and ($4::date is null or projection.event_date <= $4)"
        )
        projection = await conn.fetchrow(
            f"""
            select coalesce(sum(total_eligible), 0)::bigint as total_eligible,
                   coalesce(sum(classified_unique), 0)::bigint as classified_unique,
                   coalesce(sum(multi_membership), 0)::bigint as multi_membership,
                   coalesce(sum(source_count), 0)::bigint as source_count,
                   coalesce(sum(derived_count), 0)::bigint as derived_count,
                   coalesce(sum(unavailable), 0)::bigint as unavailable,
                   coalesce(sum(disagreement), 0)::bigint as disagreement,
                   jsonb_strip_nulls(jsonb_build_object(
                       'voc', sum((category_post_counts ->> 'voc')::bigint),
                       'vocc', sum((category_post_counts ->> 'vocc')::bigint),
                       'voco', sum((category_post_counts ->> 'voco')::bigint),
                       'vom', sum((category_post_counts ->> 'vom')::bigint),
                       'vop', sum((category_post_counts ->> 'vop')::bigint),
                       'vos', sum((category_post_counts ->> 'vos')::bigint),
                       'voe', sum((category_post_counts ->> 'voe')::bigint),
                       'vob', sum((category_post_counts ->> 'vob')::bigint),
                       'vor', sum((category_post_counts ->> 'vor')::bigint),
                       'voi', sum((category_post_counts ->> 'voi')::bigint),
                       'voso', sum((category_post_counts ->> 'voso')::bigint),
                       'vops', sum((category_post_counts ->> 'vops')::bigint)
                   )) as category_post_counts,
                   coalesce(bool_or(next_transition_at <= current_timestamp), false)
                       as projection_stale
              from {projection_relation} projection
             where {date_predicate}
                   and ($5::uuid is null or projection.corporate_entity_id = $5)
                   and ($6::uuid is null or projection.process_unit_key = $6)
                   and (projection.visibility_code = 'public'
                        or (projection.corporate_entity_id = any($1::uuid[])
                            and (cardinality($2::uuid[]) = 0
                                 or projection.process_unit_key = any($2::uuid[]))))
                   and not (projection.corporate_entity_id = any($7::uuid[]))
                   and (not $8::boolean or projection.source_context_present)
            """,
            list(authorized_corporate_entity_ids),
            list(authorized_process_unit_ids),
            date_from,
            date_to,
            corporate_entity_id,
            process_unit_id,
            list(excluded_corporate_entity_ids),
            source_context_required,
        )
        if not projection["projection_stale"]:
            return {
                key: value for key, value in dict(projection).items()
                if key != "projection_stale"
            }

    row = await conn.fetchrow(
        f"""
        with eligible as (
            select post.post_id
              from source_post post
             where {source_post_eligibility_sql('post', source_context_required=source_context_required)}
               and (post.visibility_code = 'public'
                    or (post.corporate_entity_id = any($1::uuid[])
                        and (cardinality($2::uuid[]) = 0
                             or post.process_unit_id = any($2::uuid[]))))
               and ($3::date is null or timezone('Asia/Seoul', coalesce(post.event_occurred_at, post.created_at))::date >= $3)
               and ($4::date is null or timezone('Asia/Seoul', coalesce(post.event_occurred_at, post.created_at))::date <= $4)
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
               and not (post.corporate_entity_id = any($11::uuid[]))
        ), memberships as (
            select assertion.post_id, assertion.assertion_status_code,
                   assertion.voice_concept_code
              from post_voice_classification_assertion assertion
              join eligible on eligible.post_id = assertion.post_id
             where (assertion.valid_from is null or assertion.valid_from <= current_timestamp)
               and (assertion.valid_to is null or assertion.valid_to > current_timestamp)
        ), per_post as (
            select eligible.post_id,
                   count(distinct memberships.voice_concept_code) as membership_count,
                   bool_or(memberships.assertion_status_code = 'source') as has_source,
                   bool_or(memberships.assertion_status_code = 'derived') as has_derived
              from eligible left join memberships on memberships.post_id = eligible.post_id
             group by eligible.post_id
        ), conflicts as (
            select post_id
              from memberships
             group by post_id
            having bool_or(assertion_status_code = 'source')
               and bool_or(assertion_status_code = 'derived')
               and array_agg(distinct voice_concept_code order by voice_concept_code)
                       filter (where assertion_status_code = 'source')
                   is distinct from
                   array_agg(distinct voice_concept_code order by voice_concept_code)
                       filter (where assertion_status_code = 'derived')
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
                           from categories), '{{}}'::jsonb) as category_post_counts
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
        list(excluded_corporate_entity_ids),
    )
    return dict(row)
