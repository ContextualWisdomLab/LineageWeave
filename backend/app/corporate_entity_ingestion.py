"""Resolve an organization mention to the corporate hierarchy catalog.

Existing unique similarity matches are reused. A tied top score stays
unbound and does not create a row (ADR 0026). A previously unseen entity
-- no candidate at or above the similarity threshold -- is created only
after inference proposes its complete hierarchy placement and external
verification corroborates that placement. Parent failure, cycles, and
excessive depth all fail closed. See ADR 0010.

Creation writes take one named Postgres advisory transaction lock
(``pg_advisory_xact_lock``) after network inference/verification, then
reload catalog candidates before inserting. See ADR 0012.
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass

from collections.abc import Sequence

import asyncpg

from lineageweave.corporate_hierarchy_inference import (
    CorporateHierarchyInferenceClient,
    HierarchyProposal,
)
from lineageweave.corporate_hierarchy_resolution import (
    RESOLUTION_TIE,
    RESOLUTION_UNIQUE,
    CorporateEntityCandidate,
    OrganizationNameAlias,
    expand_candidates_with_skos_aliases,
    score_corporate_entity,
)
from lineageweave.http_client import HttpClientError
from lineageweave.relation_verification import (
    STATUS_CORROBORATED,
    RelationVerificationClient,
)

from .organization_name_resolution_ingestion import (
    load_corroborated_organization_name_aliases,
)

_AUTO_CODE_PREFIX = "AUTO-"
_MAX_HIERARCHY_DEPTH = 4
_CREATION_LOCK_KEY = "lineageweave:corporate_entity_creation"


@dataclass(frozen=True)
class PreparedCorporateEntityResolution:
    """Provider-complete corporate resolution plan with no database writes."""

    normalized_name: str
    catalog_id: str | None
    unresolved_reason: str | None
    proposal: HierarchyProposal | None
    parent: PreparedCorporateEntityResolution | None


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


async def _reload_candidates(conn: asyncpg.Connection) -> list[CorporateEntityCandidate]:
    """Read every cataloged entity after the creation lock is held."""
    rows = await conn.fetch("select corporate_entity_id, entity_name from corporate_entity")
    return [
        CorporateEntityCandidate(str(row["corporate_entity_id"]), row["entity_name"])
        for row in rows
    ]


def _remember_candidate(
    candidates: list[CorporateEntityCandidate],
    corporate_entity_id: str,
    entity_name: str,
) -> None:
    """Keep the caller's in-memory snapshot aligned with a resolved id."""
    if any(candidate.corporate_entity_id == corporate_entity_id for candidate in candidates):
        return
    candidates.append(
        CorporateEntityCandidate(
            corporate_entity_id=corporate_entity_id,
            entity_name=entity_name,
        )
    )


