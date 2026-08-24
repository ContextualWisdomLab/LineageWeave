"""Finds a post's Event-Lineage-linked posts -- direct (`post_lineage_edge`,
`lineageweave.reconstruct`'s output) and indirect (Knowledge Graph, shared
Keyman/organization, per `lineageweave.knowledge_graph`) -- and assembles
the chat's *retrieve* step (Lewis et al., 2020) from them: numbered source
documents `lineageweave.post_chat`'s reason-and-cite step answers from.
ABAC is re-checked per candidate post here, never trusted from the
Knowledge Graph traversal alone -- a KG edge says two posts are related,
not that the requesting account may see both.

`gather_global_chat_sources` (Global Ask, no starting post) also expands
its single best keyword match through the same `post_lineage_edge`
neighbors, so an answer speaks to a connected timeline rather than one
isolated snapshot -- it does not have a starting post to run the
Knowledge Graph's indirect random-walk expansion from, only the lineage
chain of its own top match.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import asyncpg

from lineageweave.image_content import ImageContentClient, NullImageContentClient
from lineageweave.knowledge_graph import (
    NODE_POST,
    adjacency_from_edges,
    node_key,
    parse_node_key,
    random_walk_with_restart,
    select_related_nodes,
)
from lineageweave.ontology import ontology_annotations
from lineageweave.post_chat import (
    CANONICAL_CHAT_QUESTION,
    CANONICAL_COMMITMENT_QUESTION,
    CANONICAL_INVOLVED_QUESTION,
    ChatSourceDocument,
    normalize_chat_question,
)
from lineageweave.post_content_normalization import normalize_post_body
from lineageweave.source_lineage_hints import source_lineage_hint_facts
from lineageweave.tepp_client import (
    TemporalContextEvent,
    TemporalContextRequest,
    TeppClient,
    TeppNotAvailable,
)

from .knowledge_graph import hydrate_related_nodes, load_visible_subgraph
from .post_eligibility import SOURCE_POST_READER_ELIGIBILITY_SQL


@dataclass(frozen=True)
class LinkedPostIds:
    """A post's Event-Lineage neighbors, kept distinguishable by how they
    were found -- direct thread relations vs. indirect shared-entity
    relations are different claims about why two posts are related.
    """

    direct: frozenset[str]
    indirect: frozenset[str]


async def _normalize_post_body_text(
    body: str,
    vision_client: ImageContentClient,
) -> str:
    """Normalize one source body without blocking the request event loop."""
    normalized = await asyncio.to_thread(
        normalize_post_body,
        body,
        vision_client=vision_client,
    )
    return normalized.text


async def _graph_facts_for_posts(
    conn: asyncpg.Connection,
    visible_post_ids: list[str],
) -> tuple[str, ...]:
    """Render persisted, ontology-annotated graph facts for visible posts.

    The evidence join is deliberate: a graph edge without a visible evidence
    post must never enter an LLM prompt. This is the chat-side trust boundary
    in addition to the post-level ABAC check.
    """
    if not visible_post_ids:
        return ()
    edge_rows = await conn.fetch(
        """
        select edge.source_node_type_code, edge.source_node_id,
               edge.target_node_type_code, edge.target_node_id,
               edge.edge_type_code, edge.edge_weight,
               array_agg(distinct evidence.evidence_post_id::text) as evidence_post_ids
          from knowledge_graph_edge edge
          join knowledge_graph_edge_evidence evidence
            on evidence.knowledge_graph_edge_id = edge.knowledge_graph_edge_id
         where evidence.evidence_post_id = any($1::uuid[])
         group by edge.source_node_type_code, edge.source_node_id,
                  edge.target_node_type_code, edge.target_node_id,
                  edge.edge_type_code, edge.edge_weight
         order by min(edge.edge_type_code), min(edge.source_node_id::text),
                  min(edge.target_node_id::text)
         limit 64
        """,
        visible_post_ids,
    )
    if not edge_rows:
        return ()

    endpoint_keys = {
        node_key(row["source_node_type_code"], str(row["source_node_id"]))
        for row in edge_rows
    }
    endpoint_keys.update(
        node_key(row["target_node_type_code"], str(row["target_node_id"]))
        for row in edge_rows
    )
    hydrated = await hydrate_related_nodes(
        conn, [(key, 1.0) for key in sorted(endpoint_keys)]
    )
    labels = {
        (item["node_type_code"], item["node_id"]): item
        for item in hydrated
    }

    facts: list[str] = []
    for row in edge_rows:
        source_type = row["source_node_type_code"]
        source_id = str(row["source_node_id"])
        target_type = row["target_node_type_code"]
        target_id = str(row["target_node_id"])
        source = labels.get((source_type, source_id))
        target = labels.get((target_type, target_id))
        if source is None or target is None:
            continue
        edge_annotation = ontology_annotations(row["edge_type_code"])
        ontology_iri = edge_annotation.get("ontology_iri")
        edge_name = row["edge_type_code"]
        if ontology_iri:
            edge_name = f"{edge_name} ({ontology_iri})"
        evidence_ids = ",".join(sorted(str(value) for value in row["evidence_post_ids"]))
        facts.append(
            f'{source_type} "{source["label"]}" '
            f'--{edge_name}--> {target_type} "{target["label"]}" '
            f"[evidence_post_id={evidence_ids}]"
        )
    return tuple(dict.fromkeys(facts))


_SOURCE_HINT_FIELDS = (
    ("source_system_code", "source system"),
    ("source_record_key", "source record key"),
    ("source_author_code", "source author code"),
    ("source_author_name", "source author name"),
    ("source_company_code", "source company code"),
    ("source_company_name", "source company name"),
    ("source_process_unit_code", "source business unit (PU)"),
    ("source_process_unit_name", "source business unit name (PU)"),
    ("source_sales_pool_code", "source sales pool"),
    ("source_sales_pool_name", "source sales pool name"),
    ("source_order_pool_code", "source order pool"),
    ("source_sales_order_code", "source sales order"),
    ("source_sales_order_item_number", "source sales order item"),
    ("source_inspection_point_code", "source inspection point"),
    ("source_customer_code", "source customer code"),
    ("source_customer_name", "source customer name"),
    ("source_project_code", "source project code"),
    ("source_project_name", "source project name"),
)

_GLOBAL_ASK_TERM_PATTERN = re.compile(r"[^\W_]+(?:-[^\W_]+)*", re.UNICODE)
_POST_CHAT_SOURCE_LIMIT = 8
_POST_CHAT_CANDIDATE_LIMIT = 32


def _source_hint_facts(row: Any) -> tuple[str, ...]:
    """Render raw source fields as explicitly weak, column-level evidence."""
    facts: list[str] = []
    for field_name, label in _SOURCE_HINT_FIELDS:
        value = row.get(field_name)
        if value is not None and str(value).strip():
            facts.append(
                f"{label}={str(value).strip()} [provenance=source_post.{field_name}; hint_only]"
            )
    return tuple(facts) + source_lineage_hint_facts(
        customer_code=row.get("source_customer_code"),
        order_pool_code=row.get("source_order_pool_code"),
        sales_order_code=row.get("source_sales_order_code"),
        sales_order_item_number=row.get("source_sales_order_item_number"),
        stage_code=row.get("source_stage_code"),
        detail_state_code=row.get("source_detail_state_code"),
        inspection_point_code=row.get("source_inspection_point_code"),
        deleted_flag=row.get("source_deleted_flag"),
    )


def _semantic_event_time(value: object) -> datetime | None:
    """Parse one explicit event clue instant; ambiguous/local times stay unavailable."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


