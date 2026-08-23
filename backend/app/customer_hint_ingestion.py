"""Resolves one observed customer-hint code (`source_post.source_customer_code`)
to a real-world `corporate_entity`, using the text of posts that share the
code as evidence -- and, per the same corroboration discipline
`organization_name_resolution_ingestion.py` already applies to in-text
abbreviations (ADR 0008), never binding a new customer name that external
search did not corroborate. An uncorroborated or unresolved guess leaves
the hint exactly as unresolved as it started; it never invents a Customer
Master entity from a single ungrounded LLM answer.

A newly resolved name is created through
:func:`backend.app.corporate_entity_ingestion.get_or_create_corporate_entity`
-- the same "통합 고객사 계열 tree AI" hierarchy-inference pipeline
`keyman_ingestion.py`'s affiliation resolution already uses -- rather than
a bare same-level insert, so a SAP-sourced customer code that resolves to
e.g. "Acme Electronics South Plant" gets its inferred parent chain
(plant -> company -> group) at resolution time instead of landing as a
permanently flat, unparented row.

A genuine similarity tie among *existing* catalog entities is checked for
separately, before that hierarchy-aware path runs, and stays unbound per
ADR 0026 (a tie must never create a third same-named row) -- it is not
treated as "no hierarchy channel configured" and does not fall back to a
flat insert.
"""

from __future__ import annotations

import asyncio
from typing import Any

import asyncpg

from lineageweave.corporate_hierarchy_inference import CorporateHierarchyInferenceClient
from lineageweave.corporate_hierarchy_resolution import RESOLUTION_TIE, score_corporate_entity
from lineageweave.customer_hint_resolution import CustomerHintResolutionClient
from lineageweave.image_content import NullImageContentClient
from lineageweave.organization_name_resolution import resolve_and_verify_organization_name
from lineageweave.post_content_normalization import normalize_post_body
from lineageweave.relation_verification import STATUS_CORROBORATED, RelationVerificationClient

from .corporate_entity_ingestion import (
    get_or_create_corporate_entity,
    prune_observed_entity_for_posts,
    record_observed_entity,
)
from .keyman_ingestion import _load_corporate_entity_candidates

_EXCERPT_LENGTH = 1500


