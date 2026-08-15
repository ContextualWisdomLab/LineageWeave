"""Load a Postgres knowledge-graph subgraph and run RWR on it.

``lineageweave.knowledge_graph`` is the pure math; this module is the
application-layer reader that respects the same ABAC rule as post
endpoints: private posts the account cannot see never become related
nodes, and a Keyman who is only mentioned on such posts is forbidden.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import asyncpg

from lineageweave.ontology import ontology_annotations
from lineageweave.knowledge_graph import (
    EDGE_AFFILIATION,
    EDGE_CO_MENTION,
    EDGE_MENTION,
    NODE_CORPORATE_ENTITY,
    NODE_PERSON,
    NODE_POST,
    KnowledgeGraphEdgeSpec,
    adjacency_from_edges,
    knowledge_graph_edges_for_post,
    node_key,
    parse_node_key,
    random_walk_with_restart,
    select_related_nodes,
)


def edge_spec_from_row(row: asyncpg.Record) -> KnowledgeGraphEdgeSpec:
    """Map one ``knowledge_graph_edge`` row onto the library spec."""
    return KnowledgeGraphEdgeSpec(
        source_node_type_code=row["source_node_type_code"],
        source_node_id=str(row["source_node_id"]),
        target_node_type_code=row["target_node_type_code"],
        target_node_id=str(row["target_node_id"]),
        edge_type_code=row["edge_type_code"],
        edge_weight=float(row["edge_weight"]),
    )


async def labels_for_codes(conn: asyncpg.Connection, codes: list[str]) -> dict[str, str]:
    """Map lookup codes to their ``common_lookup_value`` labels.

    Codes with no row keep no entry -- callers fall back to the raw
    code rather than inventing a label (missing is not a guessed name).
    """
    unique = [code for code in dict.fromkeys(codes) if code]
    if not unique:
        return {}
    rows = await conn.fetch(
        "select lookup_code, lookup_label from common_lookup_value where lookup_code = any($1::text[])",
        unique,
    )
    return {row["lookup_code"]: row["lookup_label"] for row in rows}


async def fetch_post_keymen(conn: asyncpg.Connection, post_id: str) -> list[dict[str, Any]]:
    """Load mentioned people and their affiliations for one post."""
    person_rows = await conn.fetch(
        """
        select p.person_id, p.person_name, p.person_side_code, p.last_known_job_title, ppm.mention_context
        from post_person_mention ppm
        join cataloged_person p on p.person_id = ppm.person_id
        where ppm.post_id = $1
        order by p.person_name
        """,
        post_id,
    )
    if not person_rows:
        return []

    affiliation_rows = await conn.fetch(
        """
        select person_id, affiliated_organization_name, affiliated_corporate_entity_id, role_title
        from person_affiliation
        where person_id = any($1::uuid[])
        order by affiliated_organization_name
        """,
        [row["person_id"] for row in person_rows],
    )
    affiliations_by_person: dict[str, list[dict[str, Any]]] = {}
    for row in affiliation_rows:
        affiliations_by_person.setdefault(str(row["person_id"]), []).append(
            {
                "organization_name": row["affiliated_organization_name"],
                "corporate_entity_id": (
                    str(row["affiliated_corporate_entity_id"])
                    if row["affiliated_corporate_entity_id"] is not None
                    else None
                ),
                "role_title": row["role_title"],
            }
        )

    side_labels = await labels_for_codes(conn, [row["person_side_code"] for row in person_rows])
    return [
        {
            "person_id": str(row["person_id"]),
            "person_name": row["person_name"],
            "person_side_code": row["person_side_code"],
            "person_side_label": side_labels.get(row["person_side_code"], row["person_side_code"]),
            "mention_context": row["mention_context"],
            "last_known_job_title": row["last_known_job_title"],
            "affiliations": affiliations_by_person.get(str(row["person_id"]), []),
        }
        for row in person_rows
    ]


async def persist_edges_for_post(conn: asyncpg.Connection, post_id: str) -> list[KnowledgeGraphEdgeSpec]:
    """Insert mention, affiliation, and co-mention edges for one post.

    Also derives ADR 0009's team/organization mention edges from
    ``post_team_mention``/``post_organization_mention`` when present --
    a no-op for posts with none of either, so this stays the single
    "compute this post's edges" entry point Keyman ingestion and R&R
    persistence both call, rather than each needing their own partial
    edge-writing logic.
    """
    mention_rows = await conn.fetch(
        "select person_id from post_person_mention where post_id = $1",
        post_id,
    )
    affiliation_rows = await conn.fetch(
        """
        select person_id, affiliated_corporate_entity_id
        from person_affiliation
        where person_id = any($1::uuid[])
          and affiliated_corporate_entity_id is not null
        """,
        [row["person_id"] for row in mention_rows],
    )
    team_mention_rows = await conn.fetch(
        "select team_id from post_team_mention where post_id = $1",
        post_id,
    )
    team_affiliation_rows = await conn.fetch(
        """
        select team_id, affiliated_corporate_entity_id
        from cataloged_team
        where team_id = any($1::uuid[])
          and affiliated_corporate_entity_id is not null
        """,
        [row["team_id"] for row in team_mention_rows],
    )
    organization_mention_rows = await conn.fetch(
        "select corporate_entity_id from post_organization_mention where post_id = $1",
        post_id,
    )
    edges = knowledge_graph_edges_for_post(
        post_id,
        [str(row["person_id"]) for row in mention_rows],
        [
            (str(row["person_id"]), str(row["affiliated_corporate_entity_id"]))
            for row in affiliation_rows
        ],
        [str(row["team_id"]) for row in team_mention_rows],
        [
            (str(row["team_id"]), str(row["affiliated_corporate_entity_id"]))
            for row in team_affiliation_rows
        ],
        [str(row["corporate_entity_id"]) for row in organization_mention_rows],
    )
    for edge in edges:
        await conn.execute(
            """
            insert into knowledge_graph_edge (
                source_node_type_code, source_node_id,
                target_node_type_code, target_node_id,
                edge_type_code, edge_weight
            )
            select $1, $2::uuid, $3, $4::uuid, $5, $6
            where not exists (
                select 1 from knowledge_graph_edge
                where source_node_type_code = $1
                  and source_node_id = $2::uuid
                  and target_node_type_code = $3
                  and target_node_id = $4::uuid
                  and edge_type_code = $5
            )
            """,
            edge.source_node_type_code,
            edge.source_node_id,
            edge.target_node_type_code,
            edge.target_node_id,
            edge.edge_type_code,
            edge.edge_weight,
        )
    return edges


async def person_exists(conn: asyncpg.Connection, person_id: str) -> bool:
    """True when ``person_id`` is a UUID that exists in ``cataloged_person``."""
    try:
        UUID(person_id)
    except ValueError:
        return False
    row = await conn.fetchrow("select 1 from cataloged_person where person_id = $1", person_id)
    return row is not None


async def corporate_entity_exists(conn: asyncpg.Connection, entity_id: str) -> bool:
    """True when ``entity_id`` is a UUID that exists in ``corporate_entity``."""
    try:
        UUID(entity_id)
    except ValueError:
        return False
    row = await conn.fetchrow(
        "select 1 from corporate_entity where corporate_entity_id = $1", entity_id
    )
    return row is not None


async def visible_mention_post_ids(
    conn: asyncpg.Connection,
    person_id: str,
    can_see_post,
) -> list[str]:
    """Post ids that mention ``person_id`` and pass the caller's ABAC check."""
    rows = await conn.fetch(
        """
        select p.post_id, p.visibility_code, p.corporate_entity_id
        from post_person_mention ppm
        join source_post p on p.post_id = ppm.post_id
        where ppm.person_id = $1
        """,
        person_id,
    )
    return [str(row["post_id"]) for row in rows if can_see_post(row)]


