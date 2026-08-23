"""Runs a `KeymanExtractionClient` over a post and persists the result:
`cataloged_person` (upserted by name + side -- the schema has no unique
constraint on person_name alone, since two different real people can
share a name, but re-running extraction on the same post should not keep
creating duplicate rows for the same extracted mention),
`person_affiliation` (N:N, matched to a real `corporate_entity` via
similarity-based resolution -- see
`lineageweave.corporate_hierarchy_resolution`, so an abbreviation or
trailing legal suffix still resolves, not just an exact string match --
plus `role_title`, a schema column that already existed and was
previously never populated by this pipeline), and `post_person_mention`.
Finishes by calling `knowledge_graph.persist_edges_for_post` so the
Knowledge Graph edges are computed from the same write, not a separate
manual step.

Same-name disambiguation: `_upsert_person`'s name+side match is a real,
known simplification (documented above), but a stated job title is real
evidence a same-name match should NOT blindly trust -- when the new
mention names a title that conflicts with a title already on file for
that name+side (both stated, genuinely different), a fresh
`cataloged_person` row is created rather than merging two people who
happen to share a name. A person's title legitimately changes over time
(a promotion), so this only splits on an actual stated conflict, never
on a missing title on either side.

Abbreviation resolution (ADR 0008): before matching against
`corporate_entity`, each affiliated organization name is run through
`organization_name_resolution_ingestion.resolve_organization_name` --
character-similarity matching alone cannot bridge an initialism like
"AGP" to its expansion "Aurora Grid Power". Only a search-corroborated
resolution is substituted in; an unresolved or unverified name still
flows through unchanged.

Hierarchy auto-creation (ADR 0010): a unseen dataset's first mention of
any new counterparty organization has no existing `corporate_entity`
candidate for similarity matching to find at all -- matching alone can
only ever locate an already-cataloged entity. `get_or_create_corporate_entity`
tries similarity matching first, then falls back to an LLM-proposed,
search-corroborated hierarchy placement (level + parent) before
creating a real new row, so the "통합 고객사 계열 tree AI" requirement
is actually populated from real extraction, not left permanently empty.

Tie boundary (ADR 0026): a raw organization name whose distinct catalog
candidates share the top qualifying similarity score stays unbound before
abbreviation rewriting. Live name resolution therefore cannot turn known
ambiguity into an apparent miss and manufacture a third `AUTO-` row.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace

import asyncpg

from lineageweave.corporate_hierarchy_inference import (
    CorporateHierarchyInferenceClient,
    NullCorporateHierarchyInferenceClient,
)
from lineageweave.corporate_hierarchy_resolution import (
    RESOLUTION_TIE,
    CorporateEntityCandidate,
    score_corporate_entity,
)
from lineageweave.keyman_extraction import KeymanExtractionClient, PersonMention
from lineageweave.organization_name_resolution import (
    NullOrganizationNameResolutionClient,
    OrganizationNameResolutionClient,
)
from lineageweave.relation_verification import NullRelationVerificationClient, RelationVerificationClient

from .corporate_entity_ingestion import get_or_create_corporate_entity, record_observed_entity
from .knowledge_graph import persist_edges_for_post
from .organization_name_resolution_ingestion import resolve_organization_name


async def _load_corporate_entity_candidates(conn: asyncpg.Connection) -> list[CorporateEntityCandidate]:
    """All cataloged orgs, so affiliation names can resolve by similarity."""
    rows = await conn.fetch("select corporate_entity_id, entity_name from corporate_entity")
    return [
        CorporateEntityCandidate(str(row["corporate_entity_id"]), row["entity_name"]) for row in rows
    ]


async def _upsert_person(conn: asyncpg.Connection, mention: PersonMention) -> str:
    """Reuse a same-name, same-side row so re-extraction does not duplicate
    -- unless the new mention's stated job title conflicts with a title
    already on file for that name+side (`last_known_job_title`, checked
    even when this mention names no affiliated organization -- a title
    is real same-name-disambiguation evidence on its own, see module
    docstring), in which case a same name is not trusted as the same
    real person.
    """
    candidates = await conn.fetch(
        "select person_id, last_known_job_title from cataloged_person "
        "where person_name = $1 and person_side_code = $2",
        mention.person_name,
        mention.person_side_code,
    )
    if candidates and mention.job_title:
        for candidate in candidates:
            on_file = candidate["last_known_job_title"]
            if on_file is not None and on_file != mention.job_title:
                continue  # stated title conflicts -- do not reuse this row
            if on_file is None:
                await conn.execute(
                    "update cataloged_person set last_known_job_title = $1 where person_id = $2",
                    mention.job_title,
                    candidate["person_id"],
                )
            return str(candidate["person_id"])
    elif candidates:
        return str(candidates[0]["person_id"])

    row = await conn.fetchrow(
        "insert into cataloged_person (person_name, person_side_code, last_known_job_title) "
        "values ($1, $2, $3) returning person_id",
        mention.person_name,
        mention.person_side_code,
        mention.job_title,
    )
    return str(row["person_id"])


async def _upsert_affiliation(
    conn: asyncpg.Connection,
    person_id: str,
    raw_name: str,
    resolved_name: str,
    corporate_entity_id: str | None,
    role_title: str | None,
) -> None:
    """Promote a raw affiliation row into one canonical identity."""
    await conn.execute(
        """
        with legacy_affiliation as (
            select affiliated_corporate_entity_id, role_title
              from person_affiliation
             where person_id = $1
               and affiliated_organization_name = $2
        ),
        canonical_affiliation as (
            insert into person_affiliation
                (person_id, affiliated_organization_name,
                 affiliated_corporate_entity_id, role_title)
            values (
                $1,
                $3,
                coalesce($4, (select affiliated_corporate_entity_id from legacy_affiliation)),
                coalesce($5, (select role_title from legacy_affiliation))
            )
            on conflict (person_id, affiliated_organization_name)
            do update set
                affiliated_corporate_entity_id = coalesce(
                    excluded.affiliated_corporate_entity_id,
                    person_affiliation.affiliated_corporate_entity_id
                ),
                role_title = coalesce(
                    excluded.role_title,
                    person_affiliation.role_title
                )
            returning person_affiliation_id
        )
        delete from person_affiliation
         where person_id = $1
           and affiliated_organization_name = $2
           and $2 <> $3
        """,
        person_id,
        raw_name,
        resolved_name,
        corporate_entity_id,
        role_title,
    )


async def _resolve_affiliated_organization(
    conn: asyncpg.Connection,
    organization_name: str,
    context_text: str,
    resolution_client: OrganizationNameResolutionClient,
    verification_client: RelationVerificationClient,
    hierarchy_inference_client: CorporateHierarchyInferenceClient,
    candidates: list[CorporateEntityCandidate],
) -> tuple[str, str, str | None]:
    """Resolve one affiliation without rewriting a known raw-name tie."""
    raw_outcome = score_corporate_entity(organization_name, candidates)
    if raw_outcome.kind == RESOLUTION_TIE:
        return organization_name, organization_name, None

    resolved_name = await resolve_organization_name(
        conn,
        resolution_client,
        verification_client,
        organization_name,
        context_text,
    )
    corporate_entity_id = await get_or_create_corporate_entity(
        conn,
        resolved_name,
        context_text,
        hierarchy_inference_client,
        verification_client,
        candidates,
    )
    return organization_name, resolved_name, corporate_entity_id


async def ingest_post_keymen(
    conn: asyncpg.Connection,
    client: KeymanExtractionClient,
    post_id: str,
    post_title: str,
    post_body: str,
    *,
    resolution_client: OrganizationNameResolutionClient | None = None,
    verification_client: RelationVerificationClient | None = None,
    hierarchy_inference_client: CorporateHierarchyInferenceClient | None = None,
    context_hints: str = "",
    persist_graph: bool = True,
) -> list[PersonMention]:
    """Extracts, persists, and returns the `PersonMention`s found in one post.

    `resolution_client`/`verification_client`/`hierarchy_inference_client`
    default to the unavailable Null clients -- callers that don't pass
    real ones get the exact same behavior as before ADR 0008/0010 (raw
    affiliation names, unresolved).

    Organization resolution and hierarchy creation finish before the Keyman
    write transaction. Callers must not wrap this function in an outer
    transaction: that would turn ``pg_advisory_xact_lock`` into a savepoint
    and hold the creation lock across later LLM work. The post's prior
    Keyman mention set is replaced atomically after enrichment.
    ``persist_graph=False`` lets a larger caller persist edges in its own
    short write transaction after this function returns.

    Raises whatever `client.extract` raises (e.g. a `NullKeymanExtractionClient`
    would raise `RuntimeError`) -- callers should check `client.available`
    first, same discipline as every other pluggable channel in this repo.
    """
    resolution_client = resolution_client or NullOrganizationNameResolutionClient()
    verification_client = verification_client or NullRelationVerificationClient()
    hierarchy_inference_client = hierarchy_inference_client or NullCorporateHierarchyInferenceClient()
    extract_with_hints = getattr(client, "extract_with_hints", None)
    if callable(extract_with_hints):
        mentions = await asyncio.to_thread(
            extract_with_hints, post_title, post_body, context_hints
        )
    else:
        mentions = await asyncio.to_thread(client.extract, post_title, post_body)
    candidates = await _load_corporate_entity_candidates(conn)
    resolved_by_mention: list[tuple[PersonMention, list[tuple[str, str, str | None]]]] = []
    for mention in mentions:
        resolved_orgs: list[tuple[str, str, str | None]] = []
        for organization_name in mention.affiliated_organization_names:
            resolved_orgs.append(
                await _resolve_affiliated_organization(
                    conn,
                    organization_name,
                    post_body,
                    resolution_client,
                    verification_client,
                    hierarchy_inference_client,
                    candidates,
                )
            )
        resolved_by_mention.append((mention, resolved_orgs))

    normalized_mentions: list[PersonMention] = []
    async with conn.transaction():
        await conn.execute(
            "delete from post_person_mention where post_id = $1", post_id
        )
        for mention, resolved_orgs in resolved_by_mention:
            person_id = await _upsert_person(conn, mention)
            await conn.execute(
                "insert into post_person_mention (post_id, person_id) values ($1, $2) on conflict do nothing",
                post_id,
                person_id,
            )
            resolved_names: list[str] = []
            for organization_name, resolved_name, corporate_entity_id in resolved_orgs:
                await _upsert_affiliation(
                    conn,
                    person_id,
                    organization_name,
                    resolved_name,
                    corporate_entity_id,
                    mention.job_title,
                )
                if corporate_entity_id is not None:
                    await record_observed_entity(conn, corporate_entity_id, post_id)
                if resolved_name not in resolved_names:
                    resolved_names.append(resolved_name)
            normalized_mentions.append(
                replace(
                    mention,
                    affiliated_organization_names=tuple(resolved_names),
                )
            )
        if persist_graph:
            await persist_edges_for_post(conn, post_id)

    return normalized_mentions