async def _semantic_facts_for_posts(
    conn: asyncpg.Connection, post_ids: list[str]
) -> dict[str, tuple[str, ...]]:
    """Load persisted project/role/Keyman facts for already-visible posts."""
    if not post_ids:
        return {}
    rows = await conn.fetch(
        """
        select post_id::text as post_id,
               'project: ' || left(project_name, 200)
                   || ' | evidence: ' || left(evidence_text, 500)
                   || ' | ontology_iri: ' || ontology_iri
                   || ' | extraction_method: ' || extraction_method
                   || ' | confidence: ' || mention_confidence::text
                   || ' [provenance=post_project_mention]' as fact
          from post_project_mention
         where post_id = any($1::uuid[])
        union all
        select post_id::text as post_id,
               'actor: ' || left(actor_name, 200)
                   || ' | responsibility: ' || left(responsibility_text, 500)
                   || coalesce(' | affiliation: ' || left(affiliated_organization_name, 200), '')
                   || ' [provenance=post_summary_role]' as fact
          from post_summary_role
         where post_id = any($1::uuid[])
        union all
        select mention.post_id::text as post_id,
               'Keyman mention: ' || left(person.person_name, 200)
                   || coalesce(' | context: ' || left(mention.mention_context, 500), '')
                   || ' [provenance=post_person_mention]' as fact
          from post_person_mention mention
          join cataloged_person person on person.person_id = mention.person_id
         where mention.post_id = any($1::uuid[])
        union all
        select event.post_id::text as post_id,
               'event: ' || left(event.event_text, 300)
                   || coalesce(' | evidence: ' || left(event.evidence_text, 500), '')
                   || ' | ontology_iri: ' || event.ontology_iri
                   || ' | extraction_method: ' || event.extraction_method
                   || ' [provenance=post_summary_event]' as fact
          from post_summary_event event
         where event.post_id = any($1::uuid[])
        union all
        select clue.post_id::text as post_id,
               'event clue: ' || clue.clue_type_code
                   || ' | clue: ' || left(clue.clue_text, 300)
                   || coalesce(' | target: ' || left(clue.target_text, 200), '')
                   || coalesce(' | normalized: ' || left(clue.normalized_value_text, 200), '')
                   || coalesce(' | assertion: ' || clue.assertion_code, '')
                   || ' | evidence: ' || left(clue.evidence_text, 500)
                   || ' | ontology_iri: ' || clue.ontology_iri
                   || ' | extraction_method: ' || clue.extraction_method
                   || ' [provenance=post_summary_event_clue]' as fact
          from post_summary_event_clue clue
         where clue.post_id = any($1::uuid[])
        union all
        select observation.post_id::text as post_id,
               'quantitative: ' || left(observation.label_text, 200)
                   || ' | value: ' || left(observation.raw_value_text, 200)
                   || coalesce(' | quantity: ' || observation.quantity_numeric::text || ' ' || observation.quantity_unit_code, '')
                   || ' | evidence: ' || left(observation.evidence_text, 500)
                   || ' | ontology_iri: ' || observation.ontology_iri
                   || ' | extraction_method: ' || observation.extraction_method
                   || ' [provenance=post_summary_quantitative_observation]' as fact
          from post_summary_quantitative_observation observation
         where observation.post_id = any($1::uuid[])
        union all
        select fact.post_id::text as post_id,
               'source fact: ' || left(fact.label_text, 200)
                   || ' | value: ' || left(fact.value_text, 500)
                   || coalesce(' | normalized_value: ' || left(fact.normalized_value_text, 200), '')
                   || coalesce(' | normalized_date: ' || fact.normalized_date::text, '')
                   || coalesce(' | assertion: ' || fact.assertion_code, '')
                   || ' | evidence: ' || left(fact.evidence_text, 500)
                   || ' | ontology_iri: ' || fact.ontology_iri
                   || ' | extraction_method: ' || fact.extraction_method
                   || ' [provenance=post_summary_source_fact]' as fact
          from post_summary_source_fact fact
         where fact.post_id = any($1::uuid[])
        union all
        select relation.post_id::text as post_id,
               'semantic relation: ' || left(relation.subject_name, 200)
                   || ' --' || relation.predicate_code || '--> '
                   || left(relation.object_name, 200)
                   || ' | evidence: ' || left(relation.evidence_text, 500)
                   || ' | confidence: ' || relation.relation_confidence::text
                   || ' [provenance=post_summary_semantic_relationship]' as fact
          from post_summary_semantic_relationship relation
         where relation.post_id = any($1::uuid[])
         order by post_id, fact
        """,
        post_ids,
    )
    facts: dict[str, list[str]] = {}
    for row in rows:
        facts.setdefault(str(row["post_id"]), []).append(row["fact"])
    return {post_id: tuple(dict.fromkeys(values)) for post_id, values in facts.items()}


async def find_linked_post_ids(
    conn: asyncpg.Connection,
    post_id: str,
    can_see_post: Callable[[asyncpg.Record], bool],
) -> LinkedPostIds:
    """Both link kinds for `post_id`, NOT yet ABAC-filtered -- callers must
    check `can_see_post` on each id before showing or using it as chat
    context.
    """
    direct_rows = await conn.fetch(
        "select child_post_id as other_id from post_lineage_edge where parent_post_id = $1 "
        "union select parent_post_id as other_id from post_lineage_edge where child_post_id = $1",
        post_id,
    )
    direct_ids = frozenset(str(row["other_id"]) for row in direct_rows)

    # load_visible_subgraph only loads edges among an ALREADY-KNOWN post
    # set (see backend/app/knowledge_graph.py's own caller, related_for_person,
    # which pre-resolves every post mentioning a person before calling it) --
    # it does not itself discover sibling posts sharing a mentioned person.
    # Discover them here first: every post that mentions any person this
    # post itself mentions, then load the subgraph over that expanded set.
    person_rows = await conn.fetch(
        "select distinct person_id from combined_post_person_mention where post_id = $1", post_id
    )
    person_ids = [row["person_id"] for row in person_rows]
    sibling_post_ids = [post_id]
    if person_ids:
        sibling_rows = await conn.fetch(
            "select distinct post_id from combined_post_person_mention "
            "where person_id = any($1::uuid[])",
            person_ids,
        )
        sibling_post_ids = list({str(row["post_id"]) for row in sibling_rows} | {post_id})

    # A hidden sibling's mentions must not seed the entity graph
    # load_visible_subgraph walks: an unauthorized post's org/team/customer
    # mention could otherwise bridge to an unrelated visible post through
    # shared entity membership, fabricating an "indirect" relationship
    # whose only real basis is content this account cannot see (the
    # sibling itself stays correctly excluded from output either way).
    if len(sibling_post_ids) > 1:
        # Safe SQL: eligibility predicate is an immutable schema fragment; ids are bound.
        visibility_rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            "select post_id, visibility_code, corporate_entity_id, "
            "author_account_id, source_detail_state_code "
            f"from source_post where post_id = any($1::uuid[]) and ({SOURCE_POST_READER_ELIGIBILITY_SQL.format(alias='source_post')})",
            sibling_post_ids,
        )
        sibling_post_ids = [
            str(row["post_id"]) for row in visibility_rows if can_see_post(row)
        ]
        if post_id not in sibling_post_ids:
            sibling_post_ids.append(post_id)

    edges = await load_visible_subgraph(conn, sibling_post_ids)
    start = node_key(NODE_POST, post_id)
    scores = random_walk_with_restart(adjacency_from_edges(edges), start_node=start)
    related = select_related_nodes(scores, start_node=start)
    indirect_ids = frozenset(
        node_id
        for key, _ in related
        if (node_id := parse_node_key(key)[1]) and parse_node_key(key)[0] == NODE_POST
    ) - {post_id}

    return LinkedPostIds(direct=direct_ids - {post_id}, indirect=indirect_ids - direct_ids)


