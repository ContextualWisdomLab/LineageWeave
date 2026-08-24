
"""Cache and persist verified organization-name normalization."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import asyncpg

from lineageweave.organization_name_resolution import (
    OrganizationNameResolution,
    OrganizationNameResolutionClient,
    resolve_and_verify_organization_name,
)
from lineageweave.corporate_hierarchy_resolution import OrganizationNameAlias
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
) -> list[OrganizationNameAlias]:
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
    aliases: list[OrganizationNameAlias] = []
    for row in rows:
        aliases.append(
            OrganizationNameAlias(
                alt_label=row["raw_organization_name"],
                pref_label=row["resolved_organization_name"],
            )
        )
    return aliases


@dataclass(frozen=True)
class PreparedOrganizationNameResolution:
    """Effective name plus an optional verified cache row awaiting apply."""

    resolved_name: str
    resolution: OrganizationNameResolution | None


async def prepare_organization_name_resolution(
    conn: asyncpg.Connection,
    resolution_client: OrganizationNameResolutionClient,
    verification_client: RelationVerificationClient,
    raw_name: str,
    context_text: str,
) -> PreparedOrganizationNameResolution:
    """Resolve and verify a name without mutating the shared cache.

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
            return PreparedOrganizationNameResolution(
                cached["resolved_organization_name"],
                None,
            )
        return PreparedOrganizationNameResolution(raw_name, None)
    if not resolution_client.available:
        return PreparedOrganizationNameResolution(raw_name, None)

    resolution = await asyncio.to_thread(
        resolve_and_verify_organization_name,
        raw_name,
        context_text,
        resolution_client,
        verification_client,
    )
    if resolution is None:
        return PreparedOrganizationNameResolution(raw_name, None)

    return PreparedOrganizationNameResolution(
        (
            resolution.resolved_organization_name
            if resolution.verification_status_code == STATUS_CORROBORATED
            else raw_name
        ),
        resolution,
    )


async def apply_prepared_organization_name_resolution(
    conn: asyncpg.Connection,
    prepared: PreparedOrganizationNameResolution,
) -> str:
    """Persist a prepared cache row without making provider calls."""
    resolution = prepared.resolution
    if resolution is None:
        return prepared.resolved_name

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
    return prepared.resolved_name


async def resolve_organization_name(
    conn: asyncpg.Connection,
    resolution_client: OrganizationNameResolutionClient,
    verification_client: RelationVerificationClient,
    raw_name: str,
    context_text: str,
) -> str:
    """Prepare provider evidence, then persist and return the effective name."""
    prepared = await prepare_organization_name_resolution(
        conn,
        resolution_client,
        verification_client,
        raw_name,
        context_text,
    )
    return await apply_prepared_organization_name_resolution(conn, prepared)