async def visible_affiliation_post_ids(
    conn: asyncpg.Connection,
    entity_id: str,
    can_see_post,
) -> list[str]:
    """Post ids that mention someone affiliated with ``entity_id`` and pass ABAC."""
    rows = await conn.fetch(
        """
        select distinct p.post_id, p.visibility_code, p.corporate_entity_id
        from person_affiliation pa
        join post_person_mention ppm on ppm.person_id = pa.person_id
        join source_post p on p.post_id = ppm.post_id
        where pa.affiliated_corporate_entity_id = $1
        """,
        entity_id,
    )
    return [str(row["post_id"]) for row in rows if can_see_post(row)]


async def load_visible_subgraph(
    conn: asyncpg.Connection,
    visible_post_ids: list[str],
) -> list[KnowledgeGraphEdgeSpec]:
    """Edges whose endpoints the account can already see via those posts."""
    if not visible_post_ids:
        return []
    person_rows = await conn.fetch(
        "select distinct person_id from post_person_mention where post_id = any($1::uuid[])",
        visible_post_ids,
    )
    person_ids = [row["person_id"] for row in person_rows]
    if not person_ids:
        return []
    rows = await conn.fetch(
        """
        select source_node_type_code, source_node_id,
               target_node_type_code, target_node_id,
               edge_type_code, edge_weight
        from knowledge_graph_edge
        where
          (
            edge_type_code = $3
            and (
              (source_node_type_code = $4 and source_node_id = any($1::uuid[]))
              or (target_node_type_code = $4 and target_node_id = any($1::uuid[]))
            )
          )
          or (
            edge_type_code = $5
            and source_node_type_code = $6
            and target_node_type_code = $6
            and source_node_id = any($2::uuid[])
            and target_node_id = any($2::uuid[])
          )
          or (
            edge_type_code = $7
            and (
              (source_node_type_code = $6 and source_node_id = any($2::uuid[]))
              or (target_node_type_code = $6 and target_node_id = any($2::uuid[]))
            )
          )
        """,
        visible_post_ids,
        person_ids,
        EDGE_MENTION,
        NODE_POST,
        EDGE_CO_MENTION,
        NODE_PERSON,
        EDGE_AFFILIATION,
    )
    return [edge_spec_from_row(row) for row in rows]