async def resolve_customer_hint(
    conn: asyncpg.Connection,
    resolution_client: CustomerHintResolutionClient,
    verification_client: RelationVerificationClient,
    hierarchy_inference_client: CorporateHierarchyInferenceClient,
    hint_code: str,
) -> dict[str, Any] | None:
    """Resolve one `source_customer_code` hint to a real `corporate_entity`.

    Returns ``None`` when the resolver is unavailable, no eligible posts
    carry this hint, or the proposed name was not externally corroborated.
    Otherwise creates (or reuses, by case-insensitive exact name) the
    entity and reclaims every post sharing this hint that still sits at
    its account's default placeholder entity, returning the entity
    id/name plus how many posts were reclaimed.
    """
    if not resolution_client.available:
        return None
    # Five rows and 20,000 raw body characters per row bound both transfer and
    # parsing before deterministic normalization. The SQL remains literal;
    # only the observed hint code is a bound value.
    rows = await conn.fetch(
        """
        select post_title, left(post_body, 20000) as post_body
          from source_post
         where source_customer_code = $1
           and nullif(btrim(source_post.source_draft_code), '') is null
           and nullif(btrim(source_post.source_deleted_flag), '') is null
           and not (
               (
                   nullif(btrim(source_post.source_author_code), '') is null
                   and nullif(btrim(source_post.source_author_name), '') is null
                   and nullif(btrim(source_post.source_company_code), '') is null
                   and nullif(btrim(source_post.source_company_name), '') is null
                   and nullif(btrim(source_post.source_process_unit_code), '') is null
                   and nullif(btrim(source_post.source_process_unit_name), '') is null
                   and nullif(btrim(source_post.source_sales_pool_code), '') is null
                   and nullif(btrim(source_post.source_sales_pool_name), '') is null
                   and nullif(btrim(source_post.source_customer_code), '') is null
                   and nullif(btrim(source_post.source_customer_name), '') is null
                   and nullif(btrim(source_post.source_project_code), '') is null
                   and nullif(btrim(source_post.source_project_name), '') is null
               )
               and exists (
                   select 1
                     from source_post real_post
                    where (
                        nullif(btrim(real_post.source_author_code), '') is not null
                        or nullif(btrim(real_post.source_author_name), '') is not null
                        or nullif(btrim(real_post.source_company_code), '') is not null
                        or nullif(btrim(real_post.source_company_name), '') is not null
                        or nullif(btrim(real_post.source_process_unit_code), '') is not null
                        or nullif(btrim(real_post.source_process_unit_name), '') is not null
                        or nullif(btrim(real_post.source_sales_pool_code), '') is not null
                        or nullif(btrim(real_post.source_sales_pool_name), '') is not null
                        or nullif(btrim(real_post.source_customer_code), '') is not null
                        or nullif(btrim(real_post.source_customer_name), '') is not null
                        or nullif(btrim(real_post.source_project_code), '') is not null
                        or nullif(btrim(real_post.source_project_name), '') is not null
                    )
               )
           )
         order by created_at desc
         limit 5
        """,
        hint_code,
    )
    if not rows:
        return None

    vision_client = NullImageContentClient()
    excerpts = "\n---\n".join(
        f"{row['post_title']}\n"
        f"{normalize_post_body(row['post_body'], vision_client=vision_client).text[:_EXCERPT_LENGTH]}"
        for row in rows
    )
    resolution = await asyncio.to_thread(
        resolve_and_verify_organization_name,
        hint_code,
        excerpts,
        resolution_client,
        verification_client,
    )
    if resolution is None or resolution.verification_status_code != STATUS_CORROBORATED:
        return None

    entity_name = resolution.resolved_organization_name
    candidates = await _load_corporate_entity_candidates(conn)
    if score_corporate_entity(entity_name, candidates).kind == RESOLUTION_TIE:
        # ADR 0026: a tied top similarity score among *existing* catalog
        # entities must stay unbound, never create a third same-named row.
        # This is checked before get_or_create_corporate_entity runs so a
        # tie is never mistaken for "no hierarchy channel configured" below
        # and quietly given a flat fallback entity anyway.
        return None
    entity_id = await get_or_create_corporate_entity(
        conn,
        entity_name,
        excerpts,
        hierarchy_inference_client,
        verification_client,
        candidates,
    )
    if entity_id is None:
        # get_or_create_corporate_entity declined for a genuine miss -- no
        # hierarchy inference channel configured, or an inferred placement
        # that did not corroborate (a tie was already ruled out above).
        # `resolve_and_verify_organization_name` above already independently
        # corroborated the NAME itself, so a declined *placement* must not
        # regress this hint back to fully unresolved: fall back to the
        # flat, unparented entity this pathway always created before
        # hierarchy inference existed. A later re-resolve (once a hierarchy
        # channel is configured) can still enrich it with a real parent by
        # matching this same name.
        existing = await conn.fetchrow(
            "select corporate_entity_id from corporate_entity where lower(entity_name) = lower($1)",
            entity_name,
        )
        if existing is not None:
            entity_id = existing["corporate_entity_id"]
        else:
            # ON CONFLICT, not a plain INSERT: re-resolving the same hint_code
            # is not guaranteed to get byte-identical LLM phrasing back, so the
            # name-based lookup above can miss an entity this same hint already
            # created -- corporate_entity_code (deterministic from hint_code)
            # is the stable identity key a retry must key off instead.
            entity_code = f"HINT-{hint_code}"
            # Safe SQL: the statement is a literal migration-shaped query; both observed values are bound.
            created = await conn.fetchrow(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
                """
                insert into corporate_entity (corporate_entity_code, entity_name, entity_level_code)
                values ($1, $2, 'company')
                on conflict (corporate_entity_code)
                do update set entity_name = excluded.entity_name
                returning corporate_entity_id
                """,
                entity_code,
                entity_name,
            )
            entity_id = created["corporate_entity_id"]

    # `corporate_entity_id` is NOT NULL, so a bulk-imported real record
    # never sits at NULL waiting to be resolved -- it defaults to whatever
    # entity its shared placeholder `author_account_id` happens to be
    # affiliated with (the same shared-placeholder shape as the
    # `author_affiliations` hint leak fixed in semantic_hints.py). Only
    # reclaim a post still sitting at that default, never one some other
    # resolution already bound to a specific entity.
    linked = await conn.fetch(
        """
        update source_post
           set corporate_entity_id = $1
         where source_customer_code = $2
           and corporate_entity_id in (
               select corporate_entity_id from account_affiliation
                where user_account_id = source_post.author_account_id
           )
        returning post_id
        """,
        entity_id,
        hint_code,
    )
    if linked:
        # This reassignment can narrow OR widen a post's authorized-account
        # set (its corporate_entity_id, and therefore who reads it as
        # "own corp", just changed) -- reconcile every account_observed_entity
        # row sourced from these posts (ADR 0144). Re-derive rather than
        # patch in place: prune what the OLD corp granted, then re-run the
        # write-time hook for the same (entity, post) pairs so it
        # re-evaluates against the NEW corp already committed above.
        reassigned_post_ids = [str(row["post_id"]) for row in linked]
        previously_observed = await conn.fetch(
            """
            select distinct corporate_entity_id, source_post_id
              from account_observed_entity
             where source_post_id = any($1::uuid[])
            """,
            reassigned_post_ids,
        )
        await prune_observed_entity_for_posts(conn, reassigned_post_ids)
        for row in previously_observed:
            await record_observed_entity(
                conn, str(row["corporate_entity_id"]), str(row["source_post_id"])
            )
        for post_id in reassigned_post_ids:
            await record_observed_entity(conn, entity_id, post_id)
    # get_or_create_corporate_entity may have bound this hint to an
    # existing entity via fuzzy similarity matching, whose stored name can
    # differ from the freshly LLM-resolved name (e.g. punctuation/casing);
    # the exact-match fallback above can differ too (its lookup is
    # case-insensitive). Report the entity's actual catalog name, not the
    # possibly-divergent resolved name, so the response never claims a
    # name that disagrees with what is actually bound.
    canonical_name = await conn.fetchval(
        "select entity_name from corporate_entity where corporate_entity_id = $1",
        entity_id,
    )
    return {
        "corporate_entity_id": str(entity_id),
        "entity_name": canonical_name or entity_name,
        "linked_post_count": len(linked),
        "verification_evidence_url": resolution.verification_evidence_url,
    }
