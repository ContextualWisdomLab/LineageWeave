"""Corroborate raw customer hints without changing source-post ownership.

`source_post.source_customer_code` remains raw evidence. A corroborated
Customer Master identity is persisted separately in
`source_post_customer_resolution`; `source_post.corporate_entity_id` and
`process_unit_id` remain authorization ownership (ADR 0042 / ADR 0374).
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Sequence
from typing import Any

import asyncpg

from backend.app.post_eligibility import (
    fetch_visible_customer_hint_evidence,
    lock_visible_customer_hint_sources,
)
from lineageweave.customer_hint_resolution import CustomerHintResolutionClient
from lineageweave.image_content import NullImageContentClient
from lineageweave.organization_name_resolution import resolve_and_verify_organization_name
from lineageweave.post_content_normalization import normalize_post_body
from lineageweave.relation_verification import STATUS_CORROBORATED, RelationVerificationClient


_EXCERPT_LENGTH = 1500


def _resolved_customer_code(entity_name: str) -> str:
    """Return a stable catalog code derived from corroborated identity, not tenant hint."""
    digest = hashlib.sha256(entity_name.strip().casefold().encode("utf-8")).hexdigest()[:24]
    return f"RESOLVED-{digest}"


async def resolve_customer_hint(
    pool: asyncpg.Pool,
    resolution_client: CustomerHintResolutionClient,
    verification_client: RelationVerificationClient,
    hint_code: str,
    corporate_entity_ids: Sequence[str],
    process_unit_ids: Sequence[str],
) -> dict[str, Any] | None:
    """Resolve one visible raw hint to separately persisted customer identity.

    Evidence capture is bounded to the authenticated caller's explicit
    corporate/process scope. The database connection is released before
    external resolution/verification. Persistence then reacquires a short
    transaction, revalidates and share-locks the exact captured source set,
    and fails closed if authorization-relevant state changed meanwhile.
    """
    if not resolution_client.available:
        return None

    normalized_hint_code = hint_code.strip()
    if not normalized_hint_code:
        return None

    async with pool.acquire() as database_connection:
        evidence_rows = await fetch_visible_customer_hint_evidence(
            database_connection,
            corporate_entity_ids,
            process_unit_ids,
            normalized_hint_code,
        )
    if not evidence_rows:
        return None

    captured_post_ids = tuple(str(row["post_id"]) for row in evidence_rows)
    vision_client = NullImageContentClient()
    excerpts = "\n---\n".join(
        f"{row['post_title']}\n"
        f"{normalize_post_body(row['post_body'], vision_client=vision_client).text[:_EXCERPT_LENGTH]}"
        for row in evidence_rows
    )
    verified_customer_resolution = await asyncio.to_thread(
        resolve_and_verify_organization_name,
        normalized_hint_code,
        excerpts,
        resolution_client,
        verification_client,
    )
    if (
        verified_customer_resolution is None
        or verified_customer_resolution.verification_status_code != STATUS_CORROBORATED
    ):
        return None

    entity_name = verified_customer_resolution.resolved_organization_name.strip()
    if not entity_name:
        return None

    async with pool.acquire() as database_connection:
        async with database_connection.transaction():
            revalidated_rows = await lock_visible_customer_hint_sources(
                database_connection,
                corporate_entity_ids,
                process_unit_ids,
                normalized_hint_code,
                captured_post_ids,
            )
            revalidated_post_ids = {str(row["post_id"]) for row in revalidated_rows}
            if revalidated_post_ids != set(captured_post_ids):
                return None

            existing_entity = await database_connection.fetchrow(
                "select corporate_entity_id from corporate_entity where lower(entity_name) = lower($1)",
                entity_name,
            )
            if existing_entity is not None:
                resolved_corporate_entity_id = existing_entity["corporate_entity_id"]
            else:
                created_entity = await database_connection.fetchrow(
                    """
                    insert into corporate_entity (
                        corporate_entity_code,
                        entity_name,
                        entity_level_code
                    )
                    values ($1, $2, 'company')
                    on conflict (corporate_entity_code)
                    do update set entity_name = excluded.entity_name
                    returning corporate_entity_id
                    """,
                    _resolved_customer_code(entity_name),
                    entity_name,
                )
                resolved_corporate_entity_id = created_entity["corporate_entity_id"]

            linked_rows = await database_connection.fetch(
                """
                insert into source_post_customer_resolution (
                    post_id,
                    source_customer_code,
                    resolved_corporate_entity_id,
                    resolved_entity_name,
                    verification_status_code,
                    verification_evidence_url,
                    resolved_at
                )
                select source_post.post_id, source_post.source_customer_code,
                       $2::uuid, $3, $4, $5, now()
                  from unnest($1::text[]) as captured(source_post_id)
                  join source_post on source_post.post_id = captured.source_post_id::uuid
                on conflict (post_id)
                do update set
                    source_customer_code = excluded.source_customer_code,
                    resolved_corporate_entity_id = excluded.resolved_corporate_entity_id,
                    resolved_entity_name = excluded.resolved_entity_name,
                    verification_status_code = excluded.verification_status_code,
                    verification_evidence_url = excluded.verification_evidence_url,
                    resolved_at = excluded.resolved_at
                returning post_id
                """,
                list(captured_post_ids),
                resolved_corporate_entity_id,
                entity_name,
                verified_customer_resolution.verification_status_code,
                verified_customer_resolution.verification_evidence_url,
            )

    return {
        "corporate_entity_id": str(resolved_corporate_entity_id),
        "entity_name": entity_name,
        "linked_post_count": len(linked_rows),
        "verification_evidence_url": verified_customer_resolution.verification_evidence_url,
    }