async def hydrate_related_nodes(
    conn: asyncpg.Connection,
    related: list[tuple[str, float]],
) -> list[dict[str, Any]]:
    """Attach display labels and ontology class terms to scored keys.

    Unknown ids are dropped. Ontology fields are omitted (not faked)
    when ``node_type_code`` has no term in lineageweave-kg.ttl.
    """
    person_ids: list[str] = []
    post_ids: list[str] = []
    corp_ids: list[str] = []
    parsed: list[tuple[str, str, float]] = []
    for key, score in related:
        node_type_code, node_id = parse_node_key(key)
        parsed.append((node_type_code, node_id, score))
        if node_type_code == NODE_PERSON:
            person_ids.append(node_id)
        elif node_type_code == NODE_POST:
            post_ids.append(node_id)
        elif node_type_code == NODE_CORPORATE_ENTITY:
            corp_ids.append(node_id)

    people = {
        str(row["person_id"]): row
        for row in await conn.fetch(
            "select person_id, person_name, person_side_code from cataloged_person where person_id = any($1::uuid[])",
            person_ids,
        )
    } if person_ids else {}
    posts = {
        str(row["post_id"]): row
        for row in await conn.fetch(
            "select post_id, post_title from source_post where post_id = any($1::uuid[])",
            post_ids,
        )
    } if post_ids else {}
    corps = {
        str(row["corporate_entity_id"]): row
        for row in await conn.fetch(
            "select corporate_entity_id, entity_name from corporate_entity where corporate_entity_id = any($1::uuid[])",
            corp_ids,
        )
    } if corp_ids else {}

    side_labels = await labels_for_codes(
        conn, [row["person_side_code"] for row in people.values()]
    )

    payload: list[dict[str, Any]] = []
    for node_type_code, node_id, score in parsed:
        item: dict[str, Any] = {
            "node_id": node_id,
            "node_type_code": node_type_code,
            "relevance": score,
            **ontology_annotations(node_type_code),
        }
        if node_type_code == NODE_PERSON and node_id in people:
            side = people[node_id]["person_side_code"]
            item["label"] = people[node_id]["person_name"]
            item["person_side_code"] = side
            item["person_side_label"] = side_labels.get(side, side)
        elif node_type_code == NODE_POST and node_id in posts:
            item["label"] = posts[node_id]["post_title"]
        elif node_type_code == NODE_CORPORATE_ENTITY and node_id in corps:
            item["label"] = corps[node_id]["entity_name"]
        else:
            continue
        payload.append(item)
    return payload


async def related_for_start(
    conn: asyncpg.Connection,
    node_type_code: str,
    node_id: str,
    visible_post_ids: list[str],
) -> list[dict[str, Any]]:
    """Run RWR from one node over the account's visible subgraph."""
    edges = await load_visible_subgraph(conn, visible_post_ids)
    start = node_key(node_type_code, node_id)
    scores = random_walk_with_restart(adjacency_from_edges(edges), start_node=start)
    related = select_related_nodes(scores, start_node=start)
    return await hydrate_related_nodes(conn, related)


async def related_for_person(
    conn: asyncpg.Connection,
    person_id: str,
    visible_post_ids: list[str],
) -> list[dict[str, Any]]:
    """Run RWR from ``person_id`` over the account's visible subgraph."""
    return await related_for_start(conn, NODE_PERSON, person_id, visible_post_ids)


async def related_for_entity(
    conn: asyncpg.Connection,
    entity_id: str,
    visible_post_ids: list[str],
) -> list[dict[str, Any]]:
    """Run RWR from ``entity_id`` over the account's visible subgraph."""
    return await related_for_start(conn, NODE_CORPORATE_ENTITY, entity_id, visible_post_ids)
