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

from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave.ontology import ontology_annotations
from lineageweave.organization_alias import (
    OrganizationNameAlias,
    attach_organization_alias,
    attach_organization_aliases,
)
from lineageweave.knowledge_graph import (
    EDGE_AFFILIATION,
    EDGE_CO_MENTION,
    EDGE_MENTION,
    EDGE_MENTION_ORGANIZATION,
    EDGE_MENTION_TEAM,
    EDGE_TEAM_AFFILIATION,
    NODE_CORPORATE_ENTITY,
    NODE_PERSON,
    NODE_POST,
    NODE_TEAM,
    KnowledgeGraphEdgeSpec,
    adjacency_from_edges,
    knowledge_graph_edges_for_post,
    node_key,
    parse_node_key,
    random_walk_with_restart,
    select_related_nodes,
)

from .organization_name_resolution_ingestion import fetch_corroborated_organization_aliases


_GRAPH_PROJECTION_LOCK_KEY = "lineageweave:knowledge_graph_projection"


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


async def fetch_post_keymen(
    conn: asyncpg.Connection,
    post_id: str,
    *,
    organization_aliases: tuple[OrganizationNameAlias, ...] | None = None,
) -> list[dict[str, Any]]:
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
    aliases = organization_aliases
    if aliases is None:
        aliases = await fetch_corroborated_organization_aliases(conn)
    people = [
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
    for person in people:
        attach_organization_aliases(
            person["affiliations"],
            aliases,
            name_key="organization_name",
        )
    return people


async def persist_edges_for_post(
    conn: asyncpg.Connection, post_id: str
) -> list[KnowledgeGraphEdgeSpec]:
    """Reconcile one post's evidence-backed navigation projection.

    Callers own the surrounding transaction. A transaction-scoped
    advisory lock serializes the small materialized projection so two
    writers cannot interleave evidence deletion and orphan pruning.
    Keyman and R&R person sources stay distinct in their writable tables;
    ``combined_post_person_mention`` is used only to derive graph edges.
    """
    await conn.execute(
        "select pg_advisory_xact_lock(hashtext($1))",
        _GRAPH_PROJECTION_LOCK_KEY,
    )
    await conn.execute(
        "delete from knowledge_graph_edge_evidence where evidence_post_id = $1",
        post_id,
    )
    mention_rows = await conn.fetch(
        "select person_id from combined_post_person_mention where post_id = $1",
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
        await conn.fetchrow(
            """
            insert into knowledge_graph_edge (
                source_node_type_code, source_node_id,
                target_node_type_code, target_node_id,
                edge_type_code, edge_weight
            ) values ($1, $2::uuid, $3, $4::uuid, $5, $6)
            on conflict (
                source_node_type_code, source_node_id,
                target_node_type_code, target_node_id,
                edge_type_code
            ) do update set edge_weight = excluded.edge_weight
            returning knowledge_graph_edge_id
            """,
            edge.source_node_type_code,
            edge.source_node_id,
            edge.target_node_type_code,
            edge.target_node_id,
            edge.edge_type_code,
            edge.edge_weight,
        )
    await conn.execute(
        """
        delete from knowledge_graph_edge edge_row
         where not exists (
             select 1
               from knowledge_graph_edge_evidence evidence
              where evidence.knowledge_graph_edge_id =
                    edge_row.knowledge_graph_edge_id
         )
        """
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


async def team_exists(conn: asyncpg.Connection, team_id: str) -> bool:
    """True when ``team_id`` is a UUID that exists in ``cataloged_team``."""
    try:
        UUID(team_id)
    except ValueError:
        return False
    row = await conn.fetchrow("select 1 from cataloged_team where team_id = $1", team_id)
    return row is not None


async def visible_mention_post_ids(
    conn: asyncpg.Connection,
    person_id: str,
    can_see_post,
) -> list[str]:
    """Visible post ids supported by Keyman or R&R person evidence."""
    # Safe SQL: the eligibility predicate is an immutable schema fragment; person id is bound.
    rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        f"""
        select post.post_id, post.visibility_code, post.corporate_entity_id, post.process_unit_id
          from combined_post_person_mention mention
          join source_post post on post.post_id = mention.post_id
         where mention.person_id = $1
           and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}
         order by post.created_at, post.post_id
        """,
        person_id,
    )
    return [str(row["post_id"]) for row in rows if can_see_post(row)]

async def visible_affiliation_post_ids(
    conn: asyncpg.Connection,
    entity_id: str,
    can_see_post,
) -> list[str]:
    """Visible posts that mention an entity via a person or a direct org mention."""
    # Safe SQL: the eligibility predicate is an immutable schema fragment; entity id is bound.
    rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        f"""
        select distinct post.post_id, post.visibility_code,
                        post.corporate_entity_id, post.process_unit_id, post.created_at
          from source_post post
         where {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}
           and post.post_id in (
            select mention.post_id
              from person_affiliation affiliation
              join combined_post_person_mention mention
                on mention.person_id = affiliation.person_id
             where affiliation.affiliated_corporate_entity_id = $1
            union
            select org_mention.post_id
              from post_organization_mention org_mention
             where org_mention.corporate_entity_id = $1
         )
         order by post.created_at, post.post_id
        """,
        entity_id,
    )
    return [str(row["post_id"]) for row in rows if can_see_post(row)]


async def visible_team_mention_post_ids(
    conn: asyncpg.Connection,
    team_id: str,
    can_see_post,
) -> list[str]:
    """Visible post ids supported by a cataloged team mention."""
    # Safe SQL: the eligibility predicate is an immutable schema fragment; team id is bound.
    rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        f"""
        select post.post_id, post.visibility_code, post.corporate_entity_id, post.process_unit_id
          from post_team_mention mention
          join source_post post on post.post_id = mention.post_id
         where mention.team_id = $1
           and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}
         order by post.created_at, post.post_id
        """,
        team_id,
    )
    return [str(row["post_id"]) for row in rows if can_see_post(row)]

