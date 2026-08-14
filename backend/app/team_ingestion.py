"""Resolves an R&R team actor (ADR 0007's ``prov_team``) to a shared
``cataloged_team`` identity across posts -- the same catalog-then-mention
pattern ``keyman_ingestion.py`` already uses for ``cataloged_person``, so
the same "설계팀" (design team) named in two different posts becomes one
row here, not two unrelated free-text strings (ADR 0009).

Grounded in the same collective-entity-resolution framing
(Bhattacharya & Getoor, 2007) ``lineageweave.corporate_hierarchy_resolution``
already cites for the identical problem applied to organization names --
this reuses that module's candidate-matching for a team's parent
organization rather than re-deriving it.
"""

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
    """Reuse a same-(name, org) row so re-extraction does not duplicate.

    Team identity is the ``(team_name, affiliated_organization_name)``
    pair, not the bare name alone -- a name like "설계팀" (design team)
    exists at many real companies and is not, by itself, an identifiable
    entity. ``IS NOT DISTINCT FROM`` (not ``=``) so a NULL org (an
    unplaced team mention) still matches a prior NULL-org row for the
    same name, matching ``cataloged_team``'s own unique constraint.
    """
    row = await conn.fetchrow(
        "select team_id from cataloged_team "
        "where team_name = $1 and affiliated_organization_name is not distinct from $2",
        team_name,
        affiliated_organization_name,
    )
    if row is not None:
        return str(row["team_id"])

    corporate_entity_id = (
        resolve_corporate_entity(affiliated_organization_name, candidates)
        if affiliated_organization_name
        else None
    )
    row = await conn.fetchrow(
        "insert into cataloged_team (team_name, affiliated_organization_name, affiliated_corporate_entity_id) "
        "values ($1, $2, $3) returning team_id",
        team_name,
        affiliated_organization_name,
        corporate_entity_id,
    )
    return str(row["team_id"])
