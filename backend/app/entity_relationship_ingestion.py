"""Runs an `EntityRelationshipClient` over a post's already-known
organization names (typically the union of Keyman affiliations from
`keyman_ingestion.ingest_post_keymen`) and persists the classification to
`post_counterparty_entity`.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping, Sequence
from typing import Any

import asyncpg

from lineageweave.corporate_hierarchy_resolution import (
    CorporateEntityCandidate,
    resolve_corporate_entity,
)
from lineageweave.entity_relationship_classification import (
    EntityRelationshipClient,
    OrganizationRelationship,
)
from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL

#: Same cap as read_customer_master()'s other observed-evidence lists
#: (source_customer_hints / source_author_hints) -- a bound on rows
#: returned to the API, independent of the frontend's own render cap.
_RELATIONSHIP_NETWORK_LIMIT = 100


async def ingest_post_entity_relationships(
    conn: asyncpg.Connection,
    client: EntityRelationshipClient,
    post_id: str,
    post_title: str,
    post_body: str,
    organization_names: list[str],
) -> list[OrganizationRelationship]:
    """Classifies and persists each named organization's relationship to
    the post author's org. Raises whatever `client.classify` raises (a
    `NullEntityRelationshipClient` raises `RuntimeError`) -- callers
    should check `client.available` first, same discipline as every other
    pluggable channel in this repo.
    """
    if not organization_names:
        return []

    relationships = await asyncio.to_thread(
        client.classify, post_title, post_body, organization_names
    )

    for relationship in relationships:
        await conn.execute(
            """
            insert into post_counterparty_entity (post_id, counterparty_entity_name, relationship_type_code)
            values ($1, $2, $3)
            on conflict (post_id, counterparty_entity_name)
            do update set
                relationship_type_code = excluded.relationship_type_code,
                -- A re-classification invalidates any prior verification --
                -- that search was run against the OLD relationship_label,
                -- see relation_verification.py.
                verification_status_code = 'verify_pending',
                verification_evidence_url = null,
                verification_evidence_post_id = null,
                verification_checked_at = null
            """,
            post_id,
            relationship.organization_name,
            relationship.relationship_type_code,
        )

    return relationships


def attach_resolved_entity_ids(
    rows: Sequence[Mapping[str, Any]],
    candidates: Sequence[CorporateEntityCandidate],
) -> list[dict[str, Any]]:
    """Copy classified rows and attach a cataloged org id when the name resolves.

    Unresolved names keep ``corporate_entity_id`` null -- a missing
    hierarchy match is not a guessed neighborhood.
    """
    return [
        {
            **dict(row),
            "corporate_entity_id": resolve_corporate_entity(row["counterparty_entity_name"], candidates),
        }
        for row in rows
    ]


async def fetch_post_counterparties(conn: asyncpg.Connection, post_id: str) -> list[dict[str, Any]]:
    """Classified counterparties with a cataloged org id when the name resolves.

    Unresolved names keep ``corporate_entity_id`` null -- a missing
    hierarchy match is not a guessed neighborhood.
    """
    rows = await conn.fetch(
        """
        select c.counterparty_entity_name, c.relationship_type_code, v.lookup_label as relationship_label,
               c.verification_status_code, c.verification_evidence_url,
               c.verification_evidence_post_id
        from post_counterparty_entity c
        join common_lookup_value v on v.lookup_code = c.relationship_type_code
        where c.post_id = $1
        order by c.counterparty_entity_name
        """,
        post_id,
    )
    candidate_rows = await conn.fetch("select corporate_entity_id, entity_name from corporate_entity")
    candidates = [
        CorporateEntityCandidate(str(row["corporate_entity_id"]), row["entity_name"])
        for row in candidate_rows
    ]
    return attach_resolved_entity_ids(rows, candidates)


async def fetch_relationship_network(
    conn: asyncpg.Connection, corporate_entity_ids: Sequence[str]
) -> list[dict[str, Any]]:
    """Every counterparty's full observed relationship network, entity-level.

    ``post_counterparty_entity`` classifies one counterparty name's
    relationship to us per post (e.g. this specific post is
    ``rel_voc`` -- Voice of Customer). A real counterparty is not
    limited to one such role over its lifetime: the same organization
    can be a customer in one post, a competitor in another (their own
    product line competes with ours elsewhere), the customer of our
    customer in a third, or a supplier -- Customer Master's per-post
    reads never rolled these up, so buyers could only see one role at
    a time and never the entity's whole network. This groups every
    visible, eligible post's classifications by counterparty name,
    keeping every distinct relationship type observed (not just the
    most frequent), so a buyer can see a name marked both Customer and
    Competitor and know that reflects the real, mixed relationship
    rather than a classification error.

    Unresolved names keep ``corporate_entity_id`` null, same
    missing-vs-guessed discipline as :func:`attach_resolved_entity_ids`.
    Capped at the ``_RELATIONSHIP_NETWORK_LIMIT`` entities with the most
    total observed posts; ties break on name for a stable order.
    """
    if not corporate_entity_ids:
        return []
    rows = await conn.fetch(
        f"""
        with scoped as (
            select counterparty.counterparty_entity_name,
                   counterparty.relationship_type_code,
                   lookup.lookup_label as relationship_label
              from post_counterparty_entity counterparty
              join source_post post on post.post_id = counterparty.post_id
              join common_lookup_value lookup
                on lookup.lookup_code = counterparty.relationship_type_code
             where (post.visibility_code = 'public' or post.corporate_entity_id = any($1::uuid[]))
               and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}
        ), grouped as (
            select counterparty_entity_name, relationship_type_code, relationship_label,
                   count(*) as post_count
              from scoped
             group by counterparty_entity_name, relationship_type_code, relationship_label
        ), entity_totals as (
            select counterparty_entity_name, sum(post_count) as total_post_count
              from grouped
             group by counterparty_entity_name
        ), top_entities as materialized (
            select counterparty_entity_name, total_post_count
              from entity_totals
             order by total_post_count desc, counterparty_entity_name
             limit {_RELATIONSHIP_NETWORK_LIMIT}
        )
        select top_entities.counterparty_entity_name, top_entities.total_post_count,
               json_agg(
                   json_build_object(
                       'relationship_type_code', grouped.relationship_type_code,
                       'relationship_label', grouped.relationship_label,
                       'post_count', grouped.post_count
                   )
                   order by grouped.post_count desc, grouped.relationship_type_code
               ) as relationships
          from top_entities
          join grouped on grouped.counterparty_entity_name = top_entities.counterparty_entity_name
         group by top_entities.counterparty_entity_name, top_entities.total_post_count
         order by top_entities.total_post_count desc, top_entities.counterparty_entity_name
        """,
        list(corporate_entity_ids),
    )
    candidate_rows = await conn.fetch("select corporate_entity_id, entity_name from corporate_entity")
    candidates = [
        CorporateEntityCandidate(str(row["corporate_entity_id"]), row["entity_name"])
        for row in candidate_rows
    ]
    network: list[dict[str, Any]] = []
    for row in rows:
        relationships = json.loads(row["relationships"]) if isinstance(row["relationships"], str) else row["relationships"]
        network.append(
            {
                "counterparty_entity_name": row["counterparty_entity_name"],
                "corporate_entity_id": resolve_corporate_entity(row["counterparty_entity_name"], candidates),
                "total_post_count": row["total_post_count"],
                "relationships": relationships,
                "multi_role": len(relationships) > 1,
            }
        )
    return network
