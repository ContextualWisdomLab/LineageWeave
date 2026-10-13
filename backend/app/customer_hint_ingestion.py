"""Corroborate raw customer hints without changing source-post ownership.

`source_post.source_customer_code` remains raw evidence. A corroborated
Customer Master identity is persisted separately in
`source_post_customer_resolution`; `source_post.corporate_entity_id` and
`process_unit_id` remain authorization ownership (ADR 0042 / ADR 0374).
Corporate catalog binding remains owned by `corporate_entity_ingestion`
(ADR 0010 / ADR 0012 / ADR 0160); Customer Master never creates a competing
name-only identity path.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

import asyncpg

from lineageweave.corporate_hierarchy_inference import CorporateHierarchyInferenceClient
from lineageweave.corporate_hierarchy_resolution import CorporateEntityCandidate
from lineageweave.customer_hint_resolution import CustomerHintResolutionClient
from lineageweave.image_content import NullImageContentClient
from lineageweave.organization_name_resolution import resolve_and_verify_organization_name
from lineageweave.post_content_normalization import normalize_post_body
from lineageweave.relation_verification import STATUS_CORROBORATED, RelationVerificationClient

from backend.app.corporate_entity_ingestion import get_or_create_corporate_entity
from backend.app.post_eligibility import (
    fetch_visible_customer_hint_evidence,
    lock_visible_customer_hint_sources,
)


_EXCERPT_LENGTH = 1500


async def _load_corporate_entity_candidates(
    database_connection: asyncpg.Connection,
) -> list[CorporateEntityCandidate]:
    """Load the catalog snapshot consumed by the canonical organization resolver."""
    rows = await database_connection.fetch(
        "select corporate_entity_id, entity_name from corporate_entity"
    )
    return [
        CorporateEntityCandidate(
            corporate_entity_id=str(row["corporate_entity_id"]),
            entity_name=row["entity_name"],
        )
        for row in rows
    ]


async def resolve_customer_hint(
    pool: asyncpg.Pool,
    resolution_client: CustomerHintResolutionClient,
    verification_client: RelationVerificationClient,
    hierarchy_inference_client: CorporateHierarchyInferenceClient,
    hint_code: str,
    corporate_entity_ids: Sequence[str],
    process_unit_ids: Sequence[str],
) -> dict[str, Any] | None:
    """Resolve one visible raw hint to separately persisted customer identity.

    Evidence capture is bounded to the authenticated caller's explicit
    corporate/process scope. The connection used for source evidence is
    released before customer-name resolution/verification. Corporate catalog
    binding is delegated to the existing ADR 0010/0012/0160 owner; it never
    runs while source rows are locked. Persistence then reacquires a short
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

    # Copy scalars before any external work; never retain mutable evidence rows.
    evidence_rows = [dict(row) for row in evidence_rows]
    if any(not isinstance(row.get("source_content_digest"), str)
           or len(row["source_content_digest"]) != 64 for row in evidence_rows):
        return None
    captured_digests = {str(row["post_id"]): row["source_content_digest"] for row in evidence_rows}
    vision_client = NullImageContentClient()
    bindings = []
    for row in evidence_rows:
        # The only derivation source for this association is this post.
        excerpts = (
            f"{row['post_title']}\n"
            f"{normalize_post_body(row['post_body'], vision_client=vision_client).text[:_EXCERPT_LENGTH]}"
        )
        verified = await asyncio.to_thread(
            resolve_and_verify_organization_name,
            normalized_hint_code,
            excerpts,
            resolution_client,
            verification_client,
        )
        if verified is None or verified.verification_status_code != STATUS_CORROBORATED:
            continue
        entity_name = verified.resolved_organization_name.strip()
        if not entity_name:
            continue
        # Canonical catalog ownership, with no source locks across network work.
        async with pool.acquire() as database_connection:
            candidates = await _load_corporate_entity_candidates(database_connection)
            entity_id = await get_or_create_corporate_entity(
                database_connection, entity_name, excerpts,
                hierarchy_inference_client, verification_client, candidates,
            )
        if entity_id is not None:
            bindings.append((str(row["post_id"]), entity_id, entity_name, verified))
    if not bindings or len({binding[1] for binding in bindings}) != 1:
        return None

    captured_post_ids = tuple(binding[0] for binding in bindings)
    async with pool.acquire() as database_connection:
        async with database_connection.transaction():
            revalidated_rows = await lock_visible_customer_hint_sources(
                database_connection,
                corporate_entity_ids,
                process_unit_ids,
                normalized_hint_code,
                captured_post_ids,
            )
            if {str(row["post_id"]) for row in revalidated_rows} != set(captured_post_ids):
                return None
            if any(row.get("source_content_digest") != captured_digests[str(row["post_id"])]
                   for row in revalidated_rows):
                return None
            linked_count = 0
            for captured_id, entity_id, entity_name, verified in bindings:
                linked_rows = await database_connection.fetch(
                    """
                    insert into source_post_customer_resolution (
                        post_id, source_customer_code, resolved_corporate_entity_id,
                        resolved_entity_name, verification_status_code,
                        verification_evidence_url, source_content_digest, resolved_at
                    )
                    select source_post.post_id, source_post.source_customer_code,
                           $2::uuid, $3, $4, $5, $6, now()
                      from unnest($1::text[]) as captured(source_post_id)
                      join source_post on source_post.post_id = captured.source_post_id::uuid
                    on conflict (post_id) do update set
                        source_customer_code = excluded.source_customer_code,
                        resolved_corporate_entity_id = excluded.resolved_corporate_entity_id,
                        resolved_entity_name = excluded.resolved_entity_name,
                        verification_status_code = excluded.verification_status_code,
                        verification_evidence_url = excluded.verification_evidence_url,
                        source_content_digest = excluded.source_content_digest,
                        resolved_at = excluded.resolved_at
                    returning post_id
                    """,
                    [captured_id], entity_id, entity_name,
                    verified.verification_status_code, verified.verification_evidence_url,
                    captured_digests[captured_id],
                )
                linked_count += len(linked_rows)
            return {
                "corporate_entity_id": str(bindings[0][1]),
                "entity_name": bindings[0][2],
                "linked_post_count": linked_count,
                "verification_evidence_url": bindings[0][3].verification_evidence_url,
            }
