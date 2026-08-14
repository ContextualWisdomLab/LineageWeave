"""Resolves an abbreviated/slang organization name to its canonical
name, caching the result in `organization_name_resolution` so the same
abbreviation (e.g. "한수원") is resolved once, not re-queried on every
mention across thousands of posts. See ADR 0008 and
`lineageweave.organization_name_resolution` for the resolve-then-verify
pipeline itself; this module is just the cache-check-then-persist
wrapper around it, the same shape as every other `*_ingestion.py` module
in this package.
"""

from __future__ import annotations

import asyncpg

from lineageweave.organization_name_resolution import (
    OrganizationNameResolutionClient,
    resolve_and_verify_organization_name,
)
from lineageweave.relation_verification import STATUS_CORROBORATED, RelationVerificationClient


async def resolve_organization_name(
    conn: asyncpg.Connection,
    resolution_client: OrganizationNameResolutionClient,
    verification_client: RelationVerificationClient,
    raw_name: str,
    context_text: str,
) -> str:
    """Returns the name to actually use for downstream entity matching:
    the corroborated canonical name when one is known (cached or freshly
    resolved+verified), otherwise `raw_name` unchanged.

    Only a `verify_corroborated` resolution is ever substituted in for
    matching purposes -- an uncorroborated or still-pending one is still
    cached (so it is not re-attempted every post), but the raw name
    keeps flowing to `resolve_corporate_entity` rather than an unverified
    guess, the same never-trust-an-unverified-guess discipline as every
    other channel in this repo.
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

    resolution = resolve_and_verify_organization_name(
        raw_name, context_text, resolution_client, verification_client
    )
    if resolution is None:
        return raw_name

    await conn.execute(
        """
        insert into organization_name_resolution
            (raw_organization_name, resolved_organization_name, verification_status_code, verification_evidence_url)
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
