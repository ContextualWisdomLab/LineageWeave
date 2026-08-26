"""Finds a post's Event-Lineage-linked posts -- direct (`post_lineage_edge`,
`lineageweave.reconstruct`'s output) and indirect (Knowledge Graph, shared
Keyman/organization, per `lineageweave.knowledge_graph`) -- and assembles
the chat's *retrieve* step (Lewis et al., 2020) from them: numbered source
documents `lineageweave.post_chat`'s reason-and-cite step answers from.
ABAC is re-checked per candidate post here, never trusted from the
Knowledge Graph traversal alone -- a KG edge says two posts are related,
not that the requesting account may see both.

`gather_global_chat_sources` (Global Ask, no starting post) also expands
its single best persisted-embedding match through the same `post_lineage_edge`
neighbors, so an answer speaks to a connected timeline rather than one
isolated snapshot -- it does not have a starting post to run the
Knowledge Graph's indirect random-walk expansion from, only the lineage
chain of its own top match.
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable, Iterable
from zoneinfo import ZoneInfo

import asyncpg

from lineageweave.ask_time_axis import row_matches_time_range, time_axis_evidence_fact
from lineageweave.claim_verification import GlobalAskSourceDocument
from lineageweave.embedding_client import EmbeddingClient, NullEmbeddingClient
from lineageweave.image_content import ImageContentClient, NullImageContentClient
from lineageweave.knowledge_graph import (
    NODE_POST,
    adjacency_from_edges,
    node_key,
    parse_node_key,
    random_walk_with_restart,
    select_related_nodes,
)
from lineageweave.ontology import all_declared_lookup_codes, ontology_annotations
from lineageweave.post_chat import (
    CANONICAL_CHAT_QUESTION,
    CANONICAL_COMMITMENT_QUESTION,
    CANONICAL_INVOLVED_QUESTION,
    ChatSourceDocument,
    normalize_chat_question,
)
from lineageweave.post_content_normalization import normalize_post_body
from lineageweave.rankweave_client import RankWeaveNotAvailable, build_rankweave_client
from lineageweave.temporal_expressions import resolve_korean_relative_time

from .config import load_settings
from .knowledge_graph import hydrate_related_nodes, load_visible_subgraph
from .post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from .source_post_revision import fetch_known_at_revisions


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
    knowledge_cutoff: datetime | None = None,
) -> dict[str, tuple[str, ...]]:
    """Render graph facts under each visible post that evidences them.

    The evidence join is deliberate: a graph edge without a visible evidence
    post must never enter an LLM prompt. This is the chat-side trust boundary
    in addition to the post-level ABAC check. Keeping the evidence-post mapping
    also prevents a fact evidenced by one source from being rendered beneath a
    different source and then cited as though that source supported it.
    """
    if not visible_post_ids or knowledge_cutoff is not None:
        return {}
    edge_rows = await conn.fetch(
        """
        select edge.source_node_type_code, edge.source_node_id,
               edge.target_node_type_code, edge.target_node_id,
               edge.edge_type_code, edge.edge_weight,
               array_agg(distinct evidence.evidence_post_id::text
                         order by evidence.evidence_post_id::text) as evidence_post_ids
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
        return {}

    visible_post_id_set = frozenset(visible_post_ids)
    edge_rows = [
        row
        for row in edge_rows
        if not (
            row["source_node_type_code"] == NODE_POST
            and str(row["source_node_id"]) not in visible_post_id_set
        )
        and not (
            row["target_node_type_code"] == NODE_POST
            and str(row["target_node_id"]) not in visible_post_id_set
        )
    ]
    if not edge_rows:
        return {}

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

    facts_by_post: dict[str, list[str]] = {}
    fact_count = 0
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
        fact_prefix = (
            f'{source_type} "{source["label"]}" '
            f'--{edge_name}--> {target_type} "{target["label"]}" '
        )
        for evidence_post_id in row["evidence_post_ids"]:
            post_id = str(evidence_post_id)
            post_facts = facts_by_post.setdefault(post_id, [])
            fact = f"{fact_prefix}[evidence_post_id={post_id}]"
            if fact not in post_facts:
                post_facts.append(fact)
                fact_count += 1
            if fact_count >= 64:
                return {key: tuple(value) for key, value in facts_by_post.items()}
    return {key: tuple(value) for key, value in facts_by_post.items()}


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
    ("source_customer_code", "source customer code"),
    ("source_customer_name", "source customer name"),
    ("source_project_code", "source project code"),
    ("source_project_name", "source project name"),
)