async def gather_chat_sources(
    conn: asyncpg.Connection,
    post_id: str,
    can_see_post: Callable[[asyncpg.Record], bool],
    vision_client: ImageContentClient | None = None,
) -> list[ChatSourceDocument]:
    """Post `post_id` plus a bounded, deterministic linked-source window.

    Direct Event Lineage neighbors precede indirect Knowledge Graph
    neighbors; both groups are identifier-sorted before ABAC filtering. The
    current post plus at most seven visible linked posts become the numbered
    source set that `post_chat` citations refer back to. Every source's body
    is normalized (HTML tags/base64 images never reach the reason-and-cite
    LLM call raw) before becoming a `ChatSourceDocument` -- see
    `lineageweave.post_content_normalization`. `vision_client` defaults
    to unavailable (embedded images become an explicit placeholder, not
    a dropped or raw-base64 source) so this function stays callable
    without a live provider.
    """
    if vision_client is None:
        vision_client = NullImageContentClient()

    this_post = await conn.fetchrow(
        "select post_id, post_title, post_body, source_system_code, source_record_key, "
        "source_author_code, source_author_name, source_company_code, source_company_name, "
        "source_process_unit_code, source_process_unit_name, "
        "source_sales_pool_code, source_sales_pool_name, "
        "source_order_pool_code, source_sales_order_code, source_sales_order_item_number, "
        "source_inspection_point_code, source_stage_code, source_detail_state_code, source_deleted_flag, "
        "source_customer_code, source_customer_name, source_project_code, "
        "source_project_name from source_post where post_id = $1",
        post_id,
    )
    if this_post is None:
        return []
    source_id = str(this_post["post_id"])
    semantic_facts = await _semantic_facts_for_posts(conn, [source_id])
    normalized_body = await _normalize_post_body_text(
        this_post["post_body"],
        vision_client,
    )
    sources = [
        ChatSourceDocument(
            source_id,
            this_post["post_title"],
            normalized_body,
            evidence_facts=_source_hint_facts(this_post) + semantic_facts.get(source_id, ()),
        )
    ]

    linked = await find_linked_post_ids(conn, post_id, can_see_post)
    candidate_ids = [
        *sorted(linked.direct),
        *sorted(linked.indirect),
    ][:_POST_CHAT_CANDIDATE_LIMIT]
    if not candidate_ids:
        return sources

    rows = await conn.fetch(
        "select post_id, post_title, post_body, visibility_code, corporate_entity_id, "
        "author_account_id, source_detail_state_code, "
        "source_system_code, source_record_key, source_author_code, source_author_name, "
        "source_company_code, source_company_name, source_process_unit_code, "
        "source_process_unit_name, source_sales_pool_code, source_sales_pool_name, "
        "source_order_pool_code, source_sales_order_code, source_sales_order_item_number, "
        "source_inspection_point_code, source_stage_code, source_deleted_flag, "
        "source_customer_code, source_customer_name, "
        "source_project_code, source_project_name "
        "from source_post where post_id = any($1::uuid[]) "
        "order by array_position($1::uuid[], post_id) limit $2",
        candidate_ids,
        _POST_CHAT_CANDIDATE_LIMIT,
    )
    visible_source_ids = [post_id]
    visible_rows: list[asyncpg.Record] = []
    for row in rows:
        if not can_see_post(row):
            continue
        visible_rows.append(row)
        visible_source_ids.append(str(row["post_id"]))
        if len(visible_rows) >= _POST_CHAT_SOURCE_LIMIT - 1:
            break

    semantic_facts = await _semantic_facts_for_posts(conn, visible_source_ids)
    graph_facts = await _graph_facts_for_posts(conn, visible_source_ids)
    sources[0] = ChatSourceDocument(
        sources[0].post_id,
        sources[0].post_title,
        sources[0].post_body,
        graph_facts=graph_facts,
        evidence_facts=sources[0].evidence_facts,
    )
    for row in visible_rows:
        normalized_body = await _normalize_post_body_text(row["post_body"], vision_client)
        sources.append(
            ChatSourceDocument(
                str(row["post_id"]),
                row["post_title"],
                normalized_body,
                evidence_facts=_source_hint_facts(row)
                + semantic_facts.get(str(row["post_id"]), ()),
            )
        )

    return sources