async def prepare_corporate_entity_resolution(
    organization_name: str,
    context_text: str,
    inference_client: CorporateHierarchyInferenceClient,
    verification_client: RelationVerificationClient,
    candidates: list[CorporateEntityCandidate],
    *,
    aliases: Sequence[OrganizationNameAlias] | None = None,
    _depth: int = 0,
    _visited_names: frozenset[str] = frozenset(),
) -> PreparedCorporateEntityResolution:
    """Run scoring and provider checks without mutating the catalog.

    The frozen result can be applied only after a caller's own current-input
    fence. A unique similarity match is reused. A tied top score stays
    unbound and does not create a third same-named row (ADR 0026). After a
    raw miss, SKOS alt/pref pairs expand the candidate labels so a
    synthetic short form and full form bind the same row (ADR 0160); only
    an alias-expanded miss may enter ADR 0010 inference. A tie remains
    terminal and parent chains remain bounded exactly as in ADR 0010/0026.
    """
    normalized_name = organization_name.strip()
    if not normalized_name:
        return PreparedCorporateEntityResolution("", None, None, None, None)
    visit_key = normalized_name.casefold()
    if visit_key in _visited_names:
        return PreparedCorporateEntityResolution(
            normalized_name, None, None, None, None
        )

    existing = score_corporate_entity(normalized_name, candidates)
    if existing.kind == RESOLUTION_UNIQUE and existing.catalog_id is not None:
        return PreparedCorporateEntityResolution(
            normalized_name, existing.catalog_id, None, None, None
        )
    if existing.kind == RESOLUTION_TIE:
        return PreparedCorporateEntityResolution(
            normalized_name, None, "reason_tied_candidates", None, None
        )

    # No conn here by design (provider-only phase) -- a caller with a real
    # connection loads corroborated aliases once and passes them down; an
    # absent aliases argument means "expand with nothing" rather than a
    # lazy per-call database read from a phase that must not write or read.
    resolved_aliases: Sequence[OrganizationNameAlias] = aliases if aliases is not None else []
    existing = score_corporate_entity(
        normalized_name,
        expand_candidates_with_skos_aliases(candidates, resolved_aliases),
        min_similarity=1.0,
    )
    if existing.kind == RESOLUTION_UNIQUE and existing.catalog_id is not None:
        return PreparedCorporateEntityResolution(
            normalized_name, existing.catalog_id, None, None, None
        )
    if existing.kind == RESOLUTION_TIE:
        return PreparedCorporateEntityResolution(
            normalized_name, None, "reason_tied_candidates", None, None
        )
    if _depth >= _MAX_HIERARCHY_DEPTH or not inference_client.available:
        # Excessive recursion depth is folded into the same "not attempted"
        # bucket as an unconfigured client: from the reader's perspective
        # both mean enrichment never ran for this specific mention.
        return PreparedCorporateEntityResolution(
            normalized_name, None, "reason_no_live_client", None, None
        )

    try:
        proposal = await asyncio.to_thread(
            inference_client.infer,
            normalized_name,
            context_text,
        )
    except (HttpClientError, OSError, TimeoutError):
        # A provider timeout is an unavailable enrichment channel, not a
        # reason to discard the source-grounded summary. Keep the actor
        # unbound and let an explicit retry attempt catalog enrichment later.
        return PreparedCorporateEntityResolution(
            normalized_name, None, "reason_no_live_client", None, None
        )
    if proposal is None:
        return PreparedCorporateEntityResolution(
            normalized_name, None, "reason_not_corroborated", None, None
        )
    if not verification_client.available:
        return PreparedCorporateEntityResolution(
            normalized_name, None, "reason_no_live_client", None, None
        )

    try:
        placement_result = await asyncio.to_thread(
            verification_client.verify,
            normalized_name,
            _hierarchy_verification_label(proposal),
        )
    except (HttpClientError, OSError):
        # A transient search-provider failure (DNS, timeout, non-2xx) here
        # must not crash the caller (extract-keymen / post summary
        # ingestion) -- treat it the same as "not corroborated this run":
        # the entity simply isn't auto-created, same conservative outcome
        # as a real search that found nothing.
        return PreparedCorporateEntityResolution(
            normalized_name, None, "reason_no_live_client", None, None
        )
    if placement_result.status_code != STATUS_CORROBORATED:
        return PreparedCorporateEntityResolution(
            normalized_name, None, "reason_not_corroborated", None, None
        )

    visited_names = _visited_names | {visit_key}
    parent_plan: PreparedCorporateEntityResolution | None = None
    if proposal.parent_name is not None:
        normalized_parent = proposal.parent_name.strip()
        if not normalized_parent or normalized_parent.casefold() in visited_names:
            return PreparedCorporateEntityResolution(
                normalized_name, None, "reason_not_corroborated", None, None
            )
        try:
            parent_result = await asyncio.to_thread(
                verification_client.verify,
                normalized_parent,
                f"immediate parent of {normalized_name}",
            )
        except (HttpClientError, OSError):
            # Same fail-closed-without-crashing behavior as the placement
            # verification above.
            return PreparedCorporateEntityResolution(
                normalized_name, None, "reason_no_live_client", None, None
            )
        if parent_result.status_code != STATUS_CORROBORATED:
            return PreparedCorporateEntityResolution(
                normalized_name, None, "reason_not_corroborated", None, None
            )
        parent_plan = await prepare_corporate_entity_resolution(
            normalized_parent,
            context_text,
            inference_client,
            verification_client,
            candidates,
            aliases=resolved_aliases,
            _depth=_depth + 1,
            _visited_names=visited_names,
        )
        if parent_plan.catalog_id is None and parent_plan.proposal is None:
            # The child's own corroboration succeeded; it's the hierarchy
            # placement (ADR 0010 requires the whole chain) that didn't.
            return PreparedCorporateEntityResolution(
                normalized_name, None, "reason_not_corroborated", None, None
            )

    return PreparedCorporateEntityResolution(
        normalized_name,
        None,
        None,
        proposal,
        parent_plan,
    )