_POST_CHAT_SOURCE_LIMIT = 8

# Korean relative-time words ("어제", "오늘", ...) name a KST calendar day,
# not the server process's local/UTC day -- the whole repo otherwise runs on
# UTC (no per-account timezone exists to ask instead). Both the resolver's
# `today` and the SQL day-boundary cast below must use this same zone, or a
# question asked between KST 00:00-09:00 (UTC still "yesterday") resolves
# and filters against two different calendar days.
_ASK_TIME_ZONE = ZoneInfo("Asia/Seoul")


def _seoul_today() -> date:
    return datetime.now(_ASK_TIME_ZONE).date()


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
    return tuple(facts)


async def _semantic_facts_for_posts(
    conn: asyncpg.Connection,
    post_ids: list[str],
    knowledge_cutoff: datetime | None = None,
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
                   || ' | confidence: ' || confidence::text
                   || ' [provenance=post_project_mention]' as fact
          from post_project_mention
         where post_id = any($1::uuid[])
           and ($2::timestamptz is null or created_at <= $2)
        union all
        select post_id::text as post_id,
               'actor: ' || left(actor_name, 200)
                   || ' | responsibility: ' || left(responsibility, 500)
                   || coalesce(' | affiliation: ' || left(affiliated_organization_name, 200), '')
                   || ' [provenance=post_summary_role]' as fact
          from post_summary_role
         where post_id = any($1::uuid[])
           and $2::timestamptz is null
        union all
        select mention.post_id::text as post_id,
               'Keyman mention: ' || left(person.person_name, 200)
                   || coalesce(' | context: ' || left(mention.mention_context, 500), '')
                   || ' [provenance=post_person_mention]' as fact
          from post_person_mention mention
          join cataloged_person person on person.person_id = mention.person_id
         where mention.post_id = any($1::uuid[])
           and $2::timestamptz is null
         order by post_id, fact
        """,
        post_ids,
        knowledge_cutoff,
    )
    facts: dict[str, list[str]] = {}
    for row in rows:
        facts.setdefault(str(row["post_id"]), []).append(row["fact"])
    return {post_id: tuple(dict.fromkeys(values)) for post_id, values in facts.items()}


async def find_linked_post_ids(conn: asyncpg.Connection, post_id: str) -> LinkedPostIds:
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


async def find_project_sibling_post_ids(
    conn: asyncpg.Connection, post_id: str
) -> frozenset[str]:
    """Published posts sharing a persisted project key, for Ask context only."""
    project_rows = await conn.fetch(
        "select distinct project_key from post_project_mention where post_id = $1",
        post_id,
    )
    project_keys = [str(row["project_key"]) for row in project_rows]
    if not project_keys:
        return frozenset()
    rows = await conn.fetch(
        "select distinct ppm.post_id from post_project_mention ppm "
        "join source_post sp on sp.post_id = ppm.post_id "
        "where ppm.project_key = any($1::text[]) and ppm.post_id <> $2 "
        f"and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='sp')} "
        "order by ppm.post_id limit $3",
        project_keys,
        post_id,
        _POST_CHAT_CANDIDATE_LIMIT,
    )
    return frozenset(str(row["post_id"]) for row in rows)


async def gather_chat_sources(
    conn: asyncpg.Connection,
    post_id: str,
    can_see_post: Callable[[asyncpg.Record], bool],
    vision_client: ImageContentClient | None = None,
) -> list[ChatSourceDocument]:
    """Post `post_id` plus a bounded, deterministic linked-source window.

    Persisted semantic-project siblings precede direct Event Lineage and
    indirect Knowledge Graph neighbors; each group is identifier-sorted before
    ABAC filtering. This gives exact project membership a bounded opportunity
    to supply the missing original even when graph neighborhoods are dense.
    The current post plus at most seven visible linked posts become the numbered
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

    linked = await find_linked_post_ids(conn, post_id)
    project_sibling_ids = await find_project_sibling_post_ids(conn, post_id)
    candidate_ids = [
        *sorted(project_sibling_ids),
        *sorted(linked.direct - project_sibling_ids),
        *sorted(linked.indirect - project_sibling_ids),
    ][:_POST_CHAT_CANDIDATE_LIMIT]
    if not candidate_ids:
        graph_facts = await _graph_facts_for_posts(conn, [source_id])
        return [
            ChatSourceDocument(
                source_id,
                this_post["post_title"],
                normalized_body,
                graph_facts=graph_facts.get(source_id, ()),
                evidence_facts=_source_hint_facts(this_post)
                + semantic_facts.get(source_id, ()),
            )
        ]

    rows = await conn.fetch(
        "select post_id, post_title, post_body, visibility_code, corporate_entity_id, process_unit_id, "
        "source_system_code, source_record_key, source_author_code, source_author_name, "
        "source_company_code, source_company_name, source_process_unit_code, "
        "source_process_unit_name, source_sales_pool_code, source_sales_pool_name, "
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
    sources = [
        ChatSourceDocument(
            source_id,
            this_post["post_title"],
            normalized_body,
            graph_facts=graph_facts.get(source_id, ()),
            evidence_facts=_source_hint_facts(this_post) + semantic_facts.get(source_id, ()),
        )
    ]
    for row in visible_rows:
        normalized_body = await _normalize_post_body_text(row["post_body"], vision_client)
        sources.append(
            ChatSourceDocument(
                str(row["post_id"]),
                row["post_title"],
                normalized_body,
                graph_facts=graph_facts.get(str(row["post_id"]), ()),
                evidence_facts=_source_hint_facts(row)
                + semantic_facts.get(str(row["post_id"]), ()),
            )
        )

    return sources


async def prepare_global_question_embedding(
    question: str,
    embedding_client: EmbeddingClient,
) -> tuple[list[float], str, float] | None:
    """Resolve one question embedding without holding a database connection."""
    if not question.strip() or not embedding_client.available:
        return None
    try:
        question_vector = await asyncio.to_thread(embedding_client.embed, question)
    except (OSError, RuntimeError, ValueError):
        return None
    return _validated_question_embedding(
        question_vector, embedding_client.resolved_model
    )


def _validated_question_embedding(
    question_vector: list[float], embedding_model_code: str | None
) -> tuple[list[float], str, float] | None:
    """Return a finite, non-zero embedding envelope or fail closed."""
    if (
        not question_vector
        or not embedding_model_code
        or any(not math.isfinite(value) for value in question_vector)
    ):
        return None
    question_norm = math.sqrt(sum(value * value for value in question_vector))
    if not math.isfinite(question_norm) or question_norm == 0.0:
        return None
    return question_vector, embedding_model_code, question_norm


def _ontology_lookup_codes_in_question(question: str) -> list[str]:
    """Return ontology lookup codes whose complete canonical IRI is cited."""
    folded_question = question.casefold()
    matched: list[str] = []
    for lookup_code in sorted(all_declared_lookup_codes()):
        ontology_iri = ontology_annotations(lookup_code).get("ontology_iri")
        if ontology_iri and ontology_iri.casefold() in folded_question:
            matched.append(lookup_code)
    return matched


def _fuse_global_candidate_ids(
    embedding_ids: list[str], evidence_ids: list[str], limit: int
) -> list[str]:
    """Fuse two owned rank lists with RankWeave parameter-free RRF."""
    if not embedding_ids:
        return evidence_ids[:limit]
    if not evidence_ids:
        return embedding_ids[:limit]
    channels = {"embedding": embedding_ids, "evidence": evidence_ids}
    titles_by_id = {
        post_id: post_id
        for post_id in dict.fromkeys([*embedding_ids, *evidence_ids])
    }
    try:
        fused = build_rankweave_client(
            disabled=load_settings().rankweave_disabled
        ).fuse_rankings(channels, titles_by_id)
    except RankWeaveNotAvailable:
        return embedding_ids[:limit]
    return [item.post_id for item in fused.items[:limit]]


async def gather_global_chat_sources(
    conn: asyncpg.Connection,
    can_see_post: Callable[[asyncpg.Record], bool],
    authorized_corporate_entity_ids: Iterable[str] = (),
    authorized_process_unit_ids: Iterable[str] = (),
    vision_client: ImageContentClient | None = None,
    embedding_client: EmbeddingClient | None = None,
    *,
    question: str | None = None,
    search_phrases: tuple[str, ...] | None = None,
    question_embedding: tuple[list[float], str, float] | None = None,
    limit: int = 4,
    today: date | None = None,
    knowledge_cutoff: datetime | None = None,
) -> list[ChatSourceDocument]:
    """Assemble a bounded, ABAC-filtered source set for Global Ask.

    ``today`` pins the reference date for relative-time resolution so a
    caller that also restates the resolved window (the Ask worker's
    grounded prompt) uses the same date as retrieval even across a
    Seoul-midnight boundary.

    When `question` contains a Korean relative-time expression ("어제",
    "작년 이맘때쯤", "3일 전", ...; see `lineageweave.temporal_expressions`),
    the final candidate set is bounded to posts whose event instant
    (`event_occurred_at`, falling back to `created_at`) falls in the
    resolved Seoul date range -- an unbounded expression ("언젠가")
    or no expression at all applies no date filter. Cited sources name
    which clock matched (ADR 0202).

    Embedding candidates use maximum cosine similarity with exact model and
    dimension agreement. Persisted semantic/KG evidence remains available
    when that channel is unavailable; title/body lexical fallback does not.
    A cutoff instead retrieves retained revisions plus timestamped project and
    ontology-edge evidence. Current-only embeddings, roles, Keymen, graph
    labels, lineage, images, and source hints are excluded rather than
    back-projected into history.
    """
    if limit <= 0:
        return []
    if vision_client is None:
        vision_client = NullImageContentClient()
    if embedding_client is None:
        embedding_client = NullEmbeddingClient()
    resolved_time_range = resolve_korean_relative_time(
        question or "", today=today or _seoul_today()
    )
    if not (question and question.strip()):
        return []
    retrieval_phrases = search_phrases or (question,)
    supplied_question_embedding = question_embedding is not None
    if knowledge_cutoff is not None:
        question_embedding = None
        supplied_question_embedding = False
    if question_embedding is None and knowledge_cutoff is None:
        question_embedding = await prepare_global_question_embedding(
            question, embedding_client
        )
    validated_embedding = (
        _validated_question_embedding(question_embedding[0], question_embedding[1])
        if question_embedding is not None
        else None
    )
    embedding_enabled = validated_embedding is not None
    if supplied_question_embedding and not embedding_enabled:
        return []
    question_vector, embedding_model_code, question_norm = validated_embedding or (
        [],
        "",
        1.0,
    )
    # Safe SQL: the only interpolation is the repository-owned eligibility
    # expression; all request and model values remain asyncpg parameters.
    if knowledge_cutoff is not None:
        candidate_rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            f"""
            with evidence_query as (
                select websearch_to_tsquery('simple', phrase) as terms
                  from unnest($1::text[]) as phrase
            ), evidence_post_candidates as (
                select revision.post_id
                  from source_post_revision revision, evidence_query query
                 where revision.written_at <= $2
                   and (revision.superseded_at is null or revision.superseded_at > $2)
                   and to_tsvector(
                           'simple',
                           coalesce(revision.post_title, '') || ' ' ||
                           coalesce(revision.post_body, '')
                       ) @@ query.terms
                union
                select project.post_id
                  from post_project_mention project, evidence_query query
                 where project.created_at <= $2
                   and to_tsvector(
                           'simple',
                           coalesce(project.project_name, '') || ' ' ||
                           coalesce(project.evidence_text, '') || ' ' ||
                           coalesce(project.ontology_iri, '')
                       ) @@ query.terms
                union
                select evidence.evidence_post_id
                  from knowledge_graph_edge edge
                  join knowledge_graph_edge_evidence evidence
                    on evidence.knowledge_graph_edge_id = edge.knowledge_graph_edge_id
                 where edge.created_at <= $2
                   and edge.edge_type_code = any($3::text[])
            )
            select 'evidence'::text as candidate_channel, candidate.post_id,
                   row_number() over (
                       order by coalesce(post.event_occurred_at, post.created_at) desc,
                                candidate.post_id desc
                   ) as channel_rank
              from evidence_post_candidates candidate
              join source_post post on post.post_id = candidate.post_id
             where post.created_at <= $2
               and (post.visibility_code = 'public'
                    or (post.corporate_entity_id::text = any($4::text[])
                        and (cardinality($5::text[]) = 0
                             or post.process_unit_id::text = any($5::text[]))))
               and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}
               and ($6::date is null or (coalesce(post.event_occurred_at, post.created_at) at time zone 'Asia/Seoul')::date >= $6)
               and ($7::date is null or (coalesce(post.event_occurred_at, post.created_at) at time zone 'Asia/Seoul')::date <= $7)
             order by channel_rank
             limit $8
            """,
            list(retrieval_phrases),
            knowledge_cutoff,
            _ontology_lookup_codes_in_question(question),
            list(authorized_corporate_entity_ids),
            list(authorized_process_unit_ids),
            resolved_time_range[0] if resolved_time_range else None,
            resolved_time_range[1] if resolved_time_range else None,
            limit,
        )
    else:
        candidate_rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        f"""
        with question_vector as (
            select ordinality - 1 as dimension_index, dimension_value
              from unnest($1::double precision[]) with ordinality
                   as vector(dimension_value, ordinality)
        ), unit_similarity as (
            select unit.post_id, embedding.post_content_embedding_id,
                   sum(value.dimension_value * question.dimension_value)
                       / nullif(
                           sqrt(sum(value.dimension_value * value.dimension_value)) * $2,
                           0
                       ) as cosine_similarity
              from source_post post
              join post_content_unit unit on unit.post_id = post.post_id
              join post_content_embedding embedding
                on embedding.post_content_unit_id = unit.post_content_unit_id
              join post_content_embedding_value value
                on value.post_content_embedding_id = embedding.post_content_embedding_id
              join question_vector question
                on question.dimension_index = value.dimension_index
             where $11::boolean
               and embedding.embedding_model_code = $3
               and embedding.embedding_dimension_count = cardinality($1::double precision[])
               and (post.visibility_code = 'public'
                    or (post.corporate_entity_id::text = any($4::text[])
                        and (cardinality($5::text[]) = 0
                             or post.process_unit_id::text = any($5::text[]))))
               and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}
               and ($6::date is null or (coalesce(post.event_occurred_at, post.created_at) at time zone 'Asia/Seoul')::date >= $6)
               and ($7::date is null or (coalesce(post.event_occurred_at, post.created_at) at time zone 'Asia/Seoul')::date <= $7)
             group by unit.post_id, embedding.post_content_embedding_id
            having count(*) = cardinality($1::double precision[])
        ), embedding_candidates as (
            select similarity.post_id,
                   max(similarity.cosine_similarity) as semantic_score,
                   max(coalesce(post.event_occurred_at, post.created_at)) as event_clock
              from unit_similarity similarity
              join source_post post on post.post_id = similarity.post_id
             group by similarity.post_id
             order by semantic_score desc, event_clock desc, similarity.post_id desc
             limit $8
        ), evidence_query as (
            select websearch_to_tsquery('simple', phrase) as terms
              from unnest($9::text[]) as phrase
        ), matching_nodes as (
            select 'node_person'::text as node_type_code, person.person_id as node_id
              from cataloged_person person, evidence_query query
             where to_tsvector(
                       'simple',
                       coalesce(person.person_name, '') || ' ' ||
                       coalesce(person.last_known_job_title, '')
                   ) @@ query.terms
            union
            select 'node_corporate_entity', entity.corporate_entity_id
              from corporate_entity entity, evidence_query query
             where to_tsvector(
                       'simple',
                       coalesce(entity.corporate_entity_code, '') || ' ' ||
                       coalesce(entity.entity_name, '')
                   ) @@ query.terms
            union
            select 'node_team', team.team_id
              from cataloged_team team, evidence_query query
             where to_tsvector(
                       'simple',
                       coalesce(team.team_name, '') || ' ' ||
                       coalesce(team.affiliated_organization_name, '')
                   ) @@ query.terms
            union
            select 'node_post', endpoint.post_id
              from source_post endpoint, evidence_query query
             where to_tsvector('simple', coalesce(endpoint.post_title, '')) @@ query.terms
               and (endpoint.visibility_code = 'public'
                    or (endpoint.corporate_entity_id::text = any($4::text[])
                        and (cardinality($5::text[]) = 0
                             or endpoint.process_unit_id::text = any($5::text[]))))
               and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='endpoint')}
        ), matching_edges as (
            select edge.knowledge_graph_edge_id
              from knowledge_graph_edge edge
              join common_lookup_value lookup
                on lookup.lookup_code = edge.edge_type_code
              cross join evidence_query query
             where to_tsvector(
                       'simple',
                       coalesce(lookup.lookup_code, '') || ' ' ||
                       coalesce(lookup.lookup_label, '')
                   ) @@ query.terms
            union
            select edge.knowledge_graph_edge_id
              from knowledge_graph_edge edge
             where edge.edge_type_code = any($10::text[])
            union
            select edge.knowledge_graph_edge_id
              from knowledge_graph_edge edge
              join matching_nodes node
                on node.node_type_code = edge.source_node_type_code
               and node.node_id = edge.source_node_id
            union
            select edge.knowledge_graph_edge_id
              from knowledge_graph_edge edge
              join matching_nodes node
                on node.node_type_code = edge.target_node_type_code
               and node.node_id = edge.target_node_id
        ), evidence_post_candidates as (
            select project.post_id
              from post_project_mention project, evidence_query query
             where to_tsvector(
                       'simple',
                       coalesce(project.project_name, '') || ' ' ||
                       coalesce(project.evidence_text, '') || ' ' ||
                       coalesce(project.ontology_iri, '')
                   ) @@ query.terms
            union
            select role.post_id
              from post_summary_role role, evidence_query query
             where to_tsvector(
                       'simple',
                       coalesce(role.actor_name, '') || ' ' ||
                       coalesce(role.responsibility, '') || ' ' ||
                       coalesce(role.affiliated_organization_name, '')
                   ) @@ query.terms
            union
            select mention.post_id
              from combined_post_person_mention mention
              join cataloged_person person on person.person_id = mention.person_id
              cross join evidence_query query
             where to_tsvector(
                       'simple',
                       coalesce(person.person_name, '') || ' ' ||
                       coalesce(person.last_known_job_title, '')
                   ) @@ query.terms
            union
            select mention.post_id
              from combined_post_person_mention mention
              join person_affiliation affiliation
                on affiliation.person_id = mention.person_id
              cross join evidence_query query
             where to_tsvector(
                       'simple',
                       coalesce(affiliation.affiliated_organization_name, '') || ' ' ||
                       coalesce(affiliation.role_title, '')
                   ) @@ query.terms
            union
            select evidence.evidence_post_id
              from matching_edges edge
              join knowledge_graph_edge_evidence evidence
                on evidence.knowledge_graph_edge_id = edge.knowledge_graph_edge_id
        ), authorized_evidence_candidates as (
            select candidate.post_id,
                   max(coalesce(post.event_occurred_at, post.created_at)) as event_clock
              from evidence_post_candidates candidate
              join source_post post on post.post_id = candidate.post_id
             where (post.visibility_code = 'public'
                    or (post.corporate_entity_id::text = any($4::text[])
                        and (cardinality($5::text[]) = 0
                             or post.process_unit_id::text = any($5::text[]))))
               and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}
               and ($6::date is null or (coalesce(post.event_occurred_at, post.created_at) at time zone 'Asia/Seoul')::date >= $6)
               and ($7::date is null or (coalesce(post.event_occurred_at, post.created_at) at time zone 'Asia/Seoul')::date <= $7)
             group by candidate.post_id
             order by event_clock desc, candidate.post_id desc
             limit $8
        )
        select 'embedding'::text as candidate_channel, post_id,
               row_number() over (order by semantic_score desc, event_clock desc, post_id desc) as channel_rank
          from embedding_candidates
        union all
        select 'evidence', post_id,
               row_number() over (order by event_clock desc, post_id desc) as channel_rank
          from authorized_evidence_candidates
         order by candidate_channel, channel_rank
        """,
        question_vector,
        question_norm,
        embedding_model_code,
        list(authorized_corporate_entity_ids),
        list(authorized_process_unit_ids),
        resolved_time_range[0] if resolved_time_range else None,
        resolved_time_range[1] if resolved_time_range else None,
        limit,
        list(retrieval_phrases),
        _ontology_lookup_codes_in_question(question),
        embedding_enabled,
    )
    embedding_candidate_ids: list[str] = []
    evidence_candidate_ids: list[str] = []
    for row in candidate_rows:
        channel = str(row.get("candidate_channel") or "embedding")
        target = (
            evidence_candidate_ids if channel == "evidence" else embedding_candidate_ids
        )
        target.append(str(row["post_id"]))
    candidate_ids = _fuse_global_candidate_ids(
        embedding_candidate_ids, evidence_candidate_ids, limit
    )
    candidate_id_set = frozenset(candidate_ids)

    # One semantic match is still only one event snapshot. Expand the
    # best-matching post through its direct Event Lineage neighbors
    # (`post_lineage_edge`, `lineageweave.reconstruct`'s output), mirroring
    # `find_linked_post_ids`'s `.direct` set used by the post-scoped chat
    # flow. Only the top match is expanded so lower-ranked semantic candidates
    # cannot each pull a separate lineage chain into the bounded context.
    lineage_neighbor_ids: list[str] = []
    lineage_anchor_id = candidate_ids[0] if candidate_ids else None
    if lineage_anchor_id and knowledge_cutoff is None:
        lineage_rows = await conn.fetch(
            "select child_post_id as other_id from post_lineage_edge where parent_post_id = $1 "
            "union select parent_post_id as other_id from post_lineage_edge where child_post_id = $1",
            lineage_anchor_id,
        )
        lineage_neighbor_ids = sorted(
            {
                str(row["other_id"])
                for row in lineage_rows
                if str(row["other_id"]) not in candidate_id_set
            }
        )
        candidate_ids = list(
            dict.fromkeys([lineage_anchor_id, *lineage_neighbor_ids, *candidate_ids[1:]])
        )[:limit]
    elif not lineage_anchor_id:
        candidate_ids = []
    lineage_neighbor_id_set = frozenset(lineage_neighbor_ids)

    # Safe SQL: the only interpolation is the repository-owned eligibility
    # expression; all request and identity values remain asyncpg parameters.
    rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        f"""
        select post_id, post_title, post_body, visibility_code, corporate_entity_id, process_unit_id,
               source_system_code, source_record_key, source_author_code, source_author_name,
               source_company_code, source_company_name, source_process_unit_code,
               source_process_unit_name, source_sales_pool_code, source_sales_pool_name,
               source_customer_code, source_customer_name,
               source_project_code, source_project_name,
               created_at, updated_at, event_occurred_at
          from source_post
         where (visibility_code = 'public'
            or (corporate_entity_id::text = any($1::text[])
                and (cardinality($2::text[]) = 0
                     or process_unit_id::text = any($2::text[]))))
           and source_post.post_id = any($3::uuid[])
           and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='source_post')}
           and ($7::timestamptz is null or source_post.created_at <= $7)
           and ($5::date is null or (coalesce(event_occurred_at, created_at) at time zone 'Asia/Seoul')::date >= $5)
           and ($6::date is null or (coalesce(event_occurred_at, created_at) at time zone 'Asia/Seoul')::date <= $6)
         order by array_position($3::uuid[], post_id) nulls last,
                  coalesce(event_occurred_at, created_at) desc, post_id desc
         limit $4
        """,
        list(authorized_corporate_entity_ids),
        list(authorized_process_unit_ids),
        candidate_ids,
        limit,
        resolved_time_range[0] if resolved_time_range else None,
        resolved_time_range[1] if resolved_time_range else None,
        knowledge_cutoff,
    )
    visible_rows = [
        row
        for row in rows
        if can_see_post(row) and row_matches_time_range(row, resolved_time_range)
    ][:limit]
    visible_ids = [str(row["post_id"]) for row in visible_rows]
    anchor_is_visible = lineage_anchor_id in visible_ids
    revisions = await fetch_known_at_revisions(conn, visible_ids, knowledge_cutoff) if knowledge_cutoff else {}
    semantic_facts = await _semantic_facts_for_posts(conn, visible_ids, knowledge_cutoff)
    graph_facts = await _graph_facts_for_posts(conn, visible_ids, knowledge_cutoff)
    remaining_graph_facts = 16
    time_filter_active = resolved_time_range is not None
    sources: list[ChatSourceDocument] = []
    for index, row in enumerate(visible_rows):
        post_id = str(row["post_id"])
        revision = revisions.get(post_id) if knowledge_cutoff else None
        historical_body_unavailable = knowledge_cutoff is not None and revision is None
        source_title = (
            revision["post_title"]
            if revision is not None
            else ("Historical body unavailable" if historical_body_unavailable else row["post_title"])
        )
        source_body = revision["post_body"] if revision is not None else (
            "" if historical_body_unavailable else row["post_body"]
        )
        normalized_body = await _normalize_post_body_text(source_body, vision_client)
        if len(normalized_body) > 4000:
            normalized_body = (
                normalized_body[:4000]
                + "\n[Source body truncated for Global Ask; open the cited post for the full body.]"
            )
        lineage_fact = (
            (f"Event Lineage: reconstructed timeline neighbor of post_id={lineage_anchor_id}",)
            if post_id in lineage_neighbor_id_set and anchor_is_visible
            else ()
        )
        event_occurred_at = row.get("event_occurred_at")
        created_at = row.get("created_at")
        observed_at = event_occurred_at or created_at
        sources.append(
            source_type(
                post_id,
                source_title,
                normalized_body,
                graph_facts=post_graph_facts,
                evidence_facts=(
                    () if knowledge_cutoff is not None else _source_hint_facts(row)
                )
                + semantic_facts.get(post_id, ())
                + lineage_fact
                + time_axis_evidence_fact(row, time_filter_active=time_filter_active),
                observed_at=observed_at.isoformat() if observed_at else None,
                time_axis_code="event_occurred_at"
                if event_occurred_at is not None
                else "created_at"
                if created_at is not None
                else None,
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
               image.description_status_code, image.extracted_text, image.caption,
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
                  image.description_status_code, image.extracted_text, image.caption
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
            "caption": row["caption"],
            "tags": list(row["tags"] or []),
        }
        for row in rows
        if row["caption"] or row["extracted_text"] or row["tags"]
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