async def gather_global_chat_sources(
    conn: asyncpg.Connection,
    can_see_post: Callable[[asyncpg.Record], bool],
    authorized_corporate_entity_ids: Iterable[str] = (),
    vision_client: ImageContentClient | None = None,
    *,
    question: str | None = None,
    anchor_post_id: str | None = None,
    tepp_client: TeppClient | None = None,
    limit: int = 4,
) -> list[ChatSourceDocument]:
    """Assemble a bounded, ABAC-filtered source set for Global Ask.

    The source set is intentionally bounded until retrieval/reranking is
    needed for a much larger corpus; every selected body still uses the same
    image normalization and persisted graph evidence as post-scoped chat.
    """
    authorized_entity_ids = tuple(str(value) for value in authorized_corporate_entity_ids)
    if limit <= 0:
        return []
    if vision_client is None:
        vision_client = NullImageContentClient()
    search_terms = tuple(
        dict.fromkeys(
            token.casefold()
            for token in _GLOBAL_ASK_TERM_PATTERN.findall(question or "")
            if len(token) >= 2
            and token.casefold()
            not in {
                "which",
                "what",
                "where",
                "when",
                "who",
                "why",
                "how",
                "the",
                "this",
                "that",
                "posts",
                "post",
                "글",
                "게시글",
                "질문",
                "관련",
                "확인되는",
                "핵심",
                "사실",
                "무엇",
                "무엇인가요",
                "인가요",
                "있는",
                "앞쪽",
                "앞쪽에",
                "이벤트",
                "이벤트를",
                "유관",
                "선행",
                "이텐트",
                "찾아줘",
            }
        )
    )[:4]
    # A post whose title names the exact thing asked about is a far more
    # specific match than one that only shares a generic term (a common
    # word, or a hit buried in a 16KB body prefix); weighting every match
    # equally and then falling back on created_at desc as the only
    # tiebreak let recency crowd out relevance -- a year-old post whose
    # title is an exact company-name match lost to four newer, only
    # loosely related posts in a live reproduction of this bug.
    _MATCH_WEIGHT = {"title": 3.0, "body": 1.0, "source_field": 1.0, "semantic": 2.5}
    candidate_scores: dict[str, float] = {}
    for term in search_terms:
        candidate_rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            f"""
            with authorized_source_post as (
                select *
                  from source_post
                 where (visibility_code = 'public'
                    or corporate_entity_id::text = any($2::text[]))
                   and ({SOURCE_POST_READER_ELIGIBILITY_SQL.format(alias='source_post')})
            )
            select post_id, matched_in
              from (
                   (select post_id, created_at, 'title' as matched_in
                      from authorized_source_post
                     where post_title ilike '%' || $1 || '%'
                     limit 32)
                    union all
                   (select post_id, created_at, 'body' as matched_in
                      from authorized_source_post
                     where lower(left(source_post_search_text(post_body), 16384))
                               like '%' || lower($1) || '%'
                     limit 32)
                    union all
                   (select post_id, created_at, 'body' as matched_in
                      from authorized_source_post
                     where to_tsvector('simple', source_post_search_text(post_body))
                               @@ plainto_tsquery('simple', $1)
                     limit 32)
                    union all
                   (select post_id, created_at, 'source_field' as matched_in
                      from authorized_source_post
                     where concat_ws(' ', source_system_code, source_record_key,
                                      source_author_code, source_author_name,
                                      source_company_code, source_company_name,
                                      source_process_unit_code, source_process_unit_name,
                                      source_sales_pool_code, source_sales_pool_name,
                                      source_order_pool_code, source_sales_order_code,
                                      source_sales_order_item_number,
                                      source_inspection_point_code, source_stage_code,
                                      source_deleted_flag,
                                      source_customer_code, source_customer_name,
                                      source_project_code, source_project_name)
                               ilike '%' || $1 || '%'
                     limit 32)
                   union all
                   (select post.post_id, post.created_at, 'semantic' as matched_in
                      from authorized_source_post post
                      join post_summary_event semantic
                        on semantic.post_id = post.post_id
                     where semantic.event_text ilike '%' || $1 || '%'
                        or semantic.evidence_text ilike '%' || $1 || '%'
                     limit 32)
                    union all
                   (select post.post_id, post.created_at, 'semantic' as matched_in
                      from authorized_source_post post
                      join post_summary_event_clue semantic
                        on semantic.post_id = post.post_id
                     where semantic.clue_text ilike '%' || $1 || '%'
                        or semantic.target_text ilike '%' || $1 || '%'
                        or semantic.normalized_value_text ilike '%' || $1 || '%'
                        or semantic.evidence_text ilike '%' || $1 || '%'
                        or semantic.ontology_iri ilike '%' || $1 || '%'
                     limit 32)
                    union all
                   (select post.post_id, post.created_at, 'semantic' as matched_in
                      from authorized_source_post post
                      join post_project_mention semantic
                        on semantic.post_id = post.post_id
                     where semantic.project_name ilike '%' || $1 || '%'
                        or semantic.evidence_text ilike '%' || $1 || '%'
                        or semantic.ontology_iri ilike '%' || $1 || '%'
                     limit 32)
                    union all
                   (select post.post_id, post.created_at, 'semantic' as matched_in
                      from authorized_source_post post
                      join post_summary_role semantic
                        on semantic.post_id = post.post_id
                     where semantic.actor_name ilike '%' || $1 || '%'
                        or semantic.responsibility_text ilike '%' || $1 || '%'
                        or semantic.affiliated_organization_name ilike '%' || $1 || '%'
                     limit 32)
                    union all
                   (select post.post_id, post.created_at, 'semantic' as matched_in
                      from authorized_source_post post
                      join post_summary_quantitative_observation semantic
                        on semantic.post_id = post.post_id
                     where semantic.label_text ilike '%' || $1 || '%'
                        or semantic.raw_value_text ilike '%' || $1 || '%'
                        or semantic.evidence_text ilike '%' || $1 || '%'
                        or semantic.value_numeric::text ilike '%' || $1 || '%'
                        or semantic.quantity_numeric::text ilike '%' || $1 || '%'
                     limit 32)
                    union all
                   (select post.post_id, post.created_at, 'semantic' as matched_in
                      from authorized_source_post post
                      join post_summary_source_fact semantic
                        on semantic.post_id = post.post_id
                     where semantic.label_text ilike '%' || $1 || '%'
                        or semantic.value_text ilike '%' || $1 || '%'
                        or semantic.normalized_value_text ilike '%' || $1 || '%'
                        or semantic.evidence_text ilike '%' || $1 || '%'
                        or semantic.normalized_date::text ilike '%' || $1 || '%'
                     limit 32)
                    union all
                   (select post.post_id, post.created_at, 'semantic' as matched_in
                      from authorized_source_post post
                      join post_summary_semantic_relationship semantic
                        on semantic.post_id = post.post_id
                     where semantic.subject_name ilike '%' || $1 || '%'
                        or semantic.predicate_code ilike '%' || $1 || '%'
                        or semantic.object_name ilike '%' || $1 || '%'
                        or semantic.evidence_text ilike '%' || $1 || '%'
                     limit 32)
                   ) matches
             order by created_at desc, post_id desc
            limit 32
            """,
            term,
            authorized_entity_ids,
        )
        for row in candidate_rows:
            post_id = str(row["post_id"])
            candidate_scores[post_id] = candidate_scores.get(post_id, 0.0) + _MATCH_WEIGHT[row["matched_in"]]
    candidate_ids = sorted(candidate_scores, key=lambda post_id: candidate_scores[post_id], reverse=True)

    # A post opened in the Ask workspace is stronger context than words the
    # reader happens to repeat in the question.  Reuse persisted event and
    # source semantics to retrieve earlier candidates; never manufacture a
    # lineage edge from the similarity score.
    if anchor_post_id:
        prior_rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            f"""
            with authorized_source_post as (
                select *
                  from source_post
                 where (visibility_code = 'public'
                    or corporate_entity_id::text = any($2::text[]))
                   and ({SOURCE_POST_READER_ELIGIBILITY_SQL.format(alias='source_post')})
            ), anchor as (
                select post_id, created_at, source_customer_code, source_project_code,
                       source_company_code, source_process_unit_code,
                       source_sales_pool_code, source_order_pool_code,
                       source_sales_order_code
                  from authorized_source_post
                 where post_id = $1
            ), anchor_events as (
                select string_agg(event_text, ' ') as event_text
                  from post_summary_event
                 where post_id = $1
            ), source_candidates as (
                select post.post_id
                  from authorized_source_post post
                  cross join anchor
                 where post.post_id <> anchor.post_id
                   and post.created_at < anchor.created_at
                   and (post.source_customer_code = anchor.source_customer_code
                    or post.source_project_code = anchor.source_project_code
                    or post.source_company_code = anchor.source_company_code
                    or post.source_process_unit_code = anchor.source_process_unit_code
                    or post.source_sales_pool_code = anchor.source_sales_pool_code
                    or post.source_order_pool_code = anchor.source_order_pool_code
                    or post.source_sales_order_code = anchor.source_sales_order_code)
                 order by post.created_at desc, post.post_id desc
                 limit 64
            ), event_candidates as (
                select distinct event.post_id
                  from post_summary_event event
                  join authorized_source_post post on post.post_id = event.post_id
                  cross join anchor
                  cross join anchor_events
                 where post.post_id <> anchor.post_id
                   and post.created_at < anchor.created_at
                   and to_tsvector('simple', event.event_text)
                       @@ plainto_tsquery('simple', anchor_events.event_text)
                 limit 128
            ), candidates as (
                select post_id from source_candidates
                union
                select post_id from event_candidates
            ), ranked as (
                select post.post_id, post.created_at,
                       greatest(
                           coalesce((
                               select max(word_similarity(event.event_text, anchor_events.event_text))
                                 from post_summary_event event
                                where event.post_id = post.post_id
                           ), 0),
                           0.85 * (post.source_sales_order_code is not null and post.source_sales_order_code = anchor.source_sales_order_code)::int +
                           0.15 * (
                               (post.source_customer_code is not null and post.source_customer_code = anchor.source_customer_code)::int +
                               (post.source_project_code is not null and post.source_project_code = anchor.source_project_code)::int +
                               (post.source_company_code is not null and post.source_company_code = anchor.source_company_code)::int +
                               (post.source_process_unit_code is not null and post.source_process_unit_code = anchor.source_process_unit_code)::int +
                               (post.source_sales_pool_code is not null and post.source_sales_pool_code = anchor.source_sales_pool_code)::int +
                               (post.source_order_pool_code is not null and post.source_order_pool_code = anchor.source_order_pool_code)::int +
                               (post.source_sales_order_code is not null and post.source_sales_order_code = anchor.source_sales_order_code)::int
                           )
                       ) as relevance
                  from anchor
                  cross join anchor_events
                  join candidates on true
                  join authorized_source_post post on post.post_id = candidates.post_id
            )
            select post_id, relevance
              from ranked
             where relevance >= 0.25
             order by relevance desc, created_at desc, post_id desc
             limit $3
            """,
            anchor_post_id,
            authorized_entity_ids,
            limit * 4,
        )
        candidate_scores[anchor_post_id] = candidate_scores.get(anchor_post_id, 0.0) + 10.0
        for row in prior_rows:
            post_id = str(row["post_id"])
            candidate_scores[post_id] = candidate_scores.get(post_id, 0.0) + float(row["relevance"])
        candidate_ids = sorted(candidate_scores, key=lambda post_id: candidate_scores[post_id], reverse=True)

        # Discover new post ids through normalized KG evidence before asking
        # the visible-subgraph walker to rank them.  Only ontology-declared
        # relations cross from the graph projection into retrieval.
        kg_rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            f"""
            with anchor_nodes as (
                select edge.source_node_type_code as node_type_code,
                       edge.source_node_id as node_id
                  from knowledge_graph_edge edge
                  join knowledge_graph_edge_evidence evidence
                    using (knowledge_graph_edge_id)
                 where evidence.evidence_post_id = $1
                   and not (edge.source_node_type_code = 'node_post'
                            and edge.source_node_id = $1)
                union
                select edge.target_node_type_code, edge.target_node_id
                  from knowledge_graph_edge edge
                  join knowledge_graph_edge_evidence evidence
                    using (knowledge_graph_edge_id)
                 where evidence.evidence_post_id = $1
                   and not (edge.target_node_type_code = 'node_post'
                            and edge.target_node_id = $1)
            ), related_edges as (
                select edge.knowledge_graph_edge_id, edge.edge_type_code,
                       edge.edge_weight
                  from anchor_nodes node
                  join knowledge_graph_edge edge
                    on edge.source_node_type_code = node.node_type_code
                   and edge.source_node_id = node.node_id
                union
                select edge.knowledge_graph_edge_id, edge.edge_type_code,
                       edge.edge_weight
                  from anchor_nodes node
                  join knowledge_graph_edge edge
                    on edge.target_node_type_code = node.node_type_code
                   and edge.target_node_id = node.node_id
            ), related as (
                select distinct evidence.evidence_post_id as post_id,
                       edge.edge_type_code, edge.edge_weight
                  from related_edges edge
                  join knowledge_graph_edge_evidence evidence
                    using (knowledge_graph_edge_id)
            )
            select related.post_id, related.edge_type_code, related.edge_weight
              from related
              join source_post post on post.post_id = related.post_id
              join source_post anchor on anchor.post_id = $1
             where related.post_id <> $1
               and post.created_at < anchor.created_at
               and (post.visibility_code = 'public'
                    or post.corporate_entity_id::text = any($2::text[]))
               and ({SOURCE_POST_READER_ELIGIBILITY_SQL.format(alias='post')})
             order by related.edge_weight desc, post.created_at desc, related.post_id
             limit $3
            """,
            anchor_post_id,
            authorized_entity_ids,
            limit * 4,
        )
        kg_discovered_ids = list(
            dict.fromkeys(
                str(row["post_id"])
                for row in kg_rows
                if ontology_annotations(str(row["edge_type_code"])).get("ontology_iri")
            )
        )
        for post_id in kg_discovered_ids:
            candidate_scores.setdefault(post_id, 0.0)
        candidate_ids = list(
            dict.fromkeys([anchor_post_id, *kg_discovered_ids, *candidate_ids])
        )

    # A keyword match only proves one post's text is relevant -- the
    # account asking almost always wants to know what happened before and
    # after that event too, not just this one snapshot. Expand the single
    # best match through its direct Event Lineage neighbors
    # (`post_lineage_edge`, `lineageweave.reconstruct`'s output), mirroring
    # `find_linked_post_ids`'s `.direct` set used by the post-scoped chat
    # flow. Only the top match is expanded -- expanding every keyword hit
    # would let a loosely related term drag in an unrelated lineage chain.
    kg_anchor_id = anchor_post_id or (candidate_ids[0] if candidate_ids else None)
    if kg_anchor_id:
        kg_edges = await load_visible_subgraph(conn, candidate_ids[: limit * 4])
        kg_scores = random_walk_with_restart(
            adjacency_from_edges(kg_edges), node_key(NODE_POST, kg_anchor_id)
        )
        for node, score in select_related_nodes(
            kg_scores, node_key(NODE_POST, kg_anchor_id), max_nodes=limit * 2
        ):
            node_type, node_id = parse_node_key(node)
            if node_type != NODE_POST:
                continue
            candidate_scores[node_id] = candidate_scores.get(node_id, 0.0) + score
        candidate_ids = sorted(
            candidate_scores,
            key=lambda post_id: candidate_scores[post_id],
            reverse=True,
        )

    lineage_neighbor_ids: list[str] = []
    lineage_anchor_id = anchor_post_id or (candidate_ids[0] if candidate_ids else None)
    if lineage_anchor_id:
        lineage_rows = await conn.fetch(
            "select child_post_id as other_id from post_lineage_edge where parent_post_id = $1 "
            "union select parent_post_id as other_id from post_lineage_edge where child_post_id = $1",
            lineage_anchor_id,
        )
        lineage_neighbor_ids = sorted(
            {
                str(row["other_id"])
                for row in lineage_rows
                if str(row["other_id"]) not in candidate_scores
            }
        )
        candidate_ids = list(
            dict.fromkeys([lineage_anchor_id, *lineage_neighbor_ids, *candidate_ids[1:]])
        )[:limit]
    else:
        candidate_ids = []
    lineage_neighbor_id_set = frozenset(lineage_neighbor_ids)

    # Safe SQL: eligibility is a closed schema fragment; authorization, IDs, and limit are bound.
    rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        f"""
        select post_id, post_title, post_body, visibility_code, corporate_entity_id,
               author_account_id, source_detail_state_code,
               source_system_code, source_record_key, source_author_code, source_author_name,
               source_company_code, source_company_name, source_process_unit_code,
               source_process_unit_name, source_sales_pool_code, source_sales_pool_name,
               source_order_pool_code, source_sales_order_code, source_sales_order_item_number,
               source_inspection_point_code, source_stage_code, source_deleted_flag,
               source_customer_code, source_customer_name,
               source_project_code, source_project_name, created_at, updated_at,
               (
                   select min(clue.normalized_value_text)
                     from post_summary_event_clue clue
                    where clue.post_id = source_post.post_id
                      and clue.clue_type_code = 'clue_time'
                      and clue.assertion_code = 'assertion_affirmed'
                      and nullif(btrim(clue.normalized_value_text), '') is not null
                   having count(*) = 1
               ) as semantic_event_time,
               (
                   select result.computed_at
                     from post_summary_result result
                    where result.post_id = source_post.post_id
               ) as semantic_event_available_at
          from source_post
         where (visibility_code = 'public'
            or corporate_entity_id::text = any($1::text[]))
           and ({SOURCE_POST_READER_ELIGIBILITY_SQL.format(alias='source_post')})
           and post_id = any($2::uuid[])
         order by array_position($2::uuid[], post_id) nulls last,
                  created_at desc, post_id desc
         limit $3
        """,
        authorized_entity_ids,
        candidate_ids,
        limit,
    )
    visible_rows = [row for row in rows if can_see_post(row)][:limit]
    tepp_prior_ids: frozenset[str] = frozenset()
    semantic_event_times = {
        str(row["post_id"]): _semantic_event_time(row.get("semantic_event_time"))
        for row in visible_rows
    }
    if (
        tepp_client is not None
        and anchor_post_id
        and len(visible_rows) > 1
        and all(row["author_account_id"] is not None for row in visible_rows)
    ):
        temporal_events: list[TemporalContextEvent] = []
        for row in visible_rows:
            post_id = str(row["post_id"])
            semantic_time = semantic_event_times[post_id]
            semantic_available_at = row.get("semantic_event_available_at")
            is_semantic_event = semantic_time is not None and semantic_available_at is not None
            event_time = semantic_time if is_semantic_event else row["created_at"]
            available_time = (
                semantic_available_at if is_semantic_event else row["created_at"]
            )
            temporal_events.append(
                TemporalContextEvent(
                    event_id=f"{'semantic-event' if is_semantic_event else 'post-recorded'}:{post_id}",
                    source_post_id=post_id,
                    event_type_code="semantic_event" if is_semantic_event else "post_recorded",
                    event_label=(
                        "Persisted semantic event"
                        if is_semantic_event
                        else "Source post recorded"
                    ),
                    event_time=event_time.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    available_time=available_time.astimezone(UTC).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    project_reference=None,
                    actor_references=(str(row["author_account_id"]),),
                )
            )
        request = TemporalContextRequest(
            knowledge_cutoff=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            subject_post_id=anchor_post_id,
            events=tuple(temporal_events),
        )
        try:
            temporal = await asyncio.to_thread(tepp_client.temporal_context, request)
        except (TeppNotAvailable, OSError, TypeError, ValueError):
            temporal = None
        timeline = temporal["timeline_events"] if temporal else None
        if timeline:
            ordinal = {
                str(item["source_post_id"]): int(item["sequence_ordinal"])
                for item in timeline
                if isinstance(item, dict)
                and isinstance(item.get("source_post_id"), str)
                and isinstance(item.get("sequence_ordinal"), int)
            }
            if len(ordinal) == len(visible_rows) and anchor_post_id in ordinal:
                anchor_ordinal = ordinal[anchor_post_id]
                visible_rows.sort(key=lambda row: (str(row["post_id"]) != anchor_post_id, ordinal[str(row["post_id"])]))
                tepp_prior_ids = frozenset(
                    post_id for post_id, value in ordinal.items() if value < anchor_ordinal
                )
    visible_ids = [str(row["post_id"]) for row in visible_rows]
    anchor_is_visible = lineage_anchor_id in visible_ids
    semantic_facts = await _semantic_facts_for_posts(conn, visible_ids)
    graph_facts = (await _graph_facts_for_posts(conn, visible_ids))[:16]
    sources: list[ChatSourceDocument] = []
    for index, row in enumerate(visible_rows):
        normalized_body = await _normalize_post_body_text(row["post_body"], vision_client)
        if len(normalized_body) > 4000:
            normalized_body = (
                normalized_body[:4000]
                + "\n[Source body truncated for Global Ask; open the cited post for the full body.]"
            )
        post_id = str(row["post_id"])
        lineage_fact = (
            (f"Event Lineage: reconstructed timeline neighbor of post_id={lineage_anchor_id}",)
            if post_id in lineage_neighbor_id_set and anchor_is_visible
            else ()
        )
        tepp_fact = (
            ("TEPP temporal context: before the starting post; association_not_causal",)
            if post_id in tepp_prior_ids
            else ()
        )
        sources.append(
            ChatSourceDocument(
                post_id,
                row["post_title"],
                normalized_body,
                graph_facts=graph_facts if index == 0 else (),
                evidence_facts=_source_hint_facts(row)
                + semantic_facts.get(post_id, ())
                + lineage_fact
                + tepp_fact,
            )
        )
    return sources