async def apply_prepared_corporate_entity_resolution(
    conn: asyncpg.Connection,
    prepared: PreparedCorporateEntityResolution,
    candidates: list[CorporateEntityCandidate],
    *,
    _resolved_parent_ids: set[str] | None = None,
) -> tuple[str | None, str | None]:
    """Apply a provider-complete plan using database work only."""
    resolved_parent_ids = (
        _resolved_parent_ids if _resolved_parent_ids is not None else set()
    )
    if prepared.catalog_id is not None or prepared.proposal is None:
        if prepared.catalog_id is not None:
            resolved_parent_ids.add(prepared.catalog_id)
        return prepared.catalog_id, prepared.unresolved_reason

    parent_entity_id: str | None = None
    if prepared.parent is not None:
        parent_entity_id, _parent_reason = (
            await apply_prepared_corporate_entity_resolution(
                conn,
                prepared.parent,
                candidates,
                _resolved_parent_ids=resolved_parent_ids,
            )
        )
        if parent_entity_id is None:
            return None, "reason_not_corroborated"
        resolved_parent_ids.add(parent_entity_id)

    evolving = score_corporate_entity(
        prepared.normalized_name,
        [
            candidate
            for candidate in candidates
            if candidate.corporate_entity_id not in resolved_parent_ids
        ],
    )
    if evolving.kind == RESOLUTION_UNIQUE and evolving.catalog_id is not None:
        resolved_parent_ids.add(evolving.catalog_id)
        return evolving.catalog_id, None
    if evolving.kind == RESOLUTION_TIE:
        return None, "reason_tied_candidates"

    async with conn.transaction():
        await conn.execute(
            "select pg_advisory_xact_lock(hashtext($1))",
            _CREATION_LOCK_KEY,
        )
        # ponytail: exclude the resolved ancestor path before repeating normal
        # raw scoring, or an ancestor created by this recursion can absorb its
        # own child. The recheck stays fuzzy (matching the initial lookup) so
        # a tie only discovered after reload still blocks a duplicate AUTO
        # row instead of silently falling through to creation.
        fresh_candidates = await _reload_candidates(conn)
        if resolved_parent_ids:
            fresh_candidates = [
                candidate
                for candidate in fresh_candidates
                if candidate.corporate_entity_id not in resolved_parent_ids
            ]
        fresh = score_corporate_entity(
            prepared.normalized_name,
            fresh_candidates,
        )
        if fresh.kind == RESOLUTION_UNIQUE and fresh.catalog_id is not None:
            _remember_candidate(candidates, fresh.catalog_id, prepared.normalized_name)
            resolved_parent_ids.add(fresh.catalog_id)
            return fresh.catalog_id, None
        if fresh.kind == RESOLUTION_TIE:
            return None, "reason_tied_candidates"
        fresh_aliases = await load_corroborated_organization_name_aliases(conn)
        fresh = score_corporate_entity(
            prepared.normalized_name,
            expand_candidates_with_skos_aliases(fresh_candidates, fresh_aliases),
            min_similarity=1.0,
        )
        if fresh.kind == RESOLUTION_UNIQUE and fresh.catalog_id is not None:
            _remember_candidate(candidates, fresh.catalog_id, prepared.normalized_name)
            resolved_parent_ids.add(fresh.catalog_id)
            return fresh.catalog_id, None
        if fresh.kind == RESOLUTION_TIE:
            return None, "reason_tied_candidates"
        new_id = await _create_entity(
            conn,
            prepared.normalized_name,
            prepared.proposal.level_code,
            parent_entity_id,
        )
        _remember_candidate(candidates, new_id, prepared.normalized_name)
        resolved_parent_ids.add(new_id)
        return new_id, None


async def get_or_create_corporate_entity(
    conn: asyncpg.Connection,
    organization_name: str,
    context_text: str,
    inference_client: CorporateHierarchyInferenceClient,
    verification_client: RelationVerificationClient,
    candidates: list[CorporateEntityCandidate],
    *,
    aliases: Sequence[OrganizationNameAlias] | None = None,
    _depth: int = 0,
    _visited_names: frozenset[str] = frozenset(),
) -> tuple[str | None, str | None]:
    """Prepare provider evidence, then resolve or create the catalog row.

    ``aliases`` defaults to a fresh load from the shared corroborated-alias
    cache -- unlike the no-conn preparation phase, this wrapper has a real
    connection, so callers that don't already have a loaded alias list get
    the same SKOS alt/pref expansion without an extra round trip of their own.
    """
    resolved_aliases = (
        aliases if aliases is not None else await load_corroborated_organization_name_aliases(conn)
    )
    prepared = await prepare_corporate_entity_resolution(
        organization_name,
        context_text,
        inference_client,
        verification_client,
        candidates,
        aliases=resolved_aliases,
        _depth=_depth,
        _visited_names=_visited_names,
    )
    return await apply_prepared_corporate_entity_resolution(conn, prepared, candidates)
