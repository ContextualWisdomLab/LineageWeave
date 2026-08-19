"""Persist Searxng abbreviation matches against the authorized tree."""

from __future__ import annotations

import asyncio
from typing import Any

import asyncpg

from lineageweave.abbreviation_tree_corroboration import (
    AbbreviationTreeMatch,
    TreeEntityCandidate,
    abbreviation_candidates,
    corroborate_abbreviation_against_tree,
)
from lineageweave.customer_group_tree import CatalogEntityRow, authorized_catalog_ids
from lineageweave.relation_verification import RelationVerificationClient


async def collect_post_organization_names(conn: asyncpg.Connection, post_id: str) -> tuple[str, ...]:
    """Organization strings already extracted onto this post.

    Keyman affiliations and classified counterparties are the mentions
    operators can see. This path does not invent a name from post text.
    """
    rows = await conn.fetch(
        """
        select distinct name from (
            select pa.affiliated_organization_name as name
              from post_person_mention ppm
              join person_affiliation pa on pa.person_id = ppm.person_id
             where ppm.post_id = $1
            union
            select c.counterparty_entity_name as name
              from post_counterparty_entity c
             where c.post_id = $1
        ) mentioned
        where name is not null and btrim(name) <> ''
        order by name
        """,
        post_id,
    )
    return tuple(row["name"] for row in rows)


async def load_authorized_tree_candidates(
    conn: asyncpg.Connection,
    affiliated_entity_ids: list[str],
) -> tuple[TreeEntityCandidate, ...]:
    """Catalog nodes the account may corroborate an abbreviation against."""
    entity_rows = await conn.fetch(
        """
        select corporate_entity_id, parent_entity_id, entity_name, entity_level_code
        from corporate_entity
        """
    )
    entities = tuple(
        CatalogEntityRow(
            entity_id=str(row["corporate_entity_id"]),
            parent_entity_id=str(row["parent_entity_id"]) if row["parent_entity_id"] is not None else None,
            entity_name=row["entity_name"],
            entity_level_code=row["entity_level_code"],
        )
        for row in entity_rows
    )
    needed = authorized_catalog_ids(entities, affiliated_entity_ids)
    return tuple(
        TreeEntityCandidate(entity_id=row.entity_id, entity_name=row.entity_name)
        for row in entities
        if row.entity_id in needed
    )


async def persist_abbreviation_tree_match(
    conn: asyncpg.Connection,
    match: AbbreviationTreeMatch,
) -> None:
    """Upsert one raw mention's tree-constrained Searxng outcome."""
    await conn.execute(
        """
        insert into abbreviation_tree_corroboration
            (raw_organization_name, corporate_entity_id,
             verification_status_code, verification_evidence_url)
        values ($1, $2, $3, $4)
        on conflict (raw_organization_name) do update set
            corporate_entity_id = excluded.corporate_entity_id,
            verification_status_code = excluded.verification_status_code,
            verification_evidence_url = excluded.verification_evidence_url,
            corroborated_at = now()
        """,
        match.raw_organization_name,
        match.corporate_entity_id,
        match.verification_status_code,
        match.verification_evidence_url,
    )


async def fetch_post_abbreviation_matches(
    conn: asyncpg.Connection,
    post_id: str,
) -> list[dict[str, Any]]:
    """Cached tree matches for organization names already on this post."""
    names = await collect_post_organization_names(conn, post_id)
    if not names:
        return []
    rows = await conn.fetch(
        """
        select raw_organization_name, corporate_entity_id,
               verification_status_code, verification_evidence_url
          from abbreviation_tree_corroboration
         where raw_organization_name = any($1::text[])
         order by raw_organization_name
        """,
        list(names),
    )
    return [
        {
            "raw_organization_name": row["raw_organization_name"],
            "corporate_entity_id": (
                str(row["corporate_entity_id"]) if row["corporate_entity_id"] is not None else None
            ),
            "verification_status_code": row["verification_status_code"],
            "verification_evidence_url": row["verification_evidence_url"],
        }
        for row in rows
    ]


async def corroborate_post_abbreviations(
    conn: asyncpg.Connection,
    verification_client: RelationVerificationClient,
    post_id: str,
    affiliated_entity_ids: list[str],
) -> list[AbbreviationTreeMatch]:
    """Run Searxng against the authorized tree for this post's mentions."""
    names = await collect_post_organization_names(conn, post_id)
    candidates = await load_authorized_tree_candidates(conn, affiliated_entity_ids)
    to_check = abbreviation_candidates(names, candidates)
    matches: list[AbbreviationTreeMatch] = []
    for raw_name in to_check:
        match = await asyncio.to_thread(
            corroborate_abbreviation_against_tree,
            raw_name,
            candidates,
            verification_client,
        )
        await persist_abbreviation_tree_match(conn, match)
        matches.append(match)
    return matches
