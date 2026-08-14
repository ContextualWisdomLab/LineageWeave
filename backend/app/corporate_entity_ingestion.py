
"""Resolve an organization mention to the corporate hierarchy catalog.

Existing similarity matches are reused.  A previously unseen entity is
created only after inference proposes its complete hierarchy placement
and external verification corroborates that placement.  Parent failure,
cycles, and excessive depth all fail closed.  See ADR 0010.
"""

from __future__ import annotations

import asyncio
import hashlib

import asyncpg

from lineageweave.corporate_hierarchy_inference import (
    CorporateHierarchyInferenceClient,
    HierarchyProposal,
)
from lineageweave.corporate_hierarchy_resolution import (
    CorporateEntityCandidate,
    resolve_corporate_entity,
)
from lineageweave.relation_verification import (
    STATUS_CORROBORATED,
    RelationVerificationClient,
)

_AUTO_CODE_PREFIX = "AUTO-"
_MAX_HIERARCHY_DEPTH = 4


def _auto_entity_code(organization_name: str) -> str:
    """Return a deterministic, namespace-separated code."""
    digest = hashlib.sha256(organization_name.encode("utf-8")).hexdigest()[:16]
    return f"{_AUTO_CODE_PREFIX}{digest}"


def _hierarchy_verification_label(proposal: HierarchyProposal) -> str:
    """Describe every persisted hierarchy field in one claim."""
    parent = proposal.parent_name if proposal.parent_name is not None else "NO_PARENT"
    return f"corporate hierarchy level={proposal.level_code}; immediate_parent={parent}"


async def _create_entity(
    conn: asyncpg.Connection,
    organization_name: str,
    level_code: str,
    parent_entity_id: str | None,
) -> str:
    """Insert one entity atomically and return its catalog id."""
    row = await conn.fetchrow(
        """
        insert into corporate_entity
            (parent_entity_id, corporate_entity_code, entity_name, entity_level_code)
        values ($1, $2, $3, $4)
        on conflict (corporate_entity_code) do update set
            entity_name = excluded.entity_name,
            entity_level_code = excluded.entity_level_code,
            parent_entity_id = excluded.parent_entity_id
        returning corporate_entity_id
        """,
        parent_entity_id,
        _auto_entity_code(organization_name),
        organization_name,
        level_code,
    )
    return str(row["corporate_entity_id"])


async def get_or_create_corporate_entity(
    conn: asyncpg.Connection,
    organization_name: str,
    context_text: str,
    inference_client: CorporateHierarchyInferenceClient,
    verification_client: RelationVerificationClient,
    candidates: list[CorporateEntityCandidate],
    *,
    _depth: int = 0,
    _visited_names: frozenset[str] = frozenset(),
) -> str | None:
    """Return a verified catalog id, otherwise ``None``.

    A proposed parent must independently corroborate and resolve before
    the child can be inserted.  Repeated names in the recursion path are
    cycles, including multi-node cycles such as A -> B -> A.
    """
    normalized_name = organization_name.strip()
    if not normalized_name:
        return None
    visit_key = normalized_name.casefold()
    if visit_key in _visited_names:
        return None

    existing_id = resolve_corporate_entity(normalized_name, candidates)
    if existing_id is not None:
        return existing_id
    if _depth >= _MAX_HIERARCHY_DEPTH or not inference_client.available:
        return None

    proposal = await asyncio.to_thread(
        inference_client.infer,
        normalized_name,
        context_text,
    )
    if proposal is None or not verification_client.available:
        return None

    placement_result = await asyncio.to_thread(
        verification_client.verify,
        normalized_name,
        _hierarchy_verification_label(proposal),
    )
    if placement_result.status_code != STATUS_CORROBORATED:
        return None

    visited_names = _visited_names | {visit_key}
    parent_entity_id: str | None = None
    if proposal.parent_name is not None:
        normalized_parent = proposal.parent_name.strip()
        if not normalized_parent or normalized_parent.casefold() in visited_names:
            return None
        parent_result = await asyncio.to_thread(
            verification_client.verify,
            normalized_parent,
            f"immediate parent of {normalized_name}",
        )
        if parent_result.status_code != STATUS_CORROBORATED:
            return None
        parent_entity_id = await get_or_create_corporate_entity(
            conn,
            normalized_parent,
            context_text,
            inference_client,
            verification_client,
            candidates,
            _depth=_depth + 1,
            _visited_names=visited_names,
        )
        if parent_entity_id is None:
            return None

    new_id = await _create_entity(
        conn,
        normalized_name,
        proposal.level_code,
        parent_entity_id,
    )
    candidates.append(
        CorporateEntityCandidate(
            corporate_entity_id=new_id,
            entity_name=normalized_name,
        )
    )
    return new_id
