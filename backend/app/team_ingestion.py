
"""Resolve an R&R team actor to one shared cross-post identity."""

from __future__ import annotations

import asyncpg

from lineageweave.corporate_hierarchy_resolution import (
    CorporateEntityCandidate,
    resolve_corporate_entity,
)


async def upsert_team(
    conn: asyncpg.Connection,
    team_name: str,
    affiliated_organization_name: str | None,
    candidates: list[CorporateEntityCandidate],
) -> str:
    """Atomically return the unique team identity for the pair.

    ``UNIQUE NULLS NOT DISTINCT`` makes NULL affiliations participate
    in the same conflict rule.  One upsert removes the prior
    read-then-insert race.
    """
    corporate_entity_id = (
        resolve_corporate_entity(affiliated_organization_name, candidates)
        if affiliated_organization_name
        else None
    )
    row = await conn.fetchrow(
        """
        insert into cataloged_team
            (team_name, affiliated_organization_name,
             affiliated_corporate_entity_id)
        values ($1, $2, $3)
        on conflict (team_name, affiliated_organization_name) do update set
            affiliated_corporate_entity_id = coalesce(
                excluded.affiliated_corporate_entity_id,
                cataloged_team.affiliated_corporate_entity_id
            )
        returning team_id
        """,
        team_name,
        affiliated_organization_name,
        corporate_entity_id,
    )
    return str(row["team_id"])
