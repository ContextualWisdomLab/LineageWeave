"""Runs a `RelationVerificationClient` over a post's already-classified
`post_counterparty_entity` rows and persists the outcome. Separate from
`entity_relationship_ingestion.py`'s classification step (a distinct,
explicitly-triggered action, not run automatically on every extraction --
see ADR 0005) so a caller can re-verify without paying for a fresh LLM
classification.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass

import asyncpg

from lineageweave.relation_verification import RelationVerificationClient


@dataclass(frozen=True)
class VerifiedRelation:
    """One counterparty row's verification outcome, for the API response."""

    counterparty_entity_name: str
    verification_status_code: str
    verification_evidence_url: str | None
    verification_evidence_post_id: str | None


@dataclass(frozen=True)
class _PendingRelation:
    counterparty_entity_name: str
    relationship_label: str
    internal_evidence_post_id: str | None


async def _find_internal_evidence_post(
    conn: asyncpg.Connection,
    post_id: str,
    organization_name: str,
    relationship_label: str,
    visible_corporate_entity_ids: Sequence[str],
) -> str | None:
    """Find one authorized source post supporting the same relation context.

    The query searches normalized DOM/image text when it exists and falls back
    to the source title/body. Public posts are always eligible; private posts
    are restricted to the caller's affiliated corporate entities. The result
    is evidence metadata only and never changes the external verification
    status.

    Each term is matched against title, body, and content-unit text as three
    separately indexed branches unioned together (ADR 0043's title/body
    trigram indexes), rather than one `like` over a per-row concatenation --
    the concatenated form forces a sequential scan with a per-row string
    build over the whole real-imported corpus (tens of seconds at
    real-corpus scale; see the `report_leftover_pair`-class perf class of
    bug), where the unioned form stays on indexed bitmap scans.
    """
    row = await conn.fetchrow(
        """
        with term1_matches as (
            (select post_id from source_post where lower(post_title) like '%' || lower($2) || '%')
            union
            (select post_id from source_post
              where lower(left(source_post_search_text(post_body), 16384)) like '%' || lower($2) || '%')
            union
            (select post_id from post_content_unit where lower(unit_text) like '%' || lower($2) || '%')
        ),
        term2_matches as (
            (select post_id from source_post where lower(post_title) like '%' || lower($3) || '%')
            union
            (select post_id from source_post
              where lower(left(source_post_search_text(post_body), 16384)) like '%' || lower($3) || '%')
            union
            (select post_id from post_content_unit where lower(unit_text) like '%' || lower($3) || '%')
        )
        select candidate.post_id
          from source_post candidate
          join term1_matches t1 on t1.post_id = candidate.post_id
          join term2_matches t2 on t2.post_id = candidate.post_id
         where candidate.post_id <> $1
           and (
                candidate.visibility_code = 'public'
                or candidate.corporate_entity_id::text = any($4::text[])
           )
         order by candidate.updated_at desc, candidate.post_id
         limit 1
        """,
        post_id,
        organization_name,
        relationship_label,
        list(visible_corporate_entity_ids),
    )
    return None if row is None else str(row["post_id"])


async def verify_post_relations(
    conn: asyncpg.Connection,
    client: RelationVerificationClient,
    post_id: str,
    visible_corporate_entity_ids: Sequence[str] = (),
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
        internal_evidence_post_id = await _find_internal_evidence_post(
            conn,
            post_id,
            row["counterparty_entity_name"],
            row["relationship_label"],
            visible_corporate_entity_ids,
        )
        result = await asyncio.to_thread(
            client.verify,
            row["counterparty_entity_name"],
            row["relationship_label"],
        )
        await conn.execute(
            """
            update post_counterparty_entity
            set verification_status_code = $3,
                verification_evidence_url = $4,
                verification_evidence_post_id = $5,
                verification_checked_at = now()
            where post_id = $1 and counterparty_entity_name = $2
            """,
            post_id,
            row["counterparty_entity_name"],
            result.status_code,
            result.evidence_url,
            internal_evidence_post_id,
        )
        verified.append(
            VerifiedRelation(
                counterparty_entity_name=row["counterparty_entity_name"],
                verification_status_code=result.status_code,
                verification_evidence_url=result.evidence_url,
                verification_evidence_post_id=internal_evidence_post_id,
            )
        )
    return verified


async def verify_post_relations_from_pool(
    pool: asyncpg.Pool,
    client: RelationVerificationClient,
    post_id: str,
    visible_corporate_entity_ids: Sequence[str] = (),
) -> list[VerifiedRelation]:
    """Verify relations without reserving a DB connection during web I/O."""
    async with pool.acquire() as conn:
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
        pending = [
            _PendingRelation(
                str(row["counterparty_entity_name"]),
                str(row["relationship_label"]),
                await _find_internal_evidence_post(
                    conn,
                    post_id,
                    row["counterparty_entity_name"],
                    row["relationship_label"],
                    visible_corporate_entity_ids,
                ),
            )
            for row in rows
        ]

    verified = []
    for relation in pending:
        result = await asyncio.to_thread(
            client.verify,
            relation.counterparty_entity_name,
            relation.relationship_label,
        )
        completed = VerifiedRelation(
            relation.counterparty_entity_name,
            result.status_code,
            result.evidence_url,
            relation.internal_evidence_post_id,
        )
        async with pool.acquire() as conn:
            update_status = await conn.execute(
                """
                update post_counterparty_entity
                set verification_status_code = $3,
                    verification_evidence_url = $4,
                    verification_evidence_post_id = $5,
                    verification_checked_at = now()
                where post_id = $1 and counterparty_entity_name = $2
                  and verification_status_code = 'verify_pending'
                """,
                post_id,
                completed.counterparty_entity_name,
                completed.verification_status_code,
                completed.verification_evidence_url,
                completed.verification_evidence_post_id,
            )
        if update_status == "UPDATE 1":
            verified.append(completed)
    return verified
