"""Resolves an organization name to a real ``corporate_entity`` row,
creating one when no existing candidate matches -- the missing half of
the standing "통합 고객사 계열 tree AI" (integrated customer affiliate
tree) requirement:
:mod:`lineageweave.corporate_hierarchy_resolution`'s similarity
matching only ever finds an ALREADY-cataloged entity, so a real
dataset's first mention of any new counterparty organization (the
overwhelming majority of real R&R/affiliation mentions -- confirmed via
a real Milestone 2 count: 0 of 4,154 person affiliations and 0 of 9,852
R&R organization mentions resolved before this module existed) stayed
permanently unresolved. See ADR 0010.
"""

from __future__ import annotations

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
from lineageweave.relation_verification import STATUS_CORROBORATED, RelationVerificationClient

# A newly-created entity's corporate_entity_code must never collide with
# a REAL login corp code (docker/keycloak/realm-export.json's corp_code
# claim reads this same column) -- this prefix keeps the auto-created
# counterparty namespace visibly and structurally separate.
_AUTO_CODE_PREFIX = "AUTO-"

# Bounded, not unbounded recursion up the parent chain -- a
# misbehaving/adversarial LLM response chaining parent -> parent forever
# must not spin this into an infinite loop or an unbounded fan-out of
# rows for one post.
_MAX_HIERARCHY_DEPTH = 4


def _auto_entity_code(organization_name: str) -> str:
    """A stable, unique-enough code for a newly-created entity.

    Deterministic (same name -> same code) so a concurrent duplicate
    insert attempt collides on the real `unique` constraint rather than
    creating two rows for the same name under two different codes.
    """
    digest = hashlib.sha256(organization_name.encode("utf-8")).hexdigest()[:16]
    return f"{_AUTO_CODE_PREFIX}{digest}"


async def _create_entity(
    conn: asyncpg.Connection,
    organization_name: str,
    level_code: str,
    parent_entity_id: str | None,
) -> str:
    """Insert one new corporate_entity row, tolerant of a concurrent
    duplicate insert for the same name (on conflict, re-select rather
    than error) -- real concurrent extraction across many posts can
    propose creating the same new organization at the same time.
    """
    code = _auto_entity_code(organization_name)
    row = await conn.fetchrow(
        """
        insert into corporate_entity (parent_entity_id, corporate_entity_code, entity_name, entity_level_code)
        values ($1, $2, $3, $4)
        on conflict (corporate_entity_code) do update set entity_name = excluded.entity_name
        returning corporate_entity_id
        """,
        parent_entity_id,
        code,
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
) -> str | None:
    """Returns a real ``corporate_entity_id`` for ``organization_name``:
    an existing similarity match when one clears the threshold,
    otherwise a newly-created row once the LLM's proposed hierarchy
    placement is search-corroborated. Returns ``None`` -- never a
    fabricated id -- when nothing resolves and nothing can be safely
    created (inference/verification unavailable, uncorroborated, or the
    depth bound is hit).

    Recurses up the parent chain (bounded by ``_MAX_HIERARCHY_DEPTH``)
    so a plant's proposed parent company is itself resolved/created
    before the plant row is inserted, giving the whole chain real
    ``parent_entity_id`` links rather than orphaned single-level rows.
    """
    existing_id = resolve_corporate_entity(organization_name, candidates)
    if existing_id is not None:
        return existing_id

    if _depth >= _MAX_HIERARCHY_DEPTH or not inference_client.available:
        return None

    proposal: HierarchyProposal | None = inference_client.infer(organization_name, context_text)
    if proposal is None:
        return None

    if not verification_client.available:
        return None
    result = verification_client.verify(organization_name, "organization")
    if result.status_code != STATUS_CORROBORATED:
        return None

    parent_entity_id: str | None = None
    if proposal.parent_name is not None and proposal.parent_name != organization_name:
        parent_entity_id = await get_or_create_corporate_entity(
            conn,
            proposal.parent_name,
            context_text,
            inference_client,
            verification_client,
            candidates,
            _depth=_depth + 1,
        )

    new_id = await _create_entity(conn, organization_name, proposal.level_code, parent_entity_id)
    candidates.append(CorporateEntityCandidate(corporate_entity_id=new_id, entity_name=organization_name))
    return new_id