async def cited_post_images(
    conn: asyncpg.Connection,
    cited_post_ids: list[str],
) -> list[dict[str, Any]]:
    """Persisted image evidence (caption/OCR/tags) for already-cited posts.

    Global Ask cites a post's *text*; when that post's evidence actually
    came from an embedded picture (a screenshot, a diagram), the reader has
    no way to tell the difference -- the answer just reads as a text claim.
    This surfaces the same persisted, never-raw-bytes image description
    `GET /api/posts/{id}/content` already renders (`post_content_image`,
    ADR-tracked alongside its region locations), scoped to the posts this
    answer already cited.

    No ABAC re-check here: `cited_post_ids` only ever contains ids drawn
    from `gather_global_chat_sources`'s already-authorized source set, the
    same trust boundary `cited_post_evidence`/`cited_post_summaries` rely
    on (`lineageweave.post_chat`).
    """
    if not cited_post_ids:
        return []
    rows = await conn.fetch(
        """
        select unit.post_id, unit.unit_index, image.mime_type,
               image.description_status_code, image.extracted_text, image.image_caption,
               coalesce(
                   array_agg(tag.tag_text order by tag.tag_text)
                       filter (where tag.tag_text is not null),
                   '{}'::text[]
               ) as tags
          from post_content_unit unit
          join post_content_image image
            on image.post_content_unit_id = unit.post_content_unit_id
          left join post_content_image_tag tag
            on tag.post_content_image_id = image.post_content_image_id
         where unit.post_id = any($1::uuid[])
         group by unit.post_id, unit.unit_index, image.mime_type,
                  image.description_status_code, image.extracted_text, image.image_caption
         order by unit.post_id, unit.unit_index
        """,
        cited_post_ids,
    )
    return [
        {
            "post_id": str(row["post_id"]),
            "unit_index": row["unit_index"],
            "mime_type": row["mime_type"],
            "status_code": row["description_status_code"],
            "extracted_text": row["extracted_text"],
            "caption": row["image_caption"],
            "tags": list(row["tags"] or []),
        }
        for row in rows
        if row["image_caption"] or row["extracted_text"] or row["tags"]
    ]