async def load_visible_subgraph(
    conn: asyncpg.Connection,
    visible_post_ids: list[str],
) -> list[KnowledgeGraphEdgeSpec]:
    """Edges supported by at least one post the account may already see.

    Person, team, and organization mention channels are independent. A
    team-only or organization-only post must still walk (ADR 0018).
    """
    if not visible_post_ids:
        return []
    person_rows = await conn.fetch(
        "select distinct person_id from combined_post_person_mention "
        "where post_id = any($1::uuid[])",
        visible_post_ids,
    )
    person_ids = [row["person_id"] for row in person_rows]
    team_rows = await conn.fetch(
        "select distinct team_id from post_team_mention "
        "where post_id = any($1::uuid[])",
        visible_post_ids,
    )
    team_ids = [row["team_id"] for row in team_rows]
    organization_rows = await conn.fetch(
        "select distinct corporate_entity_id from post_organization_mention "
        "where post_id = any($1::uuid[])",
        visible_post_ids,
    )
    organization_ids = [row["corporate_entity_id"] for row in organization_rows]
    if not person_ids and not team_ids and not organization_ids:
        return []
    rows = await conn.fetch(
        """
        select distinct edge.source_node_type_code, edge.source_node_id,
               edge.target_node_type_code, edge.target_node_id,
               edge.edge_type_code, edge.edge_weight
          from knowledge_graph_edge edge
          join knowledge_graph_edge_evidence evidence
            on evidence.knowledge_graph_edge_id = edge.knowledge_graph_edge_id
           and evidence.evidence_post_id = any($1::uuid[])
         where
          (
            edge.edge_type_code = $3
            and (
              (edge.source_node_type_code = $4
               and edge.source_node_id = any($1::uuid[]))
              or
              (edge.target_node_type_code = $4
               and edge.target_node_id = any($1::uuid[]))
            )
          )
          or (
            edge.edge_type_code = $5
            and edge.source_node_type_code = $6
            and edge.target_node_type_code = $6
            and edge.source_node_id = any($2::uuid[])
            and edge.target_node_id = any($2::uuid[])
          )
          or (
            edge.edge_type_code = $7
            and (
              (edge.source_node_type_code = $6
               and edge.source_node_id = any($2::uuid[]))
              or
              (edge.target_node_type_code = $6
               and edge.target_node_id = any($2::uuid[]))
            )
          )
          or (
            edge.edge_type_code = $8
            and (
              (edge.source_node_type_code = $4
               and edge.source_node_id = any($1::uuid[]))
              or
              (edge.target_node_type_code = $4
               and edge.target_node_id = any($1::uuid[]))
              or
              (edge.source_node_type_code = $9
               and edge.source_node_id = any($10::uuid[]))
              or
              (edge.target_node_type_code = $9
               and edge.target_node_id = any($10::uuid[]))
            )
          )
          or (
            edge.edge_type_code = $11
            and (
              (edge.source_node_type_code = $9
               and edge.source_node_id = any($10::uuid[]))
              or
              (edge.target_node_type_code = $9
               and edge.target_node_id = any($10::uuid[]))
            )
          )
          or (
            edge.edge_type_code = $12
            and (
              (edge.source_node_type_code = $4
               and edge.source_node_id = any($1::uuid[]))
              or
              (edge.target_node_type_code = $4
               and edge.target_node_id = any($1::uuid[]))
              or
              (edge.source_node_type_code = $13
               and edge.source_node_id = any($14::uuid[]))
              or
              (edge.target_node_type_code = $13
               and edge.target_node_id = any($14::uuid[]))
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
        EDGE_MENTION_TEAM,
        NODE_TEAM,
        team_ids,
        EDGE_TEAM_AFFILIATION,
        EDGE_MENTION_ORGANIZATION,
        NODE_CORPORATE_ENTITY,
        organization_ids,
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
    team_ids: list[str] = []
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
        elif node_type_code == NODE_TEAM:
            team_ids.append(node_id)

    people = {
        str(row["person_id"]): row
        for row in await conn.fetch(
            "select person_id, person_name, person_side_code from cataloged_person where person_id = any($1::uuid[])",
            person_ids,
        )
    } if person_ids else {}
    posts = {
        str(row["post_id"]): row
        # Safe SQL: the eligibility predicate is an immutable schema fragment; post ids are bound.
        for row in await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            f"select post_id, post_title, "
            "btrim(left(source_post_search_text(post_body), 420)) as post_body_excerpt, "
            "char_length(coalesce(post_body, '')) > 420 as post_body_truncated "
            f"from source_post where post_id = any($1::uuid[]) and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')}",
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
    teams = {
        str(row["team_id"]): row
        for row in await conn.fetch(
            "select team_id, team_name from cataloged_team where team_id = any($1::uuid[])",
            team_ids,
        )
    } if team_ids else {}

    side_labels = await labels_for_codes(
        conn, [row["person_side_code"] for row in people.values()]
    )
    aliases = await fetch_corroborated_organization_aliases(conn) if corp_ids else ()

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
            item["post_body_excerpt"] = posts[node_id]["post_body_excerpt"]
            item["post_body_truncated"] = posts[node_id]["post_body_truncated"]
        elif node_type_code == NODE_CORPORATE_ENTITY and node_id in corps:
            item["label"] = corps[node_id]["entity_name"]
            attach_organization_alias(
                item,
                aliases,
                name_key="label",
                entity_id_key="node_id",
            )
        elif node_type_code == NODE_TEAM and node_id in teams:
            item["label"] = teams[node_id]["team_name"]
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


async def fetch_person_role_history(
    conn: asyncpg.Connection,
    person_id: str,
    visible_post_ids: list[str],
) -> list[dict[str, Any]]:
    """This Keyman's responsibility and affiliated organization across time.

    RWR's related-nodes view answers "what else connects to this
    person"; it does not answer "how has this specific person's role
    changed" -- the same cataloged_person can be affiliated with
    different organizations, or described with a different
    responsibility, in posts at different times (a job change, a title
    change, a move between projects). ``post_summary_role`` already
    carries this per post; this simply orders it chronologically for
    one person instead of leaving a buyer to open every post that
    mentions them and compare manually.

    ``visible_post_ids`` must already be ABAC-filtered by the caller
    (see ``visible_mention_post_ids``); this function does not itself
    check visibility. An empty result means no role classification
    exists for this person on any post the account can see, not that
    the person is unknown.
    """
    if not visible_post_ids:
        return []
    rows = await conn.fetch(
        """
        select role.post_id, post.post_title, post.created_at,
               role.responsibility, role.affiliated_organization_name
          from post_summary_role role
          join source_post post on post.post_id = role.post_id
         where role.cataloged_person_id = $1
           and role.post_id = any($2::uuid[])
         order by post.created_at asc, role.post_id
        """,
        person_id,
        visible_post_ids,
    )
    return [
        {
            "post_id": str(row["post_id"]),
            "post_title": row["post_title"],
            "created_at": row["created_at"].isoformat(),
            "responsibility": row["responsibility"],
            "affiliated_organization_name": row["affiliated_organization_name"],
        }
        for row in rows
    ]


async def related_for_entity(
    conn: asyncpg.Connection,
    entity_id: str,
    visible_post_ids: list[str],
) -> list[dict[str, Any]]:
    """Run RWR from ``entity_id`` over the account's visible subgraph."""
    return await related_for_start(conn, NODE_CORPORATE_ENTITY, entity_id, visible_post_ids)


async def related_for_team(
    conn: asyncpg.Connection,
    team_id: str,
    visible_post_ids: list[str],
) -> list[dict[str, Any]]:
    """Run RWR from ``team_id`` over the account's visible subgraph."""
    return await related_for_start(conn, NODE_TEAM, team_id, visible_post_ids)
