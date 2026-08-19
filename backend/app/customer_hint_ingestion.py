"""Resolves one observed customer-hint code (`source_post.source_customer_code`)
to a real-world `corporate_entity`, using the text of posts that share the
code as evidence -- and, per the same corroboration discipline
`organization_name_resolution_ingestion.py` already applies to in-text
abbreviations (ADR 0008), never binding a new customer name that external
search did not corroborate. An uncorroborated or unresolved guess leaves
the hint exactly as unresolved as it started; it never invents a Customer
Master entity from a single ungrounded LLM answer.
"""

from __future__ import annotations

import asyncio
from typing import Any

import asyncpg

from lineageweave.customer_hint_resolution import CustomerHintResolutionClient
from lineageweave.image_content import NullImageContentClient
from lineageweave.organization_name_resolution import resolve_and_verify_organization_name
from lineageweave.post_content_normalization import normalize_post_body
from lineageweave.relation_verification import STATUS_CORROBORATED, RelationVerificationClient

from .post_eligibility import SOURCE_POST_ELIGIBILITY_SQL

#: How many of a hint's posts to read as resolution evidence -- enough
#: context for the LLM to recognize the real organization without
#: hitting an unbounded prompt for a hint shared by thousands of posts.
_SAMPLE_POST_LIMIT = 5
_EXCERPT_LENGTH = 1500


async def resolve_customer_hint(
    conn: asyncpg.Connection,
    resolution_client: CustomerHintResolutionClient,
    verification_client: RelationVerificationClient,
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
    rows = await conn.fetch(
        f"""
        select post_title, post_body
          from source_post
         where source_customer_code = $1
           and {SOURCE_POST_ELIGIBILITY_SQL.format(alias="source_post")}
         order by length(post_body) desc
         limit {_SAMPLE_POST_LIMIT}
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
    existing = await conn.fetchrow(
        "select corporate_entity_id from corporate_entity where lower(entity_name) = lower($1)",
        entity_name,
    )
    if existing is not None:
        entity_id = existing["corporate_entity_id"]
    else:
        created = await conn.fetchrow(
            "insert into corporate_entity (corporate_entity_code, entity_name, entity_level_code) "
            "values ($1, $2, 'company') returning corporate_entity_id",
            f"HINT-{hint_code}",
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
    return {
        "corporate_entity_id": str(entity_id),
        "entity_name": entity_name,
        "linked_post_count": len(linked),
        "verification_evidence_url": resolution.verification_evidence_url,
    }