@dataclass(frozen=True)
class SeededChat:
    """Synthetic Q&A for a reconstruct/calendar/demo fixture -- not an LLM."""

    answer_text: str
    cited_titles: tuple[str, ...]


async def _serialize_chat(
    conn: asyncpg.Connection, post_id: str, question_norm: str
) -> dict[str, Any] | None:
    """One stored exchange plus citation chips, or None when missing."""
    header = await conn.fetchrow(
        "select question_text, answer_text from post_chat_result "
        "where post_id = $1 and question_norm = $2",
        post_id,
        question_norm,
    )
    if header is None:
        return None
    cites = await conn.fetch(
        "select c.cited_post_id, p.post_title from post_chat_citation c "
        "join source_post p on p.post_id = c.cited_post_id "
        "where c.post_id = $1 and c.question_norm = $2 "
        "order by c.citation_ordinal",
        post_id,
        question_norm,
    )
    cited_ids = [str(row["cited_post_id"]) for row in cites]
    return {
        "question_text": header["question_text"],
        "answer_text": header["answer_text"],
        "cited_post_ids": cited_ids,
        "cited_posts": [
            {"post_id": str(row["cited_post_id"]), "post_title": row["post_title"]}
            for row in cites
        ],
    }


async def fetch_persisted_chat(
    conn: asyncpg.Connection, post_id: str, question: str
) -> dict[str, Any] | None:
    """Return the stored answer for ``question``, or None when none written."""
    norm = normalize_chat_question(question)
    if not norm:
        return None
    return await _serialize_chat(conn, post_id, norm)


