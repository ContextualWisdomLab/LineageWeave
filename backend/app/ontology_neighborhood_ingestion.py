"""Load an ABAC-visible ontology neighborhood from PostgreSQL (ADR 0184)."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence
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
    EDGE_MENTION_PROJECT,
    NODE_CORPORATE_ENTITY,
    NODE_OCCUPATIONAL_CONSTRUCT,
    NODE_PERSON,
    NODE_POST,
    NODE_PROJECT,
    NODE_TEAM,
    EDGE_MENTION_PROJECT,
    EDGE_SUPPORTS_OCCUPATIONAL_CONSTRUCT,
)
from lineageweave.ontology import iri_for_lookup_code
from lineageweave.ontology_neighborhood import (
    DEFAULT_MAXIMUM_DEPTH,
    DEFAULT_MAXIMUM_EDGES,
    DEFAULT_MAXIMUM_NODES,
    HARD_MAXIMUM_EDGES,
    KNOWN_NODE_TYPES,
    PROPERTY_SKOS_BROADER,
    NeighborhoodFact,
    OntologyNeighborhood,
    OntologyNeighborhoodError,
    OntologyNodeMetadata,
    OntologyVoiceAssignment,
    assemble_ontology_neighborhood,
    fact_from_knowledge_graph_edge,
    skos_broader_fact,
)
from lineageweave.ontology_source_cursor import (
    SOURCE_CURSOR_PREFIX,
    OntologySourceCursor,
    OntologySourceKey,
    mint_source_cursor,
    source_cursor_secret_from_env,
    source_key_from_row,
    verify_source_cursor,
)
from lineageweave.post_summary import parse_project_candidate_node_id

NOT_FOUND_NEIGHBORHOOD_CODES = frozenset(
    {"focus_hidden", "focus_not_visible", "unknown_node_type", "dangling_endpoint"}
)


class _LoadedFactWindow(list[NeighborhoodFact]):
    """Bounded fact list plus whether the SQL source window was exhausted."""

    def __init__(
        self,
        facts: Sequence[NeighborhoodFact] = (),
        *,
        truncated: bool = False,
        last_source_key: OntologySourceKey | None = None,
        source_keys_by_edge: Mapping[
            tuple[str, str, str, str, str], OntologySourceKey
        ] | None = None,
    ) -> None:
        super().__init__(facts)
        self.truncated = truncated
        self.last_source_key = last_source_key
        self.source_keys_by_edge = dict(source_keys_by_edge or {})


def neighborhood_error_http_status(error: OntologyNeighborhoodError) -> int:
    """Map a fail-closed assembler error onto an HTTP status.

    Next action: return this status from GET /api/ontology/neighborhood
    and name the buyer's next visible focus rather than leaking counts.
    """
    if error.code in NOT_FOUND_NEIGHBORHOOD_CODES:
        return 404
    return 422


def neighborhood_error_detail(error: OntologyNeighborhoodError) -> str:
    """Return a stable detail that does not reveal focus-node existence.

    Hidden, missing, and dangling focus nodes are intentionally indistinguishable
    at the HTTP boundary. Next action: let the buyer choose another authorized
    focus instead of probing catalog membership through response details.
    """
    if error.code in NOT_FOUND_NEIGHBORHOOD_CODES:
        return "focus node is unavailable"
    return str(error)


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
    *,
    knowledge_cutoff: datetime | None = None,
    snapshot_at: datetime | None = None,
) -> list[str]:
    """Visible evidence posts that authorize the requested focus node."""
    if focus_node_type_code == NODE_POST:
        # Safe SQL: eligibility is an immutable schema fragment; id is bound.
        row = await conn.fetchrow(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            f"""
            select post_id, visibility_code, corporate_entity_id, process_unit_id
              from source_post
             where post_id = $1
               and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')}
               and ($2::timestamptz is null or created_at <= $2::timestamptz)
               and ($3::timestamptz is null or created_at <= $3::timestamptz)
            """,
            focus_node_id,
            knowledge_cutoff,
            snapshot_at,
        )
        if row is None:
            return []
        return [str(row["post_id"])] if can_see_post(row) else []
    candidate_post_ids: list[str] | None = None
    if focus_node_type_code == NODE_PERSON:
        candidate_post_ids = await visible_mention_post_ids(conn, focus_node_id, can_see_post)
    elif focus_node_type_code == NODE_CORPORATE_ENTITY:
        candidate_post_ids = await visible_affiliation_post_ids(conn, focus_node_id, can_see_post)
    elif focus_node_type_code == NODE_TEAM:
        candidate_post_ids = await visible_team_mention_post_ids(conn, focus_node_id, can_see_post)
    if candidate_post_ids is not None:
        if knowledge_cutoff is None and snapshot_at is None:
            return candidate_post_ids
        rows = await conn.fetch(
            """
            select post_id
              from source_post
             where post_id = any($1::uuid[])
               and ($2::timestamptz is null or created_at <= $2::timestamptz)
               and ($3::timestamptz is null or created_at <= $3::timestamptz)
            """,
            candidate_post_ids,
            knowledge_cutoff,
            snapshot_at,
        )
        admitted = {str(row["post_id"]) for row in rows}
        return [post_id for post_id in candidate_post_ids if post_id in admitted]
    if focus_node_type_code == NODE_PROJECT:
        project_post_id, project_key = parse_project_candidate_node_id(focus_node_id)
        # Safe SQL: eligibility is an immutable schema fragment and the alias is
        # fixed here; all request-derived values remain asyncpg parameters.
        project_posts_sql = f"""
            select post.post_id, post.visibility_code, post.corporate_entity_id,
                   post.process_unit_id
              from post_project_mention mention
              join source_post post on post.post_id = mention.post_id
             where mention.post_id = $1::uuid
               and mention.project_key = $2
               and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}
               and ($3::timestamptz is null
                    or greatest(post.created_at, mention.created_at) <= $3::timestamptz)
               and ($4::timestamptz is null
                    or greatest(post.created_at, mention.created_at) <= $4::timestamptz)
            """
        rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            project_posts_sql,
            project_post_id,
            project_key,
            knowledge_cutoff,
            snapshot_at,
        )
        return [str(row["post_id"]) for row in rows if can_see_post(row)]
    if focus_node_type_code == NODE_OCCUPATIONAL_CONSTRUCT:
        query = f"""
            select post.post_id, post.visibility_code,
                   post.corporate_entity_id, post.process_unit_id
              from post_occupational_construct_assertion assertion
              join source_post post on post.post_id = assertion.post_id
             where assertion.construct_id = $1::uuid
               and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}
               and ($2::timestamptz is null
                    or greatest(post.created_at, assertion.generated_at) <= $2::timestamptz)
               and ($3::timestamptz is null
                    or greatest(post.created_at, assertion.generated_at) <= $3::timestamptz)
        """
        rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            query,
            focus_node_id,
            knowledge_cutoff,
            snapshot_at,
        )
        return [str(row["post_id"]) for row in rows if can_see_post(row)]
    raise OntologyNeighborhoodError("unknown_node_type", f"unknown node type {focus_node_type_code!r}")


async def _visible_post_ids_by_nodes(
    conn: asyncpg.Connection,
    node_keys: set[tuple[str, str]],
    can_see_post: Callable[[asyncpg.Record], bool],
    *,
    knowledge_cutoff: datetime | None = None,
    snapshot_at: datetime | None = None,
) -> dict[tuple[str, str], list[str]]:
    """Load evidence visibility for all endpoint nodes in bounded type queries.

    The neighborhood can contain many endpoints. Grouping ids by node type
    preserves the same ABAC predicate as the single-node readers while
    preventing one database round trip per endpoint.
    """
    visible: dict[tuple[str, str], list[str]] = {key: [] for key in node_keys}
    ids_by_type = {
        node_type: sorted(node_id for candidate_type, node_id in node_keys if candidate_type == node_type)
        for node_type in KNOWN_NODE_TYPES
    }
    queries = (
        (
            NODE_POST,
            """
            select post.post_id, post.visibility_code,
                   post.corporate_entity_id, post.process_unit_id,
                   post.post_id as node_id
              from source_post post
             where post.post_id = any($1::uuid[])
               and {eligibility}
               and ($2::timestamptz is null or post.created_at <= $2::timestamptz)
               and ($3::timestamptz is null or post.created_at <= $3::timestamptz)
            """,
        ),
        (
            NODE_PERSON,
            """
            select post.post_id, post.visibility_code,
                   post.corporate_entity_id, post.process_unit_id,
                   mention.person_id as node_id
              from combined_post_person_mention mention
              join source_post post on post.post_id = mention.post_id
             where mention.person_id = any($1::uuid[])
               and {eligibility}
               and ($2::timestamptz is null or post.created_at <= $2::timestamptz)
               and ($3::timestamptz is null or post.created_at <= $3::timestamptz)
            """,
        ),
        (
            NODE_CORPORATE_ENTITY,
            """
            select distinct post.post_id, post.visibility_code,
                   post.corporate_entity_id, post.process_unit_id,
                   affiliation.affiliated_corporate_entity_id as node_id
              from person_affiliation affiliation
              join combined_post_person_mention mention
                on mention.person_id = affiliation.person_id
              join source_post post on post.post_id = mention.post_id
             where affiliation.affiliated_corporate_entity_id = any($1::uuid[])
               and {eligibility}
               and ($2::timestamptz is null or post.created_at <= $2::timestamptz)
               and ($3::timestamptz is null or post.created_at <= $3::timestamptz)
            union
            select distinct post.post_id, post.visibility_code,
                   post.corporate_entity_id, post.process_unit_id,
                   org_mention.corporate_entity_id as node_id
              from post_organization_mention org_mention
              join source_post post on post.post_id = org_mention.post_id
             where org_mention.corporate_entity_id = any($1::uuid[])
               and {eligibility}
               and ($2::timestamptz is null or post.created_at <= $2::timestamptz)
               and ($3::timestamptz is null or post.created_at <= $3::timestamptz)
            """,
        ),
        (
            NODE_TEAM,
            """
            select post.post_id, post.visibility_code,
                   post.corporate_entity_id, post.process_unit_id,
                   mention.team_id as node_id
              from post_team_mention mention
              join source_post post on post.post_id = mention.post_id
             where mention.team_id = any($1::uuid[])
               and {eligibility}
               and ($2::timestamptz is null or post.created_at <= $2::timestamptz)
               and ($3::timestamptz is null or post.created_at <= $3::timestamptz)
            """,
        ),
        (
            NODE_PROJECT,
            """
            select post.post_id, post.visibility_code,
                   post.corporate_entity_id, post.process_unit_id,
                   mention.post_id::text || '/' || mention.project_key as node_id
              from post_project_mention mention
              join source_post post on post.post_id = mention.post_id
             where mention.post_id::text || '/' || mention.project_key = any($1::text[])
               and {eligibility}
               and ($2::timestamptz is null
                    or greatest(post.created_at, mention.created_at) <= $2::timestamptz)
               and ($3::timestamptz is null
                    or greatest(post.created_at, mention.created_at) <= $3::timestamptz)
            """,
        ),
        (
            NODE_OCCUPATIONAL_CONSTRUCT,
            """
            select post.post_id, post.visibility_code,
                   post.corporate_entity_id, post.process_unit_id,
                   assertion.construct_id as node_id
              from post_occupational_construct_assertion assertion
              join source_post post on post.post_id = assertion.post_id
             where assertion.construct_id = any($1::uuid[])
               and {eligibility}
               and ($2::timestamptz is null
                    or greatest(post.created_at, assertion.generated_at) <= $2::timestamptz)
               and ($3::timestamptz is null
                    or greatest(post.created_at, assertion.generated_at) <= $3::timestamptz)
            """,
        ),
    )
    for node_type, template in queries:
        ids = ids_by_type[node_type]
        if not ids:
            continue
        query = template.format(eligibility=SOURCE_POST_ELIGIBILITY_SQL.format(alias="post"))
        rows = await conn.fetch(query, ids, knowledge_cutoff, snapshot_at)
        for row in rows:
            try:
                raw_node_id = row["node_id"]
            except (KeyError, IndexError, TypeError):
                raw_node_id = None
            if raw_node_id is None and len(ids) == 1:
                raw_node_id = ids[0]
            if raw_node_id is None:
                continue
            node_id = str(raw_node_id)
            key = (node_type, node_id)
            try:
                raw_post_id = row["post_id"]
            except (KeyError, IndexError, TypeError):
                raw_post_id = None
            if key in visible and raw_post_id is not None and can_see_post(row):
                visible[key].append(str(raw_post_id))
    return {key: list(dict.fromkeys(post_ids)) for key, post_ids in visible.items()}


async def focus_catalog_exists(
    conn: asyncpg.Connection, focus_node_type_code: str, focus_node_id: str
) -> bool:
    """True when the focus id exists in its governed relational source."""
    if focus_node_type_code == NODE_PROJECT:
        project_post_id, project_key = parse_project_candidate_node_id(focus_node_id)
        row = await conn.fetchrow(
            "select 1 from post_project_mention where post_id = $1::uuid and project_key = $2",
            project_post_id,
            project_key,
        )
        return row is not None
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
    if focus_node_type_code == NODE_OCCUPATIONAL_CONSTRUCT:
        row = await conn.fetchrow(
            "select 1 from occupational_construct where construct_id = $1", focus_node_id
        )
        return row is not None
    raise OntologyNeighborhoodError("unknown_node_type", f"unknown node type {focus_node_type_code!r}")


async def _load_facts(
    conn: asyncpg.Connection,
    visible_post_ids: list[str],
    *,
    focus_node_type_code: str = NODE_POST,
    focus_node_id: str = "",
    maximum_depth: int = DEFAULT_MAXIMUM_DEPTH,
    maximum_edges: int = DEFAULT_MAXIMUM_EDGES,
    knowledge_cutoff: datetime | None = None,
    snapshot_at: datetime | None = None,
    after_key: OntologySourceKey | None = None,
) -> _LoadedFactWindow:
    """Load one keyset page of cutoff-safe recursive facts for the focus node."""
    if not visible_post_ids:
        return _LoadedFactWindow()
    query_limit = maximum_edges + 1
    query = """
        with recursive candidate_facts as (
            select edge.source_node_type_code,
                   edge.source_node_id::text as source_node_id,
                   edge.target_node_type_code,
                   edge.target_node_id::text as target_node_id,
                   edge.edge_type_code,
                   'truth_observed'::text as truth_status_code,
                   greatest(edge.created_at, min(post.created_at)) as available_at,
                   array_agg(evidence.evidence_post_id::text order by evidence.evidence_post_id)
                       as evidence_ids
              from knowledge_graph_edge edge
              join knowledge_graph_edge_evidence evidence
                on evidence.knowledge_graph_edge_id = edge.knowledge_graph_edge_id
              join source_post post
                on post.post_id = evidence.evidence_post_id
             where evidence.evidence_post_id = any($1::uuid[])
               and ($6::timestamptz is null or post.created_at <= $6::timestamptz)
               and ($6::timestamptz is null or edge.created_at <= $6::timestamptz)
               and ($7::timestamptz is null or post.created_at <= $7::timestamptz)
               and ($7::timestamptz is null or edge.created_at <= $7::timestamptz)
             group by edge.source_node_type_code, edge.source_node_id,
                      edge.target_node_type_code, edge.target_node_id,
                      edge.edge_type_code
            union all
            select 'node_post'::text as source_node_type_code,
                   mention.post_id::text as source_node_id,
                   'node_project'::text as target_node_type_code,
                   mention.post_id::text || '/' || mention.project_key as target_node_id,
                   'edge_mention_project'::text as edge_type_code,
                   'truth_proposed'::text as truth_status_code,
                   greatest(post.created_at, mention.created_at) as available_at,
                   array[mention.post_id::text] as evidence_ids
              from post_project_mention mention
              join source_post post on post.post_id = mention.post_id
             where mention.post_id = any($1::uuid[])
               and ($6::timestamptz is null
                    or greatest(post.created_at, mention.created_at) <= $6::timestamptz)
               and ($7::timestamptz is null
                    or greatest(post.created_at, mention.created_at) <= $7::timestamptz)
            union all
            select 'node_post'::text as source_node_type_code,
                   assertion.post_id::text as source_node_id,
                   'node_occupational_construct'::text as target_node_type_code,
                   assertion.construct_id::text as target_node_id,
                   'edge_supports_occupational_construct'::text as edge_type_code,
                   min(assertion.truth_status_code)::text as truth_status_code,
                   min(greatest(post.created_at, assertion.generated_at)) as available_at,
                   array[assertion.post_id::text] as evidence_ids
              from post_occupational_construct_assertion assertion
              join source_post post on post.post_id = assertion.post_id
             where assertion.post_id = any($1::uuid[])
               and ($6::timestamptz is null
                    or greatest(post.created_at, assertion.generated_at) <= $6::timestamptz)
               and ($7::timestamptz is null
                    or greatest(post.created_at, assertion.generated_at) <= $7::timestamptz)
             group by assertion.post_id, assertion.construct_id
            having count(distinct assertion.truth_status_code) = 1
        ), reachable(node_type_code, node_id, depth) as (
            values ($2::text, $3::text, 0)
            union
            select case when candidate.source_node_type_code = reachable.node_type_code
                        and candidate.source_node_id = reachable.node_id
                        then candidate.target_node_type_code
                        else candidate.source_node_type_code end,
                   case when candidate.source_node_type_code = reachable.node_type_code
                        and candidate.source_node_id = reachable.node_id
                        then candidate.target_node_id
                        else candidate.source_node_id end,
                   reachable.depth + 1
              from candidate_facts candidate
              join reachable
                on (candidate.source_node_type_code = reachable.node_type_code
                    and candidate.source_node_id = reachable.node_id)
                or (candidate.target_node_type_code = reachable.node_type_code
                    and candidate.target_node_id = reachable.node_id)
             where reachable.depth < $4::integer
        ), ranked as (
            select candidate.source_node_type_code,
                   candidate.source_node_id,
                   candidate.target_node_type_code,
                   candidate.target_node_id,
                   candidate.edge_type_code,
                   candidate.truth_status_code,
                   candidate.available_at,
                   candidate.evidence_ids,
                   min(reachable.depth) as hop_depth
              from candidate_facts candidate
              join reachable
                on ((candidate.source_node_type_code = reachable.node_type_code
                     and candidate.source_node_id = reachable.node_id)
                 or (candidate.target_node_type_code = reachable.node_type_code
                     and candidate.target_node_id = reachable.node_id))
               and reachable.depth < $4::integer
             group by candidate.source_node_type_code,
                      candidate.source_node_id,
                      candidate.target_node_type_code,
                      candidate.target_node_id,
                      candidate.edge_type_code,
                      candidate.truth_status_code,
                      candidate.available_at,
                      candidate.evidence_ids
        )
        select source_node_type_code,
               source_node_id,
               target_node_type_code,
               target_node_id,
               edge_type_code,
               truth_status_code,
               available_at,
               evidence_ids,
               hop_depth
          from ranked
         where $8::integer is null
            or (hop_depth, edge_type_code, source_node_type_code, source_node_id,
                target_node_type_code, target_node_id)
               > ($8::integer, $9::text, $10::text, $11::text, $12::text, $13::text)
         order by hop_depth,
                  edge_type_code,
                  source_node_type_code,
                  source_node_id,
                  target_node_type_code,
                  target_node_id
         limit $5::integer
        """
    arguments: list[object] = [
        visible_post_ids,
        focus_node_type_code,
        focus_node_id,
        maximum_depth,
        query_limit,
        knowledge_cutoff,
        snapshot_at,
        None if after_key is None else after_key.hop_depth,
        None if after_key is None else after_key.edge_type_code,
        None if after_key is None else after_key.source_node_type_code,
        None if after_key is None else after_key.source_node_id,
        None if after_key is None else after_key.target_node_type_code,
        None if after_key is None else after_key.target_node_id,
    ]
    rows = await conn.fetch(query, *arguments)
    source_truncated = len(rows) >= query_limit
    page_rows = list(rows[:maximum_edges])
    facts: list[NeighborhoodFact] = []
    source_keys_by_edge: dict[tuple[str, str, str, str, str], OntologySourceKey] = {}
    for row in page_rows:
        try:
            truth_status_code = row["truth_status_code"]
        except (KeyError, IndexError):
            truth_status_code = "truth_observed"
        fact = fact_from_knowledge_graph_edge(
                source_node_type_code=row["source_node_type_code"],
                source_node_id=str(row["source_node_id"]),
                target_node_type_code=row["target_node_type_code"],
                target_node_id=str(row["target_node_id"]),
                edge_type_code=row["edge_type_code"],
                recorded_at=row["available_at"],
                evidence_references=tuple(row["evidence_ids"] or ()),
                provenance_reference=(
                    "post_project_mention"
                    if row["edge_type_code"] == EDGE_MENTION_PROJECT
                    else (
                        "post_occupational_construct_assertion"
                        if row["edge_type_code"] == EDGE_SUPPORTS_OCCUPATIONAL_CONSTRUCT
                        else "knowledge_graph_edge"
                    )
                ),
                truth_status_code=truth_status_code,
            )
        try:
            hop_depth = row["hop_depth"]
        except (KeyError, IndexError):
            hop_depth = None
        source_key = source_key_from_row(row)
        source_order_key = (
            source_key.hop_depth,
            source_key.edge_type_code,
            source_key.source_node_type_code,
            source_key.source_node_id,
            source_key.target_node_type_code,
            source_key.target_node_id,
        )
        facts.append(
            replace(
                fact,
                source_hop_depth=None if hop_depth is None else int(hop_depth),
                source_order_key=source_order_key,
            )
        )
        source_keys_by_edge[
            (
                fact.property_code,
                fact.source_node_type_code,
                fact.source_node_id,
                fact.target_node_type_code,
                fact.target_node_id,
            )
        ] = source_key
    last_key = source_key_from_row(page_rows[-1]) if page_rows else None
    return _LoadedFactWindow(
        facts,
        truncated=source_truncated,
        last_source_key=last_key,
        source_keys_by_edge=source_keys_by_edge,
    )


async def _load_skos_facts(
    conn: asyncpg.Connection, corporate_entity_ids: list[str]
) -> list[NeighborhoodFact]:
    """Load governed corporate hierarchy facts for visible entities."""
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


async def _load_labels(
    conn: asyncpg.Connection,
    facts: list[NeighborhoodFact],
    *,
    knowledge_cutoff: datetime | None = None,
    snapshot_at: datetime | None = None,
    focus_node_type_code: str | None = None,
    focus_node_id: str | None = None,
    visible_post_ids: list[str] | None = None,
) -> dict[tuple[str, str], str]:
    """Load only non-empty buyer-visible labels for fact endpoints."""
    ids_by_type = _node_ids_by_type(facts, focus_node_type_code, focus_node_id)
    person_ids = ids_by_type[NODE_PERSON]
    post_ids = ids_by_type[NODE_POST]
    corp_ids = ids_by_type[NODE_CORPORATE_ENTITY]
    team_ids = ids_by_type[NODE_TEAM]
    project_ids = ids_by_type[NODE_PROJECT]
    construct_ids = ids_by_type[NODE_OCCUPATIONAL_CONSTRUCT]
    labels: dict[tuple[str, str], str] = {}
    if person_ids:
        for row in await conn.fetch(
            "select person_id, person_name from cataloged_person where person_id = any($1::uuid[])",
            person_ids,
        ):
            if row["person_name"]:
                labels[(NODE_PERSON, str(row["person_id"]))] = str(row["person_name"])
    if post_ids:
        for row in await conn.fetch(
            "select post_id, post_title from source_post where post_id = any($1::uuid[])",
            post_ids,
        ):
            if row["post_title"]:
                labels[(NODE_POST, str(row["post_id"]))] = str(row["post_title"])
    if corp_ids:
        for row in await conn.fetch(
            "select corporate_entity_id, entity_name from corporate_entity "
            "where corporate_entity_id = any($1::uuid[])",
            corp_ids,
        ):
            if row["entity_name"]:
                labels[(NODE_CORPORATE_ENTITY, str(row["corporate_entity_id"]))] = str(row["entity_name"])
    if team_ids:
        for row in await conn.fetch(
            "select team_id, team_name from cataloged_team where team_id = any($1::uuid[])",
            team_ids,
        ):
            if row["team_name"]:
                labels[(NODE_TEAM, str(row["team_id"]))] = str(row["team_name"])
    if project_ids:
        evidence_post_ids = sorted(
            {
                post_id
                for fact in facts
                for post_id in fact.evidence_references
                if fact.source_node_type_code == NODE_PROJECT
                or fact.target_node_type_code == NODE_PROJECT
            }
        )
        if evidence_post_ids:
            for row in await conn.fetch(
                """
                select mention.post_id::text || '/' || mention.project_key as node_id,
                       mention.project_name as display_label
                  from post_project_mention mention
                  join source_post post on post.post_id = mention.post_id
                 where mention.post_id::text || '/' || mention.project_key = any($1::text[])
                   and mention.post_id = any($2::uuid[])
                   and ($3::timestamptz is null
                        or greatest(post.created_at, mention.created_at) <= $3::timestamptz)
                   and ($4::timestamptz is null
                        or greatest(post.created_at, mention.created_at) <= $4::timestamptz)
                 group by mention.post_id, mention.project_key, mention.project_name
                """,
                project_ids,
                evidence_post_ids,
                knowledge_cutoff,
                snapshot_at,
            ):
                if row["display_label"]:
                    labels[(NODE_PROJECT, str(row["node_id"]))] = str(
                        row["display_label"]
                    )
    if construct_ids and visible_post_ids:
        for row in await conn.fetch(
            """
            select construct.construct_id, construct.preferred_label
              from occupational_construct construct
             where construct.construct_id = any($1::uuid[])
               and exists (
                   select 1
                     from post_occupational_construct_assertion assertion
                     join source_post post on post.post_id = assertion.post_id
                    where assertion.construct_id = construct.construct_id
                      and assertion.post_id = any($2::uuid[])
                      and ($3::timestamptz is null
                           or greatest(post.created_at, assertion.generated_at) <= $3::timestamptz)
                      and ($4::timestamptz is null
                           or greatest(post.created_at, assertion.generated_at) <= $4::timestamptz)
               )
            """,
            construct_ids,
            visible_post_ids,
            knowledge_cutoff,
            snapshot_at,
        ):
            if row["preferred_label"]:
                labels[(NODE_OCCUPATIONAL_CONSTRUCT, str(row["construct_id"]))] = str(
                    row["preferred_label"]
                )
    return labels


def _node_ids_by_type(
    facts: list[NeighborhoodFact],
    focus_node_type_code: str | None = None,
    focus_node_id: str | None = None,
) -> dict[str, list[str]]:
    """Collect unique catalog ids needed by labels and metadata queries."""
    ids_by_type = {node_type: [] for node_type in KNOWN_NODE_TYPES}
    seen: set[tuple[str, str]] = set()
    endpoints = [
        (fact.source_node_type_code, fact.source_node_id)
        for fact in facts
    ] + [
        (fact.target_node_type_code, fact.target_node_id)
        for fact in facts
    ]
    if focus_node_type_code and focus_node_id:
        endpoints.append((focus_node_type_code, focus_node_id))
    for node_type, node_id in endpoints:
        key = (node_type, node_id)
        if node_type in ids_by_type and key not in seen:
            ids_by_type[node_type].append(node_id)
            seen.add(key)
    return ids_by_type


async def _load_node_metadata(
    conn: asyncpg.Connection,
    facts: list[NeighborhoodFact],
    *,
    focus_node_type_code: str,
    focus_node_id: str,
) -> dict[tuple[str, str], OntologyNodeMetadata]:
    """Load node timestamps from catalogs without deriving them from edges."""
    ids_by_type = _node_ids_by_type(facts, focus_node_type_code, focus_node_id)
    metadata: dict[tuple[str, str], OntologyNodeMetadata] = {}
    queries = (
        (NODE_PERSON, "select person_id, created_at from cataloged_person where person_id = any($1::uuid[])", "person_id"),
        (NODE_POST, "select post_id, created_at from source_post where post_id = any($1::uuid[])", "post_id"),
        (NODE_CORPORATE_ENTITY, "select corporate_entity_id, created_at from corporate_entity where corporate_entity_id = any($1::uuid[])", "corporate_entity_id"),
        (NODE_TEAM, "select team_id, created_at from cataloged_team where team_id = any($1::uuid[])", "team_id"),
    )
    for node_type, query, id_column in queries:
        ids = ids_by_type[node_type]
        if not ids:
            continue
        for row in await conn.fetch(query, ids):
            metadata[(node_type, str(row[id_column]))] = OntologyNodeMetadata(
                recorded_at=row["created_at"]
            )
    return metadata


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
                "recorded_at": node.recorded_at.isoformat() if node.recorded_at else None,
                "evidence_count": node.evidence_count,
                "shape_code": node.shape_code,
            }
            for node in neighborhood.nodes
        ],
        "edges": [
            {
                "edge_id": edge.edge_id,
                "source_node_type_code": edge.source_node_type_code,
                "source_node_id": edge.source_node_id,
                "target_node_type_code": edge.target_node_type_code,
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
        "voice_assignments": [
            {
                "post_id": assignment.post_id,
                "voice_type_code": assignment.voice_type_code,
                "voice_type_iri": assignment.voice_type_iri,
                "voice_type_label": assignment.voice_type_label,
                "is_primary": assignment.is_primary,
                "truth_status_code": assignment.truth_status_code,
                "recorded_at": assignment.recorded_at.isoformat(),
                "effective_from": assignment.effective_from.isoformat(),
                "effective_to": assignment.effective_to.isoformat()
                if assignment.effective_to
                else None,
                "provenance_reference": assignment.provenance_reference,
                "evidence_post_id": assignment.evidence_post_id,
            }
            for assignment in neighborhood.voice_assignments
        ],
        "exact_value_rows": list(neighborhood.exact_value_rows()),
        "jsonld": neighborhood.jsonld_document(),
    }


async def _load_voice_assignments(
    conn: asyncpg.Connection,
    post_ids: Sequence[str],
    *,
    knowledge_cutoff: datetime | None,
    snapshot_at: datetime,
) -> tuple[OntologyVoiceAssignment, ...]:
    """Load qualified voices only for posts admitted to the visible neighborhood."""
    if not post_ids:
        return ()
    rows = await conn.fetch(
        """
        select voice.post_id, voice.voice_type_code, lookup.lookup_label, voice.is_primary,
               voice.truth_status_code, voice.recorded_at,
               voice.effective_from, voice.effective_to,
               case when evidence.node_id = any($1::uuid[]) then evidence.node_id end
                   as evidence_post_id
          from source_post_voice voice
          join common_lookup_value lookup
            on lookup.lookup_category = 'voc_type'
           and lookup.lookup_code = voice.voice_type_code
          left join provenance_assertion assertion
            on assertion.assertion_id = voice.provenance_assertion_id
          left join provenance_resource_binding evidence
            on evidence.resource_id = assertion.object_resource_id
           and evidence.node_type_code = 'node_post'
         where voice.post_id = any($1::uuid[])
           and (voice.is_primary or evidence.node_id = any($1::uuid[]))
           and (($2::timestamptz is null and voice.effective_to is null)
                or ($2::timestamptz is not null
                    and voice.effective_from <= $2
                    and (voice.effective_to is null or $2 < voice.effective_to)))
           and voice.effective_from <= coalesce($2::timestamptz, $3::timestamptz)
           and (
               voice.effective_to is null
               or coalesce($2::timestamptz, $3::timestamptz) < voice.effective_to
           )
           and voice.recorded_at <= $3::timestamptz
         order by voice.post_id, voice.is_primary desc,
                  lookup.display_order, voice.voice_type_code
        """,
        list(post_ids),
        knowledge_cutoff,
        snapshot_at,
    )
    assignments: list[OntologyVoiceAssignment] = []
    for row in rows:
        voice_type_iri = iri_for_lookup_code(row["voice_type_code"])
        if voice_type_iri is None:
            raise OntologyNeighborhoodError(
                "unknown_property", "voice type has no published ontology term"
            )
        assignments.append(
            OntologyVoiceAssignment(
                post_id=str(row["post_id"]),
                voice_type_code=row["voice_type_code"],
                voice_type_iri=voice_type_iri,
                voice_type_label=row["lookup_label"],
                is_primary=row["is_primary"],
                truth_status_code=row["truth_status_code"],
                recorded_at=row["recorded_at"],
                effective_from=row["effective_from"],
                effective_to=row["effective_to"],
                provenance_reference=(
                    "Evidence-backed additional voice"
                    if not row["is_primary"]
                    else "Imported primary voice"
                ),
                evidence_post_id=(
                    str(row["evidence_post_id"])
                    if row["evidence_post_id"] is not None
                    else None
                ),
            )
        )
    return tuple(assignments)


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
    source_cursor_secret: str | None = None,
    source_cursor_scope: str | None = None,
) -> OntologyNeighborhood:
    """Assemble the authorized neighborhood for one focus node."""
    if focus_node_type_code not in KNOWN_NODE_TYPES:
        raise OntologyNeighborhoodError(
            "unknown_node_type", f"unknown node type {focus_node_type_code!r}"
        )
    if not focus_node_id or focus_node_id.strip() != focus_node_id:
        raise OntologyNeighborhoodError("invalid_focus_id", "focus node id is empty or malformed")
    if focus_node_type_code == NODE_PROJECT:
        try:
            parse_project_candidate_node_id(focus_node_id)
        except ValueError as exc:
            raise OntologyNeighborhoodError(
                "invalid_focus_id", "project focus id is not a post-scoped candidate id"
            ) from exc
    else:
        if not _is_uuid(focus_node_id):
            raise OntologyNeighborhoodError("invalid_focus_id", "focus node id is not a UUID")
        focus_node_id = str(UUID(focus_node_id))
    if not await focus_catalog_exists(conn, focus_node_type_code, focus_node_id):
        raise OntologyNeighborhoodError("unknown_node_type", "focus node not found")
    secret = source_cursor_secret_from_env(source_cursor_secret)
    snapshot_at = datetime.now(timezone.utc)
    after_key: OntologySourceKey | None = None
    source_cursor_claims: OntologySourceCursor | None = None
    assembler_cursor = cursor
    if cursor is not None and cursor.startswith(SOURCE_CURSOR_PREFIX):
        assembler_cursor = None
        if secret is None or not source_cursor_scope:
            raise OntologyNeighborhoodError("malformed_cursor", "source cursor is unavailable")
        source_cursor_claims = verify_source_cursor(
            cursor,
            secret=secret,
            user_account_id=source_cursor_scope,
            focus_node_type_code=focus_node_type_code,
            focus_node_id=focus_node_id,
            knowledge_cutoff=knowledge_cutoff,
            maximum_depth=maximum_depth,
            maximum_nodes=maximum_nodes,
            maximum_edges=maximum_edges,
            allowed_property_codes=allowed_property_codes,
            visible_post_ids=(),
            validate_eligibility=False,
        )
        snapshot_at = source_cursor_claims.snapshot_at
        after_key = source_cursor_claims.last_key
    elif cursor is not None and not cursor.startswith("after:"):
        raise OntologyNeighborhoodError("malformed_cursor", "cursor must be an opaque after: or source token")
    visible_post_ids = await visible_post_ids_for_focus(
        conn,
        focus_node_type_code,
        focus_node_id,
        can_see_post,
        knowledge_cutoff=knowledge_cutoff,
        snapshot_at=snapshot_at,
    )
    if not visible_post_ids:
        raise OntologyNeighborhoodError("focus_not_visible", "focus node is not visible")
    fact_window = await _load_facts(
        conn,
        visible_post_ids,
        focus_node_type_code=focus_node_type_code,
        focus_node_id=focus_node_id,
        maximum_depth=maximum_depth,
        maximum_edges=HARD_MAXIMUM_EDGES,
        knowledge_cutoff=knowledge_cutoff,
        snapshot_at=snapshot_at,
    )
    facts = list(fact_window)
    expansion_truncated = bool(getattr(fact_window, "truncated", False))
    expanded_source_keys = dict(getattr(fact_window, "source_keys_by_edge", {}))
    loaded_post_ids = set(visible_post_ids)
    visible_by_node: dict[tuple[str, str], list[str]] = {}
    for _ in range(maximum_depth):
        endpoint_keys = {
            (fact.source_node_type_code, fact.source_node_id)
            for fact in facts
        } | {
            (fact.target_node_type_code, fact.target_node_id)
            for fact in facts
        }
        if not endpoint_keys:
            break
        visible_by_node = await _visible_post_ids_by_nodes(
            conn, endpoint_keys, can_see_post,
            knowledge_cutoff=knowledge_cutoff, snapshot_at=snapshot_at,
        )
        candidate_post_ids = loaded_post_ids | {
            post_id
            for post_ids in visible_by_node.values()
            for post_id in post_ids
        }
        if candidate_post_ids == loaded_post_ids:
            break
        expanded_window = await _load_facts(
            conn,
            sorted(candidate_post_ids),
            focus_node_type_code=focus_node_type_code,
            focus_node_id=focus_node_id,
            maximum_depth=maximum_depth,
            maximum_edges=HARD_MAXIMUM_EDGES,
            knowledge_cutoff=knowledge_cutoff,
            snapshot_at=snapshot_at,
        )
        expansion_truncated = expansion_truncated or bool(getattr(expanded_window, "truncated", False))
        expanded_source_keys.update(getattr(expanded_window, "source_keys_by_edge", {}))
        for fact in expanded_window:
            if fact not in facts:
                facts.append(fact)
        loaded_post_ids = candidate_post_ids
    else:
        # The last expansion can add endpoints after the final visibility pass.
        # Recheck them before the authorization cache turns an unseen endpoint
        # into a silently dropped edge.
        endpoint_keys = {
            (fact.source_node_type_code, fact.source_node_id)
            for fact in facts
        } | {
            (fact.target_node_type_code, fact.target_node_id)
            for fact in facts
        }
        if endpoint_keys:
            visible_by_node = await _visible_post_ids_by_nodes(
                conn, endpoint_keys, can_see_post,
                knowledge_cutoff=knowledge_cutoff, snapshot_at=snapshot_at,
            )
    frozen_posts = sorted(loaded_post_ids)
    if source_cursor_claims is not None:
        if secret is None or source_cursor_scope is None:
            raise OntologyNeighborhoodError("malformed_cursor", "source cursor is unavailable")
        source_cursor_claims = verify_source_cursor(
            cursor,
            secret=secret,
            user_account_id=source_cursor_scope,
            focus_node_type_code=focus_node_type_code,
            focus_node_id=focus_node_id,
            knowledge_cutoff=knowledge_cutoff,
            maximum_depth=maximum_depth,
            maximum_nodes=maximum_nodes,
            maximum_edges=maximum_edges,
            allowed_property_codes=allowed_property_codes,
            visible_post_ids=frozen_posts,
            validate_eligibility=True,
        )
        snapshot_at = source_cursor_claims.snapshot_at
        after_key = source_cursor_claims.last_key
    page_window = fact_window
    if after_key is not None:
        page_window = await _load_facts(
        conn,
        frozen_posts,
        focus_node_type_code=focus_node_type_code,
        focus_node_id=focus_node_id,
        maximum_depth=maximum_depth,
        maximum_edges=maximum_edges,
        knowledge_cutoff=knowledge_cutoff,
            snapshot_at=snapshot_at,
            after_key=after_key,
        )
    else:
        page_window = _LoadedFactWindow(
            facts,
            truncated=expansion_truncated,
            last_source_key=getattr(fact_window, "last_source_key", None),
            source_keys_by_edge=expanded_source_keys,
        )
    facts = list(page_window)
    source_truncated = bool(getattr(page_window, "truncated", False))
    last_source_key = getattr(page_window, "last_source_key", None)
    source_keys_by_edge = getattr(page_window, "source_keys_by_edge", {})
    endpoint_keys = {
        (fact.source_node_type_code, fact.source_node_id)
        for fact in facts
    } | {
        (fact.target_node_type_code, fact.target_node_id)
        for fact in facts
    }
    if endpoint_keys:
        # Continuation pages can introduce endpoints absent from the first
        # window. Rebuild the authorization cache for the actual page before
        # discarding unseen relations.
        visible_by_node = await _visible_post_ids_by_nodes(
            conn, endpoint_keys, can_see_post,
            knowledge_cutoff=knowledge_cutoff, snapshot_at=snapshot_at,
        )
    corp_ids = [
        fact.source_node_id if fact.source_node_type_code == NODE_CORPORATE_ENTITY else fact.target_node_id
        for fact in facts
        if NODE_CORPORATE_ENTITY in {fact.source_node_type_code, fact.target_node_type_code}
    ]
    if focus_node_type_code == NODE_CORPORATE_ENTITY:
        corp_ids.append(focus_node_id)
    unique_corp_ids = list(dict.fromkeys(corp_ids))
    skos_facts = await _load_skos_facts(conn, unique_corp_ids)
    facts.extend(skos_facts)
    parent_keys = {
        (fact.target_node_type_code, fact.target_node_id)
        for fact in skos_facts
        if fact.property_code == PROPERTY_SKOS_BROADER
    }
    missing_parent_keys = {key for key in parent_keys if key not in visible_by_node}
    if missing_parent_keys:
        parent_visible = await _visible_post_ids_by_nodes(
            conn, missing_parent_keys, can_see_post,
            knowledge_cutoff=knowledge_cutoff, snapshot_at=snapshot_at,
        )
        visible_by_node.update(parent_visible)
    hidden_node_keys: set[str] = set()
    authorized_facts: list[NeighborhoodFact] = []
    visibility_cache: dict[tuple[str, str], bool] = {
        (focus_node_type_code, focus_node_id): True,
    }
    visibility_cache.update(
        {
            key: bool(post_ids)
            for key, post_ids in visible_by_node.items()
            if key != (focus_node_type_code, focus_node_id)
        }
    )
    for fact in facts:
        endpoints = (
            (fact.source_node_type_code, fact.source_node_id),
            (fact.target_node_type_code, fact.target_node_id),
        )
        authorized = True
        for node_type, node_id in endpoints:
            node_key = (node_type, node_id)
            if node_key not in visibility_cache:
                visibility_cache[node_key] = False
            if not visibility_cache[node_key]:
                hidden_node_keys.add(f"{node_type}:{node_id}")
                authorized = False
        if authorized:
            authorized_facts.append(fact)
    facts = authorized_facts
    labels = await _load_labels(
        conn,
        facts,
        knowledge_cutoff=knowledge_cutoff,
        snapshot_at=snapshot_at,
        focus_node_type_code=focus_node_type_code,
        focus_node_id=focus_node_id,
        visible_post_ids=frozen_posts,
    )
    if hasattr(conn, "fetchval"):
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
        elif focus_node_type_code == NODE_TEAM:
            name = await conn.fetchval(
                "select team_name from cataloged_team where team_id = $1", focus_node_id
            )
            if name:
                labels[(NODE_TEAM, focus_node_id)] = name
    labels.setdefault((focus_node_type_code, focus_node_id), focus_node_id)
    facts = [
        fact
        for fact in facts
        if (fact.source_node_type_code, fact.source_node_id) in labels
        and (fact.target_node_type_code, fact.target_node_id) in labels
    ]
    node_metadata = await _load_node_metadata(
        conn,
        facts,
        focus_node_type_code=focus_node_type_code,
        focus_node_id=focus_node_id,
    )
    page_node_keys = {(focus_node_type_code, focus_node_id)}
    for fact in facts:
        page_node_keys.add((fact.source_node_type_code, fact.source_node_id))
        page_node_keys.add((fact.target_node_type_code, fact.target_node_id))
    neighborhood = assemble_ontology_neighborhood(
        focus_node_type_code=focus_node_type_code,
        focus_node_id=focus_node_id,
        facts=facts,
        labels=labels,
        hidden_node_keys=frozenset(hidden_node_keys),
        node_metadata=node_metadata,
        knowledge_cutoff=knowledge_cutoff,
        maximum_depth=maximum_depth,
        maximum_nodes=maximum_nodes,
        maximum_edges=maximum_edges,
        allowed_property_codes=allowed_property_codes,
        cursor=assembler_cursor,
        source_truncated=source_truncated,
    )
    visible_post_ids = tuple(
        node.node_id
        for node in getattr(neighborhood, "nodes", ())
        if node.node_type_code == NODE_POST
    )
    if visible_post_ids:
        neighborhood = replace(
            neighborhood,
            voice_assignments=await _load_voice_assignments(
                conn,
                visible_post_ids,
                knowledge_cutoff=knowledge_cutoff,
                snapshot_at=snapshot_at,
            ),
        )
    last_source_key = None
    neighborhood_edges = getattr(neighborhood, "edges", ())
    for edge in reversed(neighborhood_edges):
        source_key = source_keys_by_edge.get(
            (
                edge.property_code,
                edge.source_node_type_code,
                edge.source_node_id,
                edge.target_node_type_code,
                edge.target_node_id,
            )
        )
        if source_key is not None:
            last_source_key = source_key
            break
    if (
        secret is not None
        and source_cursor_scope
        and last_source_key is not None
        and neighborhood.truncated
        and (source_truncated or neighborhood.next_cursor is not None)
        and len(page_node_keys) <= maximum_nodes
        and neighborhood_edges
    ):
        return replace(
            neighborhood,
            next_cursor=mint_source_cursor(
                secret=secret,
                user_account_id=source_cursor_scope,
                focus_node_type_code=focus_node_type_code,
                focus_node_id=focus_node_id,
                knowledge_cutoff=knowledge_cutoff,
                maximum_depth=maximum_depth,
                maximum_nodes=maximum_nodes,
                maximum_edges=maximum_edges,
                allowed_property_codes=allowed_property_codes,
                last_key=last_source_key,
                snapshot_at=snapshot_at,
                visible_post_ids=frozen_posts,
            ),
        )
    return neighborhood
