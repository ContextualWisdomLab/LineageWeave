"""Runs a `RelationVerificationClient` over a post's already-classified
`post_counterparty_entity` rows and persists the outcome. Separate from
`entity_relationship_ingestion.py`'s classification step (a distinct,
explicitly-triggered action, not run automatically on every extraction --
see ADR 0005) so a caller can re-verify without paying for a fresh LLM
classification.
"""

from __future__ import annotations

from dataclasses import dataclass

import asyncpg

from lineageweave.relation_verification import RelationVerificationClient


@dataclass(frozen=True)
class VerifiedRelation:
    """One counterparty row's verification outcome, for the API response."""

    counterparty_entity_name: str
    verification_status_code: str
    verification_evidence_url: str | None


async def verify_post_relations(
    conn: asyncpg.Connection,
    client: RelationVerificationClient,
    post_id: str,
) -> list[VerifiedRelation]:
    """Verifies every counterparty row still `verify_pending` for this
    post and persists the result. Already-checked rows are left alone --
    call `POST /api/posts/{id}/verify-relations` again after a
    re-extraction resets them to pending (see
    `entity_relationship_ingestion.ingest_post_entity_relationships`).

    Raises whatever `client.verify` raises (a failed search must not be
    recorded as "uncorroborated") -- callers should check
    `client.available` first, same discipline as every other pluggable
    channel in this repo.
    """
    rows = await conn.fetch(
        """
        select c.counterparty_entity_name, v.lookup_label as relationship_label
        from post_counterparty_entity c
        join common_lookup_value v on v.lookup_code = c.relationship_type_code
        where c.post_id = $1 and c.verification_status_code = 'verify_pending'
        order by c.counterparty_entity_name
        """,
        post_id,
    )

    verified: list[VerifiedRelation] = []
    for row in rows:
        result = client.verify(row["counterparty_entity_name"], row["relationship_label"])
        await conn.execute(
            """
            update post_counterparty_entity
            set verification_status_code = $3,
                verification_evidence_url = $4,
                verification_checked_at = now()
            where post_id = $1 and counterparty_entity_name = $2
            """,
            post_id,
            row["counterparty_entity_name"],
            result.status_code,
            result.evidence_url,
        )
        verified.append(
            VerifiedRelation(
                counterparty_entity_name=row["counterparty_entity_name"],
                verification_status_code=result.status_code,
                verification_evidence_url=result.evidence_url,
            )
        )
    return verified
