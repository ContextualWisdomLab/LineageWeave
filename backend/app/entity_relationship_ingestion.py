"""Runs an `EntityRelationshipClient` over a post's already-known
organization names (typically the union of Keyman affiliations from
`keyman_ingestion.ingest_post_keymen`) and persists the classification to
`post_counterparty_entity`.
"""

from __future__ import annotations

import asyncpg

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

    relationships = client.classify(post_title, post_body, organization_names)

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
                verification_checked_at = null
            """,
            post_id,
            relationship.organization_name,
            relationship.relationship_type_code,
        )

    return relationships
