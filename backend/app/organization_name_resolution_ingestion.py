
"""Cache and persist verified organization-name normalization."""

from __future__ import annotations

import asyncio
import hashlib

import asyncpg

from lineageweave.organization_name_resolution import (
    OrganizationNameResolutionClient,
    resolve_and_verify_organization_name,
)
from lineageweave.relation_verification import (
    STATUS_CORROBORATED,
    RelationVerificationClient,
)


def _context_sha256(context_text: str) -> str:
    """Return the cache key for context without persisting the source body."""
    return hashlib.sha256(context_text.encode("utf-8")).hexdigest()


async def resolve_organization_name(
    conn: asyncpg.Connection,
    resolution_client: OrganizationNameResolutionClient,
    verification_client: RelationVerificationClient,
    raw_name: str,
    context_text: str,
) -> str:
    """Return the corroborated canonical name, otherwise ``raw_name``.

    The cache is scoped by the exact post context. A raw abbreviation is not
    globally unambiguous, and only the digest is stored so the source body is
    not duplicated in the resolution cache. Synchronous network adapters run
    in a worker thread so this async ingestion path does not block unrelated
    requests.
    """
    context_sha256 = _context_sha256(context_text)
    cached = await conn.fetchrow(
        "select resolved_organization_name, verification_status_code "
        "from organization_name_resolution "
        "where raw_organization_name = $1 and context_sha256 = $2",
        raw_name,
        context_sha256,
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
            (raw_organization_name, context_sha256, resolved_organization_name,
             verification_status_code, verification_evidence_url)
        values ($1, $2, $3, $4, $5)
        on conflict (raw_organization_name, context_sha256) do update set
            resolved_organization_name = excluded.resolved_organization_name,
            verification_status_code = excluded.verification_status_code,
            verification_evidence_url = excluded.verification_evidence_url,
            resolved_at = now()
        """,
        resolution.raw_organization_name,
        context_sha256,
        resolution.resolved_organization_name,
        resolution.verification_status_code,
        resolution.verification_evidence_url,
    )
    if resolution.verification_status_code == STATUS_CORROBORATED:
        return resolution.resolved_organization_name
    return raw_name