async def fetch_persisted_chats(conn: asyncpg.Connection, post_id: str) -> list[dict[str, Any]]:
    """Every stored exchange for ``post_id``, oldest first."""
    rows = await conn.fetch(
        "select question_norm from post_chat_result where post_id = $1 order by computed_at, question_norm",
        post_id,
    )
    exchanges: list[dict[str, Any]] = []
    for row in rows:
        payload = await _serialize_chat(conn, post_id, row["question_norm"])
        if payload is not None:
            exchanges.append(payload)
    return exchanges


async def persist_post_chat(
    conn: asyncpg.Connection,
    post_id: str,
    question: str,
    answer_text: str,
    cited_post_ids: list[str] | tuple[str, ...],
) -> dict[str, Any]:
    """Replace the stored exchange for ``(post_id, question)`` and return it."""
    norm = normalize_chat_question(question)
    if not norm:
        raise ValueError("question is empty after normalize")
    await conn.execute(
        "delete from post_chat_result where post_id = $1 and question_norm = $2",
        post_id,
        norm,
    )
    await conn.execute(
        "insert into post_chat_result (post_id, question_norm, question_text, answer_text) "
        "values ($1, $2, $3, $4)",
        post_id,
        norm,
        question.strip(),
        answer_text,
    )
    seen: set[str] = set()
    ordinal = 0
    for cited_id in cited_post_ids:
        if cited_id in seen:
            continue
        seen.add(cited_id)
        await conn.execute(
            "insert into post_chat_citation "
            "(post_id, question_norm, citation_ordinal, cited_post_id) "
            "values ($1, $2, $3, $4)",
            post_id,
            norm,
            ordinal,
            cited_id,
        )
        ordinal += 1
    payload = await _serialize_chat(conn, post_id, norm)
    if payload is None:
        raise RuntimeError("persist_post_chat wrote no row")
    return payload


def seeded_demo_chat() -> SeededChat:
    """Synthetic Ask answer for the demo public post -- not an LLM result."""
    return SeededChat(
        answer_text=(
            "Ada West at Demo Corp followed up with Priya Nair at Northridge Grid "
            "about the delayed shipment."
        ),
        cited_titles=("Demo public post",),
    )


def seeded_demo_involved_chat() -> SeededChat:
    """Synthetic Keyman answer for the demo public post -- not an LLM result."""
    return SeededChat(
        answer_text=(
            "Ada West at Demo Corp and Priya Nair at Northridge Grid are the "
            "Keymen named in this post."
        ),
        cited_titles=("Demo public post",),
    )


def seeded_demo_commitment_chat() -> SeededChat:
    """Synthetic Calendar answer for the demo public post -- not an LLM result."""
    return SeededChat(
        answer_text=(
            "The next commitment is Send Northridge Grid the revised quote, "
            "due 2026-01-12."
        ),
        cited_titles=("Demo public post",),
    )


def seeded_demo_exchanges() -> list[tuple[str, SeededChat]]:
    """Canned Ask Q&As `make seed` writes for the demo public post."""
    return [
        (CANONICAL_CHAT_QUESTION, seeded_demo_chat()),
        (CANONICAL_INVOLVED_QUESTION, seeded_demo_involved_chat()),
        (CANONICAL_COMMITMENT_QUESTION, seeded_demo_commitment_chat()),
    ]


def seeded_fixture_chat(post_title: str) -> SeededChat | None:
    """Synthetic what-happened answer for a reconstruct/calendar fixture.

    Not an LLM result. Returns None when the title is not a known seed
    fixture so an unknown question still 503s instead of inventing prose.
    """
    return _FIXTURE_CHATS.get(post_title)


def seeded_fixture_involved_chat(post_title: str) -> SeededChat | None:
    """Synthetic Keyman answer for a reconstruct/calendar fixture title.

    Not an LLM result. Returns None when the title has no seeded cast
    answer so an unknown question still 503s instead of inventing people.
    """
    return _INVOLVED_CHATS.get(post_title)


def seeded_fixture_commitment_chat(post_title: str) -> SeededChat | None:
    """Synthetic Calendar answer for a reconstruct/calendar fixture title.

    Not an LLM result. Returns None when the title has no seeded
    commitment answer so an unknown question still 503s instead of
    inventing a ticket.
    """
    return _COMMITMENT_CHATS.get(post_title)


def seeded_fixture_exchanges(post_title: str) -> list[tuple[str, SeededChat]]:
    """Every canned Ask Q&A `make seed` writes for ``post_title``.

    Order is what-happened, who-is-involved, then next-commitment, so
    GET history and the popup chips stay stable. Empty when the title
    is not a known seed fixture.
    """
    exchanges: list[tuple[str, SeededChat]] = []
    happened = seeded_fixture_chat(post_title)
    if happened is not None:
        exchanges.append((CANONICAL_CHAT_QUESTION, happened))
    involved = seeded_fixture_involved_chat(post_title)
    if involved is not None:
        exchanges.append((CANONICAL_INVOLVED_QUESTION, involved))
    commitment = seeded_fixture_commitment_chat(post_title)
    if commitment is not None:
        exchanges.append((CANONICAL_COMMITMENT_QUESTION, commitment))
    return exchanges


def _chat(answer: str, *cited: str) -> SeededChat:
    return SeededChat(answer_text=answer, cited_titles=cited)


