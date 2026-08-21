"""Load an ABAC-visible ontology neighborhood from PostgreSQL (ADR 0119)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Sequence
from uuid import UUID

import asyncpg

from backend.app.knowledge_graph import (
    corporate_entity_exists,
    person_exists,
    team_exists,
    visible_affiliation_post_ids,
    visible_mention_post_ids,
    visible_team_mention_post_ids,
)
from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave.knowledge_graph import (
    NODE_CORPORATE_ENTITY,
    NODE_PERSON,
    NODE_POST,
    NODE_TEAM,
)
from lineageweave.ontology_neighborhood import (
    DEFAULT_MAXIMUM_DEPTH,
    DEFAULT_MAXIMUM_EDGES,
    DEFAULT_MAXIMUM_NODES,
    KNOWN_NODE_TYPES,
    NeighborhoodFact,
    OntologyNeighborhood,
    OntologyNeighborhoodError,
    assemble_ontology_neighborhood,
    fact_from_knowledge_graph_edge,
    skos_broader_fact,
)

FORBIDDEN_NEIGHBORHOOD_CODES = frozenset({"focus_hidden", "focus_not_visible"})
NOT_FOUND_NEIGHBORHOOD_CODES = frozenset({"unknown_node_type", "dangling_endpoint"})


def neighborhood_error_http_status(error: OntologyNeighborhoodError) -> int:
    """Map a fail-closed assembler error onto an HTTP status.

    Next action: return this status from GET /api/ontology/neighborhood
    and name the buyer's next visible focus rather than leaking counts.
    """
    if error.code in FORBIDDEN_NEIGHBORHOOD_CODES:
        return 403
    if error.code in NOT_FOUND_NEIGHBORHOOD_CODES:
        return 404
    return 422


def parse_allowed_property_query(values: Sequence[str] | None) -> list[str] | None:
    """Split repeated or comma-separated property filters into codes."""
    if values is None:
        return None
    codes: list[str] = []
    for value in values:
        for part in value.split(","):
            stripped = part.strip()
            if stripped:
                codes.append(stripped)
    return codes or None


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
    except ValueError:
        return False
    return True


async def visible_post_ids_for_focus(
    conn: asyncpg.Connection,
    focus_node_type_code: str,
    focus_node_id: str,
    can_see_post: Callable[[asyncpg.Record], bool],
) -> list[str]:
    """Visible evidence posts that authorize the requested focus node."""
    if focus_node_type_code == NODE_POST:
        # Safe SQL: eligibility is an immutable schema fragment; id is bound.
        row = await conn.fetchrow(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            f"""
            select post_id, visibility_code, corporate_entity_id
              from source_post
             where post_id = $1
               and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')}
            """,
            focus_node_id,
        )
        if row is None:
            return []
        return [str(row["post_id"])] if can_see_post(row) else []
    if focus_node_type_code == NODE_PERSON:
        return await visible_mention_post_ids(conn, focus_node_id, can_see_post)
    if focus_node_type_code == NODE_CORPORATE_ENTITY:
        return await visible_affiliation_post_ids(conn, focus_node_id, can_see_post)
    if focus_node_type_code == NODE_TEAM:
        return await visible_team_mention_post_ids(conn, focus_node_id, can_see_post)
    raise OntologyNeighborhoodError("unknown_node_type", f"unknown node type {focus_node_type_code!r}")


async def focus_catalog_exists(
    conn: asyncpg.Connection, focus_node_type_code: str, focus_node_id: str
) -> bool:
    """True when the focus id exists in the governed catalog."""
    if not _is_uuid(focus_node_id):
        return False
    if focus_node_type_code == NODE_POST:
        row = await conn.fetchrow("select 1 from source_post where post_id = $1", focus_node_id)
        return row is not None
    if focus_node_type_code == NODE_PERSON:
        return await person_exists(conn, focus_node_id)
    if focus_node_type_code == NODE_CORPORATE_ENTITY:
        return await corporate_entity_exists(conn, focus_node_id)
    if focus_node_type_code == NODE_TEAM:
        return await team_exists(conn, focus_node_id)
    raise OntologyNeighborhoodError("unknown_node_type", f"unknown node type {focus_node_type_code!r}")


async def _load_facts(
    conn: asyncpg.Connection, visible_post_ids: list[str]
) -> list[NeighborhoodFact]:
    if not visible_post_ids:
        return []
    rows = await conn.fetch(
        """
        select edge.source_node_type_code,
               edge.source_node_id,
               edge.target_node_type_code,
               edge.target_node_id,
               edge.edge_type_code,
               min(post.created_at) as available_at,
               array_agg(evidence.evidence_post_id::text order by evidence.evidence_post_id)
                   as evidence_ids
          from knowledge_graph_edge edge
          join knowledge_graph_edge_evidence evidence
            on evidence.knowledge_graph_edge_id = edge.knowledge_graph_edge_id
          join source_post post
            on post.post_id = evidence.evidence_post_id
         where evidence.evidence_post_id = any($1::uuid[])
         group by edge.source_node_type_code, edge.source_node_id,
                  edge.target_node_type_code, edge.target_node_id,
                  edge.edge_type_code
        """,
        visible_post_ids,
    )
    facts: list[NeighborhoodFact] = []
    for row in rows:
        facts.append(
            fact_from_knowledge_graph_edge(
                source_node_type_code=row["source_node_type_code"],
                source_node_id=str(row["source_node_id"]),
                target_node_type_code=row["target_node_type_code"],
                target_node_id=str(row["target_node_id"]),
                edge_type_code=row["edge_type_code"],
                recorded_at=row["available_at"],
                evidence_references=tuple(row["evidence_ids"] or ()),
                provenance_reference="knowledge_graph_edge",
            )
        )
    return facts


async def _load_skos_facts(
    conn: asyncpg.Connection, corporate_entity_ids: list[str]
) -> list[NeighborhoodFact]:
    if not corporate_entity_ids:
        return []
    rows = await conn.fetch(
        """
        select corporate_entity_id, parent_entity_id, created_at
          from corporate_entity
         where corporate_entity_id = any($1::uuid[])
           and parent_entity_id is not null
        """,
        corporate_entity_ids,
    )
    return [
        skos_broader_fact(
            narrower_entity_id=str(row["corporate_entity_id"]),
            broader_entity_id=str(row["parent_entity_id"]),
            recorded_at=row["created_at"],
            provenance_reference="corporate_entity.parent_entity_id",
        )
        for row in rows
    ]


async def _visible_corporate_entity_ids(
    conn: asyncpg.Connection,
    corporate_entity_ids: list[str],
    can_see_post: Callable[[asyncpg.Record], bool],
) -> set[str]:
    """Return catalog entities supported by at least one visible post.

    Corporate hierarchy rows do not carry their own post visibility. A
    parent entity therefore cannot be exposed merely because a visible child
    points at it; it needs the same visible evidence gate as every other
    corporate-entity endpoint.
    """
    visible: set[str] = set()
    for entity_id in dict.fromkeys(corporate_entity_ids):
        if await visible_affiliation_post_ids(conn, entity_id, can_see_post):
            visible.add(entity_id)
    return visible


async def _load_labels(
    conn: asyncpg.Connection, facts: list[NeighborhoodFact]
) -> dict[tuple[str, str], str]:
    person_ids: list[str] = []
    post_ids: list[str] = []
    corp_ids: list[str] = []
    team_ids: list[str] = []
    for fact in facts:
        for node_type, node_id in (
            (fact.source_node_type_code, fact.source_node_id),
            (fact.target_node_type_code, fact.target_node_id),
        ):
            if node_type == NODE_PERSON:
                person_ids.append(node_id)
            elif node_type == NODE_POST:
                post_ids.append(node_id)
            elif node_type == NODE_CORPORATE_ENTITY:
                corp_ids.append(node_id)
            elif node_type == NODE_TEAM:
                team_ids.append(node_id)
    labels: dict[tuple[str, str], str] = {}
    if person_ids:
        for row in await conn.fetch(
            "select person_id, person_name from cataloged_person where person_id = any($1::uuid[])",
            person_ids,
        ):
            labels[(NODE_PERSON, str(row["person_id"]))] = row["person_name"]
    if post_ids:
        for row in await conn.fetch(
            "select post_id, post_title from source_post where post_id = any($1::uuid[])",
            post_ids,
        ):
            labels[(NODE_POST, str(row["post_id"]))] = row["post_title"]
    if corp_ids:
        for row in await conn.fetch(
            "select corporate_entity_id, entity_name from corporate_entity "
            "where corporate_entity_id = any($1::uuid[])",
            corp_ids,
        ):
            labels[(NODE_CORPORATE_ENTITY, str(row["corporate_entity_id"]))] = row["entity_name"]
    if team_ids:
        for row in await conn.fetch(
            "select team_id, team_name from cataloged_team where team_id = any($1::uuid[])",
            team_ids,
        ):
            labels[(NODE_TEAM, str(row["team_id"]))] = row["team_name"]
    return labels


def neighborhood_to_payload(neighborhood: OntologyNeighborhood) -> dict[str, Any]:
    """JSON object for GET /api/ontology/neighborhood."""
    return {
        "focus_node_id": neighborhood.focus_node_id,
        "focus_node_type_code": neighborhood.focus_node_type_code,
        "truncated": neighborhood.truncated,
        "next_cursor": neighborhood.next_cursor,
        "limitation_code": neighborhood.limitation_code,
        "nodes": [
            {
                "node_id": node.node_id,
                "node_type_code": node.node_type_code,
                "ontology_class_iri": node.ontology_class_iri,
                "display_label": node.display_label,
                "truth_status_code": node.truth_status_code,
                "valid_from": node.valid_from.isoformat() if node.valid_from else None,
                "valid_to": node.valid_to.isoformat() if node.valid_to else None,
                "recorded_at": node.recorded_at.isoformat(),
                "evidence_count": node.evidence_count,
                "shape_code": node.shape_code,
            }
            for node in neighborhood.nodes
        ],
        "edges": [
            {
                "edge_id": edge.edge_id,
                "source_node_id": edge.source_node_id,
                "target_node_id": edge.target_node_id,
                "property_code": edge.property_code,
                "ontology_property_iri": edge.ontology_property_iri,
                "property_label": edge.property_label,
                "truth_status_code": edge.truth_status_code,
                "valid_from": edge.valid_from.isoformat() if edge.valid_from else None,
                "valid_to": edge.valid_to.isoformat() if edge.valid_to else None,
                "recorded_at": edge.recorded_at.isoformat(),
                "provenance_reference": edge.provenance_reference,
                "evidence_references": list(edge.evidence_references),
            }
            for edge in neighborhood.edges
        ],
        "exact_value_rows": list(neighborhood.exact_value_rows()),
        "jsonld": neighborhood.jsonld_document(),
    }


async def visible_ontology_neighborhood(
    conn: asyncpg.Connection,
    *,
    focus_node_type_code: str,
    focus_node_id: str,
    can_see_post: Callable[[asyncpg.Record], bool],
    maximum_depth: int = DEFAULT_MAXIMUM_DEPTH,
    maximum_nodes: int = DEFAULT_MAXIMUM_NODES,
    maximum_edges: int = DEFAULT_MAXIMUM_EDGES,
    allowed_property_codes: list[str] | None = None,
    knowledge_cutoff: datetime | None = None,
    cursor: str | None = None,
) -> OntologyNeighborhood:
    """Assemble the authorized neighborhood for one focus node."""
    if focus_node_type_code not in KNOWN_NODE_TYPES:
        raise OntologyNeighborhoodError(
            "unknown_node_type", f"unknown node type {focus_node_type_code!r}"
        )
    if not focus_node_id or focus_node_id.strip() != focus_node_id:
        raise OntologyNeighborhoodError("invalid_focus_id", "focus node id is empty or malformed")
    if not await focus_catalog_exists(conn, focus_node_type_code, focus_node_id):
        raise OntologyNeighborhoodError("unknown_node_type", "focus node not found")
    visible_post_ids = await visible_post_ids_for_focus(
        conn, focus_node_type_code, focus_node_id, can_see_post
    )
    if not visible_post_ids:
        raise OntologyNeighborhoodError("focus_not_visible", "focus node is not visible")
    facts = await _load_facts(conn, visible_post_ids)
    corp_ids = [
        fact.source_node_id if fact.source_node_type_code == NODE_CORPORATE_ENTITY else fact.target_node_id
        for fact in facts
        if NODE_CORPORATE_ENTITY in {fact.source_node_type_code, fact.target_node_type_code}
    ]
    if focus_node_type_code == NODE_CORPORATE_ENTITY:
        corp_ids.append(focus_node_id)
    skos_facts = await _load_skos_facts(conn, list(dict.fromkeys(corp_ids)))
    corp_endpoint_ids = [
        endpoint_id
        for fact in skos_facts
        for endpoint_type, endpoint_id in (
            (fact.source_node_type_code, fact.source_node_id),
            (fact.target_node_type_code, fact.target_node_id),
        )
        if endpoint_type == NODE_CORPORATE_ENTITY and endpoint_id != focus_node_id
    ]
    visible_corp_ids = await _visible_corporate_entity_ids(
        conn, corp_endpoint_ids, can_see_post
    )
    visible_corp_ids.add(focus_node_id)
    facts.extend(
        fact
        for fact in skos_facts
        if all(
            endpoint_type != NODE_CORPORATE_ENTITY or endpoint_id in visible_corp_ids
            for endpoint_type, endpoint_id in (
                (fact.source_node_type_code, fact.source_node_id),
                (fact.target_node_type_code, fact.target_node_id),
            )
        )
    )
    labels = await _load_labels(conn, facts)
    if focus_node_type_code == NODE_POST:
        title = await conn.fetchval("select post_title from source_post where post_id = $1", focus_node_id)
        if title:
            labels[(NODE_POST, focus_node_id)] = title
    elif focus_node_type_code == NODE_PERSON:
        name = await conn.fetchval(
            "select person_name from cataloged_person where person_id = $1", focus_node_id
        )
        if name:
            labels[(NODE_PERSON, focus_node_id)] = name
    elif focus_node_type_code == NODE_CORPORATE_ENTITY:
        name = await conn.fetchval(
            "select entity_name from corporate_entity where corporate_entity_id = $1",
            focus_node_id,
        )
        if name:
            labels[(NODE_CORPORATE_ENTITY, focus_node_id)] = name
    else:
        name = await conn.fetchval(
            "select team_name from cataloged_team where team_id = $1", focus_node_id
        )
        if name:
            labels[(NODE_TEAM, focus_node_id)] = name
    facts = [
        fact
        for fact in facts
        if (fact.source_node_type_code, fact.source_node_id) in labels
        and (fact.target_node_type_code, fact.target_node_id) in labels
    ]
    return assemble_ontology_neighborhood(
        focus_node_type_code=focus_node_type_code,
        focus_node_id=focus_node_id,
        facts=facts,
        labels=labels,
        knowledge_cutoff=knowledge_cutoff,
        maximum_depth=maximum_depth,
        maximum_nodes=maximum_nodes,
        maximum_edges=maximum_edges,
        allowed_property_codes=allowed_property_codes,
        cursor=cursor,
    )
