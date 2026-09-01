
"""Cache and persist verified organization-name normalization."""

from __future__ import annotations

import asyncio

import asyncpg

from lineageweave.organization_alias import OrganizationNameAlias
from lineageweave.organization_name_resolution import (
    OrganizationNameResolutionClient,
    resolve_and_verify_organization_name,
)
from lineageweave.corporate_hierarchy_resolution import (
    OrganizationNameAlias as CorporateHierarchyOrganizationNameAlias,
)
from lineageweave.relation_verification import (
    STATUS_CORROBORATED,
    RelationVerificationClient,
)

_CORROBORATED_ALIAS_SQL = (
    "select raw_organization_name, resolved_organization_name "
    "from organization_name_resolution "
    "where verification_status_code = $1"
)


async def load_corroborated_organization_name_aliases(
    conn: asyncpg.Connection,
) -> list[CorporateHierarchyOrganizationNameAlias]:
    """Return search-corroborated SKOS alt/pref pairs, or an empty list.

    Callers with a stub connection that has no ``fetch`` (the early-return
    tie tests) get no aliases rather than raising. Only
    ``verify_corroborated`` rows are returned; pending or uncorroborated
    guesses must not bind catalog identities (ADR 0008).
    """
    fetch = getattr(conn, "fetch", None)
    if not callable(fetch):
        return []
    rows = await fetch(_CORROBORATED_ALIAS_SQL, STATUS_CORROBORATED)
    aliases: list[CorporateHierarchyOrganizationNameAlias] = []
    for row in rows:
        aliases.append(
            CorporateHierarchyOrganizationNameAlias(
                alt_label=row["raw_organization_name"],
                pref_label=row["resolved_organization_name"],
            )
        )
    return aliases


async def resolve_organization_name(
    conn: asyncpg.Connection,
    resolution_client: OrganizationNameResolutionClient,
    verification_client: RelationVerificationClient,
    raw_name: str,
    context_text: str,
) -> str:
    """Return the corroborated canonical name, otherwise ``raw_name``.

    Synchronous network adapters run in a worker thread so this async
    ingestion path does not block unrelated requests.
    """
    cached = await conn.fetchrow(
        "select resolved_organization_name, verification_status_code "
        "from organization_name_resolution where raw_organization_name = $1",
        raw_name,
    )
    if cached is not None:
        if cached["verification_status_code"] == STATUS_CORROBORATED:
            return cached["resolved_organization_name"]
        return raw_name
    if not resolution_client.available:
        return raw_name

    resolution = await asyncio.to_thread(
        resolve_and_verify_organization_name,
        raw_name,
        context_text,
        resolution_client,
        verification_client,
    )
    if resolution is None:
        return raw_name

    await conn.execute(
        """
        insert into organization_name_resolution
            (raw_organization_name, resolved_organization_name,
             verification_status_code, verification_evidence_url)
        values ($1, $2, $3, $4)
        on conflict (raw_organization_name) do update set
            resolved_organization_name = excluded.resolved_organization_name,
            verification_status_code = excluded.verification_status_code,
            verification_evidence_url = excluded.verification_evidence_url,
            resolved_at = now()
        """,
        resolution.raw_organization_name,
        resolution.resolved_organization_name,
        resolution.verification_status_code,
        resolution.verification_evidence_url,
    )
    if resolution.verification_status_code == STATUS_CORROBORATED:
        return resolution.resolved_organization_name
    return raw_name


async def fetch_corroborated_organization_aliases(
    conn: asyncpg.Connection,
    *,
    organization_names: tuple[str, ...] | None = None,
) -> tuple[OrganizationNameAlias, ...]:
    """Load corroborated aliases, optionally bounded to observed names.

    ``organization_names`` narrows the resolution rows and catalog-name join
    before they enter application memory. Callers that need the complete
    corroborated alias catalog may omit it and retain the existing behavior.
    Pending and uncorroborated rows stay out, and same-named catalog rows fail
    closed with a null target id.
    """
    if organization_names is None:
        rows = await conn.fetch(
            """
            select resolution.raw_organization_name,
                   resolution.resolved_organization_name,
                   case when count(distinct entity.corporate_entity_id) = 1
                        then min(entity.corporate_entity_id::text)
                        else null
                   end as corporate_entity_id
            from organization_name_resolution as resolution
            left join corporate_entity as entity
              on entity.entity_name = resolution.raw_organization_name
              or entity.entity_name = resolution.resolved_organization_name
            where resolution.verification_status_code = $1
            group by resolution.raw_organization_name,
                     resolution.resolved_organization_name
            """,
            STATUS_CORROBORATED,
        )
    else:
        names = sorted({name.strip() for name in organization_names if name.strip()})
        if not names:
            return ()
        rows = await conn.fetch(
            """
            select resolution.raw_organization_name,
                   resolution.resolved_organization_name,
                   case when count(distinct entity.corporate_entity_id) = 1
                        then min(entity.corporate_entity_id::text)
                        else null
                   end as corporate_entity_id
            from organization_name_resolution as resolution
            left join corporate_entity as entity
              on entity.entity_name = resolution.raw_organization_name
              or entity.entity_name = resolution.resolved_organization_name
            where resolution.verification_status_code = $1
              and (
                  resolution.raw_organization_name = any($2::text[])
                  or resolution.resolved_organization_name = any($2::text[])
              )
            group by resolution.raw_organization_name,
                     resolution.resolved_organization_name
            """,
            STATUS_CORROBORATED,
            names,
        )
    return tuple(
        OrganizationNameAlias(
            alt_label=row["raw_organization_name"],
            pref_label=row["resolved_organization_name"],
            corporate_entity_id=(
                str(row["corporate_entity_id"])
                if row["corporate_entity_id"] is not None
                else None
            ),
        )
        for row in rows
    )