_A100 = (
    "Initial site visit and project scope discussion",
    "Pricing renegotiation follow-up",
    "Pricing renegotiation: revised quote sent",
    "Delivery schedule question raised",
    "Delivery schedule confirmed with logistics",
)
_B200 = (
    "Technical specification review meeting",
    "Specification revision requested",
    "Revised specification approved",
)

_FIXTURE_CHATS: dict[str, SeededChat] = {
    "Initial site visit and project scope discussion": _chat(
        "The thread starts with an initial site visit and project scope "
        "discussion. Ada West followed up with Priya Nair at Northridge Grid. "
        "Later posts cover a pricing renegotiation follow-up that forks into "
        "a revised quote and a delivery-schedule question.",
        *_A100,
    ),
    "Pricing renegotiation follow-up": _chat(
        "After the initial site visit, the pricing renegotiation follow-up is "
        "where the thread forks: a revised quote was sent, and a delivery "
        "schedule question was raised (later confirmed with logistics). Ada "
        "West followed up with Priya Nair at Northridge Grid.",
        *_A100,
    ),
    "Pricing renegotiation: revised quote sent": _chat(
        "The pricing renegotiation produced a revised quote that was sent. "
        "That quote sits on the pricing branch of the A-100 thread, alongside "
        "a separate delivery-schedule question. Ada West followed up with "
        "Priya Nair at Northridge Grid.",
        "Pricing renegotiation follow-up",
        "Pricing renegotiation: revised quote sent",
    ),
    "Delivery schedule question raised": _chat(
        "A delivery schedule question was raised after the pricing follow-up, "
        "separate from the revised-quote branch. Logistics later confirmed "
        "the schedule. Ada West followed up with Priya Nair at Northridge Grid.",
        "Pricing renegotiation follow-up",
        "Delivery schedule question raised",
        "Delivery schedule confirmed with logistics",
    ),
    "Delivery schedule confirmed with logistics": _chat(
        "The delivery schedule question was confirmed with logistics, closing "
        "that branch of the A-100 thread. Ada West followed up with Priya "
        "Nair at Northridge Grid.",
        "Delivery schedule question raised",
        "Delivery schedule confirmed with logistics",
    ),
    "Unrelated: annual account review": _chat(
        "This post is an annual account review. It shares the A-100 group "
        "but is not part of the pricing or delivery sequence.",
        "Unrelated: annual account review",
    ),
    "Technical specification review meeting": _chat(
        "A technical specification review meeting opened the B-200 thread. "
        "Jordan Hale reviewed the Westfield Power specification. A revision "
        "was later requested and then approved.",
        *_B200,
    ),
    "Specification revision requested": _chat(
        "After the technical specification review meeting, a specification "
        "revision was requested. Jordan Hale reviewed the Westfield Power "
        "specification. The revised specification was later approved.",
        *_B200,
    ),
    "Revised specification approved": _chat(
        "The revised specification was approved after the review meeting and "
        "revision request. Jordan Hale reviewed the Westfield Power "
        "specification.",
        *_B200,
    ),
    "Follow-up on the Riverbend order confirmation": _chat(
        "The Riverbend order was already confirmed last Tuesday. The remaining "
        "commitment is to send Riverbend the revised delivery schedule by "
        "next Friday.",
        "Follow-up on the Riverbend order confirmation",
    ),
}

_INVOLVED_CHATS: dict[str, SeededChat] = {
    "Initial site visit and project scope discussion": _chat(
        "Ada West (our side) and Priya Nair at Northridge Grid (counterparty) "
        "opened the A-100 site visit.",
        "Initial site visit and project scope discussion",
    ),
    "Pricing renegotiation follow-up": _chat(
        "Ada West and Priya Nair are the Keymen on the A-100 pricing "
        "renegotiation follow-up.",
        "Pricing renegotiation follow-up",
    ),
    "Pricing renegotiation: revised quote sent": _chat(
        "Ada West sent the revised quote; Priya Nair at Northridge Grid is "
        "the counterparty.",
        "Pricing renegotiation: revised quote sent",
    ),
    "Delivery schedule question raised": _chat(
        "Ada West raised the delivery-schedule question with Priya Nair at "
        "Northridge Grid.",
        "Delivery schedule question raised",
    ),
    "Delivery schedule confirmed with logistics": _chat(
        "Ada West and logistics confirmed the schedule with Priya Nair at "
        "Northridge Grid.",
        "Delivery schedule confirmed with logistics",
    ),
    "Unrelated: annual account review": _chat(
        "This annual account review does not name a Keyman.",
        "Unrelated: annual account review",
    ),
    "Technical specification review meeting": _chat(
        "Jordan Hale is the Keyman on the B-200 technical specification review.",
        "Technical specification review meeting",
    ),
    "Specification revision requested": _chat(
        "Jordan Hale requested the Westfield Power specification revision.",
        "Specification revision requested",
    ),
    "Revised specification approved": _chat(
        "Jordan Hale approved the revised Westfield Power specification.",
        "Revised specification approved",
    ),
    "Follow-up on the Riverbend order confirmation": _chat(
        "This Riverbend order follow-up does not name a Keyman.",
        "Follow-up on the Riverbend order confirmation",
    ),
}

_COMMITMENT_CHATS: dict[str, SeededChat] = {
    "Initial site visit and project scope discussion": _chat(
        "After the A-100 site visit the next commitment is Send Northridge "
        "Grid the revised quote, due 2026-01-12.",
        "Initial site visit and project scope discussion",
    ),
    "Pricing renegotiation follow-up": _chat(
        "The next commitment is Send Northridge Grid the revised quote, "
        "due 2026-01-12.",
        "Pricing renegotiation follow-up",
    ),
    "Pricing renegotiation: revised quote sent": _chat(
        "The revised quote is already sent; the next commitment is still "
        "Send Northridge Grid the revised quote, due 2026-01-12.",
        "Pricing renegotiation: revised quote sent",
    ),
    "Delivery schedule question raised": _chat(
        "The next commitment on this delivery-schedule branch is Confirm "
        "the delivery window with logistics, due 2026-01-16.",
        "Delivery schedule question raised",
    ),
    "Delivery schedule confirmed with logistics": _chat(
        "The delivery window is confirmed; the next open commitment on the "
        "A-100 thread is Send Northridge Grid the revised quote, due 2026-01-12.",
        "Delivery schedule confirmed with logistics",
    ),
    "Unrelated: annual account review": _chat(
        "This annual account review does not have an open commitment.",
        "Unrelated: annual account review",
    ),
    "Technical specification review meeting": _chat(
        "The next commitment after the B-200 review meeting is Send "
        "Westfield Power the revised specification, due 2026-01-14.",
        "Technical specification review meeting",
    ),
    "Specification revision requested": _chat(
        "The next commitment is Send Westfield Power the revised "
        "specification, due 2026-01-14.",
        "Specification revision requested",
    ),
    "Revised specification approved": _chat(
        "The specification is approved; the next commitment is still Send "
        "Westfield Power the revised specification, due 2026-01-14.",
        "Revised specification approved",
    ),
    "Follow-up on the Riverbend order confirmation": _chat(
        "The next commitment is Send Riverbend the revised delivery "
        "schedule, due 2026-01-09.",
        "Follow-up on the Riverbend order confirmation",
    ),
}
