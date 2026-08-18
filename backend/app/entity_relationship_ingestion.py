"""Runs an `EntityRelationshipClient` over a post's already-known
organization names (typically the union of Keyman affiliations from
`keyman_ingestion.ingest_post_keymen`) and persists the classification to
`post_counterparty_entity`.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from typing import Any

import asyncpg

from lineageweave.corporate_hierarchy_resolution import (
    CorporateEntityCandidate,
    resolve_corporate_entity,
)
from lineageweave.entity_relationship_classification import (
    EntityRelationshipClient,
    OrganizationRelationship,
)


async def ingest_post_entity_relationships(
    conn: asyncpg.Connection,
    client: EntityRelationshipClient,
    post_id: str,
    post_title: str,
    post_body: str,
    organization_names: list[str],
) -> list[OrganizationRelationship]:
    """Classifies and persists each named organization's relationship to
    the post author's org. Raises whatever `client.classify` raises (a
    `NullEntityRelationshipClient` raises `RuntimeError`) -- callers
    should check `client.available` first, same discipline as every other
    pluggable channel in this repo.
    """
    if not organization_names:
        return []

    relationships = await asyncio.to_thread(
        client.classify, post_title, post_body, organization_names
    )

    for relationship in relationships:
        await conn.execute(
            """
            insert into post_counterparty_entity (post_id, counterparty_entity_name, relationship_type_code)
            values ($1, $2, $3)
            on conflict (post_id, counterparty_entity_name)
            do update set
                relationship_type_code = excluded.relationship_type_code,
                -- A re-classification invalidates any prior verification --
                -- that search was run against the OLD relationship_label,
                -- see relation_verification.py.
                verification_status_code = 'verify_pending',
                verification_evidence_url = null,
                verification_evidence_post_id = null,
                verification_checked_at = null
            """,
            post_id,
            relationship.organization_name,
            relationship.relationship_type_code,
        )

    return relationships


def attach_resolved_entity_ids(
    rows: Sequence[Mapping[str, Any]],
    candidates: Sequence[CorporateEntityCandidate],
) -> list[dict[str, Any]]:
    """Copy classified rows and attach a cataloged org id when the name resolves.

    Unresolved names keep ``corporate_entity_id`` null -- a missing
    hierarchy match is not a guessed neighborhood.
    """
    return [
        {
            **dict(row),
            "corporate_entity_id": resolve_corporate_entity(row["counterparty_entity_name"], candidates),
        }
        for row in rows
    ]


async def fetch_post_counterparties(conn: asyncpg.Connection, post_id: str) -> list[dict[str, Any]]:
    """Classified counterparties with a cataloged org id when the name resolves.

    Unresolved names keep ``corporate_entity_id`` null -- a missing
    hierarchy match is not a guessed neighborhood.
    """
    rows = await conn.fetch(
        """
        select c.counterparty_entity_name, c.relationship_type_code, v.lookup_label as relationship_label,
               c.verification_status_code, c.verification_evidence_url,
               c.verification_evidence_post_id
        from post_counterparty_entity c
        join common_lookup_value v on v.lookup_code = c.relationship_type_code
        where c.post_id = $1
        order by c.counterparty_entity_name
        """,
        post_id,
    )
    candidate_rows = await conn.fetch("select corporate_entity_id, entity_name from corporate_entity")
    candidates = [
        CorporateEntityCandidate(str(row["corporate_entity_id"]), row["entity_name"])
        for row in candidate_rows
    ]
    return attach_resolved_entity_ids(rows, candidates)
