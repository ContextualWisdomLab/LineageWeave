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

import asyncpg

from lineageweave.corporate_hierarchy_inference import (
    CorporateHierarchyInferenceClient,
    HierarchyProposal,
)
from lineageweave.corporate_hierarchy_resolution import (
    RESOLUTION_TIE,
    RESOLUTION_UNIQUE,
    CorporateEntityCandidate,
    score_corporate_entity,
)
from lineageweave.http_client import HttpClientError
from lineageweave.relation_verification import (
    STATUS_CORROBORATED,
    RelationVerificationClient,
)

from .post_eligibility import SOURCE_POST_ELIGIBILITY_SQL

_AUTO_CODE_PREFIX = "AUTO-"
_MAX_HIERARCHY_DEPTH = 4
_CREATION_LOCK_KEY = "lineageweave:corporate_entity_creation"


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

    A unique similarity match is reused. A tied top score stays unbound
    and does not create a third same-named row (ADR 0026). Only a genuine
    miss -- no candidate at or above ``min_similarity`` -- may enter ADR
    0010 inference. A proposed parent must independently corroborate and
    resolve before the child can be inserted. Repeated names in the
    recursion path are cycles, including multi-node cycles such as
    A -> B -> A.
    """
    normalized_name = organization_name.strip()
    if not normalized_name:
        return None
    visit_key = normalized_name.casefold()
    if visit_key in _visited_names:
        return None

    existing = score_corporate_entity(normalized_name, candidates)
    if existing.kind == RESOLUTION_UNIQUE and existing.catalog_id is not None:
        return existing.catalog_id
    if existing.kind == RESOLUTION_TIE:
        return None
    if _depth >= _MAX_HIERARCHY_DEPTH or not inference_client.available:
        return None

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
        return None
    if proposal is None or not verification_client.available:
        return None

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
        return None
    if placement_result.status_code != STATUS_CORROBORATED:
        return None

    visited_names = _visited_names | {visit_key}
    parent_entity_id: str | None = None
    if proposal.parent_name is not None:
        normalized_parent = proposal.parent_name.strip()
        if not normalized_parent or normalized_parent.casefold() in visited_names:
            return None
        try:
            parent_result = await asyncio.to_thread(
                verification_client.verify,
                normalized_parent,
                f"immediate parent of {normalized_name}",
            )
        except (HttpClientError, OSError):
            # Same fail-closed-without-crashing behavior as the placement
            # verification above.
            return None
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

    async with conn.transaction():
        await conn.execute(
            "select pg_advisory_xact_lock(hashtext($1))",
            _CREATION_LOCK_KEY,
        )
        # ponytail: the lock recheck is exact-only; fuzzy matching here can
        # mistake an inferred child for the parent just created above. The
        # initial lookup remains fuzzy, while this check only prevents a
        # concurrent insert of the same normalized name.
        fresh = score_corporate_entity(
            normalized_name,
            await _reload_candidates(conn),
            min_similarity=1.0,
        )
        if fresh.kind == RESOLUTION_UNIQUE and fresh.catalog_id is not None:
            _remember_candidate(candidates, fresh.catalog_id, normalized_name)
            return fresh.catalog_id
        if fresh.kind == RESOLUTION_TIE:
            return None
        new_id = await _create_entity(
            conn,
            normalized_name,
            proposal.level_code,
            parent_entity_id,
        )
        _remember_candidate(candidates, new_id, normalized_name)
        return new_id


async def record_observed_entity(
    conn: asyncpg.Connection,
    corporate_entity_id: str,
    source_post_id: str,
) -> None:
    """Upsert one ``account_observed_entity`` row per account this post's own
    ABAC predicate already authorizes to read it (ADR 0144).

    Mirrors ``read_customer_master``'s own eligibility predicate exactly --
    public-or-own-corp, gated by ``SOURCE_POST_ELIGIBILITY_SQL`` -- so the
    two call sites cannot silently drift. An account's own-corp affiliation
    is preferred as ``granting_corporate_entity_id``; an account that can
    only read this post because it is public (no affiliation to the post's
    own entity) still records one of its other live affiliations instead,
    since public visibility does not require any specific affiliation.
    """
    # Safe SQL: the eligibility predicate is an immutable schema fragment; ids are bound.
    await conn.execute(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        f"""
        insert into account_observed_entity (
            account_id, corporate_entity_id, granting_corporate_entity_id, source_post_id
        )
        select distinct on (affiliation.user_account_id)
               affiliation.user_account_id, $1::uuid, affiliation.corporate_entity_id, $2::uuid
          from source_post post
          join account_affiliation affiliation on true
         where post.post_id = $2
           and (post.visibility_code = 'public'
                or affiliation.corporate_entity_id = post.corporate_entity_id)
           and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}
         order by affiliation.user_account_id,
                  (affiliation.corporate_entity_id = post.corporate_entity_id) desc
        on conflict (account_id, corporate_entity_id) do update
           set granting_corporate_entity_id = excluded.granting_corporate_entity_id,
               source_post_id = excluded.source_post_id,
               last_observed_at = now(),
               observation_count = account_observed_entity.observation_count + 1
        """,
        corporate_entity_id,
        source_post_id,
    )


async def prune_observed_entity_for_posts(
    conn: asyncpg.Connection,
    source_post_ids: list[str],
) -> None:
    """Delete stale ``account_observed_entity`` rows after a post's own
    ``corporate_entity_id``/eligibility narrows (ADR 0144 reconciliation).

    Called inline, in the same transaction as the mutation that can narrow
    a post's authorized-account set (currently: the corporate_entity_id
    reassignment in ``customer_hint_ingestion.py``). A row survives only
    if some *other* still-eligible post also observed that
    (account, corporate_entity) pair through the same account -- deleting
    and re-deriving is simpler and no less correct than trying to patch
    ``granting_corporate_entity_id``/``source_post_id`` in place, since a
    later ``get_or_create_corporate_entity`` call naturally re-inserts any
    row that is genuinely still observed.
    """
    if not source_post_ids:
        return
    await conn.execute(
        """
        delete from account_observed_entity observed
         where observed.source_post_id = any($1::uuid[])
           and not exists (
               select 1
                 from source_post post
                 join account_affiliation affiliation
                   on affiliation.user_account_id = observed.account_id
                where post.post_id = observed.source_post_id
                  and (post.visibility_code = 'public'
                       or affiliation.corporate_entity_id = post.corporate_entity_id)
           )
        """,
        source_post_ids,
    )
