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
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable
from uuid import uuid4

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
from lineageweave.post_chat import (
    CANONICAL_CHAT_QUESTION,
    CANONICAL_COMMITMENT_QUESTION,
    CANONICAL_INVOLVED_QUESTION,
    ChatSourceDocument,
    normalize_chat_question,
)
from lineageweave.post_content_normalization import normalize_post_body

from .knowledge_graph import hydrate_related_nodes, load_visible_subgraph
from .post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave.ontology import ontology_annotations


@dataclass(frozen=True)
class LinkedPostIds:
    """A post's Event-Lineage neighbors, kept distinguishable by how they
    were found -- direct thread relations vs. indirect shared-entity
    relations are different claims about why two posts are related.
    """

    direct: frozenset[str]
    indirect: frozenset[str]


@dataclass(frozen=True)
class GlobalAskContext:
    """Account-scoped continuity context; source evidence is re-retrieved."""

    session_id: str
    summary: str | None
    summary_through_ordinal: int
    recent_turns: tuple[tuple[int, str, str], ...]
    compress_turns: tuple[tuple[int, str, str], ...]


async def ensure_global_ask_session(
    conn: asyncpg.Connection,
    account_id: str,
    session_id: str | None,
) -> str | None:
    """Create or account-check one Global Ask session; hidden ids stay hidden."""
    if session_id is not None:
        row = await conn.fetchrow(
            """
            select global_ask_session_id
              from global_ask_session
             where global_ask_session_id = $1
               and user_account_id = $2
            """,
            session_id,
            account_id,
        )
        return str(row["global_ask_session_id"]) if row is not None else None
    created = str(uuid4())
    await conn.execute(
        "insert into global_ask_session (global_ask_session_id, user_account_id) values ($1, $2)",
        created,
        account_id,
    )
    return created


async def load_global_ask_context(
    conn: asyncpg.Connection,
    session_id: str,
    *,
    recent_limit: int = 6,
    compression_batch: int = 4,
) -> GlobalAskContext:
    """Load bounded continuity rows and the oldest batch eligible for compression."""
    session = await conn.fetchrow(
        """
        select context_summary, context_summary_through_ordinal
          from global_ask_session
         where global_ask_session_id = $1
        """,
        session_id,
    )
    if session is None:
        raise ValueError("global ask session not found")
    through = int(session["context_summary_through_ordinal"])
    pending_count = int(
        await conn.fetchval(
            "select count(*) from global_ask_turn where global_ask_session_id = $1 and turn_ordinal > $2",
            session_id,
            through,
        )
    )
    compress_count = min(compression_batch, max(0, pending_count - recent_limit))
    compress_rows = (
        await conn.fetch(
            """
            select turn_ordinal, question_text, answer_text
              from global_ask_turn
             where global_ask_session_id = $1
               and turn_ordinal > $2
             order by turn_ordinal
             limit $3
            """,
            session_id,
            through,
            compress_count,
        )
        if compress_count
        else []
    )
    recent_rows = await conn.fetch(
        """
        select turn_ordinal, question_text, answer_text
          from global_ask_turn
         where global_ask_session_id = $1
           and turn_ordinal > $2
         order by turn_ordinal desc
         limit $3
        """,
        session_id,
        through,
        recent_limit,
    )
    return GlobalAskContext(
        session_id=session_id,
        summary=session["context_summary"],
        summary_through_ordinal=through,
        recent_turns=tuple(
            (int(row["turn_ordinal"]), row["question_text"], row["answer_text"])
            for row in reversed(recent_rows)
        ),
        compress_turns=tuple(
            (int(row["turn_ordinal"]), row["question_text"], row["answer_text"])
            for row in compress_rows
        ),
    )


async def persist_global_ask_summary(
    conn: asyncpg.Connection,
    session_id: str,
    summary: str,
    through_ordinal: int,
) -> None:
    """Replace the bounded continuity summary after orchestrator compression."""
    if not summary.strip() or through_ordinal <= 0:
        raise ValueError("global ask summary requires covered turns")
    await conn.execute(
        """
        update global_ask_session
           set context_summary = $2,
               context_summary_through_ordinal = $3,
               updated_at = now()
         where global_ask_session_id = $1
        """,
        session_id,
        summary.strip(),
        through_ordinal,
    )


async def persist_global_ask_turn(
    conn: asyncpg.Connection,
    session_id: str,
    question: str,
    answer: str,
    cited_post_ids: Iterable[str],
) -> int:
    """Append one serialized turn and its normalized citation references."""
    citations = list(dict.fromkeys(str(post_id) for post_id in cited_post_ids))
    async with conn.transaction():
        await conn.fetchrow(
            "select global_ask_session_id from global_ask_session where global_ask_session_id = $1 for update",
            session_id,
        )
        ordinal = int(
            await conn.fetchval(
                "select coalesce(max(turn_ordinal), 0) + 1 from global_ask_turn where global_ask_session_id = $1",
                session_id,
            )
        )
        await conn.execute(
            "insert into global_ask_turn (global_ask_session_id, turn_ordinal, question_text, answer_text) values ($1, $2, $3, $4)",
            session_id,
            ordinal,
            question,
            answer,
        )
        for citation_ordinal, post_id in enumerate(citations):
            await conn.execute(
                "insert into global_ask_turn_citation (global_ask_session_id, turn_ordinal, citation_ordinal, cited_post_id) values ($1, $2, $3, $4)",
                session_id,
                ordinal,
                citation_ordinal,
                post_id,
            )
        await conn.execute(
            "update global_ask_session set updated_at = now() where global_ask_session_id = $1",
            session_id,
        )
    return ordinal


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
    ("source_customer_code", "source customer code"),
    ("source_customer_name", "source customer name"),
    ("source_project_code", "source project code"),
    ("source_project_name", "source project name"),
)

_GLOBAL_ASK_TERM_PATTERN = re.compile(r"[^\W_]+(?:-[^\W_]+)*", re.UNICODE)
_POST_CHAT_SOURCE_LIMIT = 8
_POST_CHAT_CANDIDATE_LIMIT = 32
_SOURCE_ELIGIBILITY = SOURCE_POST_ELIGIBILITY_SQL.format(alias="source_post")


def _ask_cutoff(value: datetime | None) -> datetime:
    """Return an aware UTC cutoff for one Ask retrieval."""

    cutoff = value or datetime.now(timezone.utc)
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("knowledge_cutoff must include an offset")
    return cutoff.astimezone(timezone.utc)


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


def _timestamp_text(row: Any) -> str | None:
    value = row.get("created_at")
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


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
                   || ' | confidence: ' || confidence::text
                   || ' [provenance=post_project_mention]' as fact
          from post_project_mention
         where post_id = any($1::uuid[])
        union all
        select post_id::text as post_id,
               'actor: ' || left(actor_name, 200)
                   || ' | responsibility: ' || left(responsibility, 500)
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
         order by post_id, fact
        """,
        post_ids,
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


async def gather_chat_sources(
    conn: asyncpg.Connection,
    post_id: str,
    can_see_post: Callable[[asyncpg.Record], bool],
    vision_client: ImageContentClient | None = None,
    *,
    knowledge_cutoff: datetime | None = None,
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
    cutoff = _ask_cutoff(knowledge_cutoff)

    this_post = await conn.fetchrow(
        "select post_id, post_title, post_body, created_at, source_system_code, source_record_key, "
        "source_author_code, source_author_name, source_company_code, source_company_name, "
        "source_process_unit_code, source_process_unit_name, "
        "source_sales_pool_code, source_sales_pool_name, "
        "source_customer_code, source_customer_name, source_project_code, "
        f"source_project_name from source_post where post_id = $1 "
        f"and created_at <= $2 and {_SOURCE_ELIGIBILITY}",
        post_id,
        cutoff,
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

    linked = await find_linked_post_ids(conn, post_id)
    candidate_ids = [
        *sorted(linked.direct),
        *sorted(linked.indirect),
    ][:_POST_CHAT_CANDIDATE_LIMIT]
    if not candidate_ids:
        return sources

    rows = await conn.fetch(
        "select post_id, post_title, post_body, visibility_code, corporate_entity_id, "
        "source_system_code, source_record_key, source_author_code, source_author_name, "
        "source_company_code, source_company_name, source_process_unit_code, "
        "source_process_unit_name, source_sales_pool_code, source_sales_pool_name, "
        "source_customer_code, source_customer_name, "
        "source_project_code, source_project_name, created_at "
        f"from source_post where post_id = any($1::uuid[]) "
        f"and created_at <= $3 and {_SOURCE_ELIGIBILITY} "
        "order by array_position($1::uuid[], post_id) limit $2",
        candidate_ids,
        _POST_CHAT_CANDIDATE_LIMIT,
        cutoff,
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
    limit: int = 4,
    knowledge_cutoff: datetime | None = None,
) -> list[ChatSourceDocument]:
    """Assemble a bounded, ABAC-filtered source set for Global Ask.

    The source set is intentionally bounded until retrieval/reranking is
    needed for a much larger corpus; every selected body still uses the same
    image normalization and persisted graph evidence as post-scoped chat.
    """
    if limit <= 0:
        return []
    if vision_client is None:
        vision_client = NullImageContentClient()
    cutoff = _ask_cutoff(knowledge_cutoff)
    authorized_entity_ids = list(authorized_corporate_entity_ids)
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
            }
        )
    )[:8]
    # A post whose title names the exact thing asked about is a far more
    # specific match than one that only shares a generic term (a common
    # word, or a hit buried in a 16KB body prefix); weighting every match
    # equally and then falling back on created_at desc as the only
    # tiebreak let recency crowd out relevance -- a year-old post whose
    # title is an exact company-name match lost to four newer, only
    # loosely related posts in a live reproduction of this bug.
    _MATCH_WEIGHT = {"title": 3.0, "body": 1.0, "source_field": 1.0}
    candidate_scores: dict[str, float] = {}
    for term in search_terms:
        candidate_rows = await conn.fetch(
            f"""
            select post_id, matched_in
              from (
                   (select post_id, created_at, 'title' as matched_in
                      from source_post
                     where (visibility_code = 'public'
                            or corporate_entity_id::text = any($2::text[]))
                       and created_at <= $3
                       and {_SOURCE_ELIGIBILITY}
                       and post_title ilike '%' || $1 || '%'
                     limit 32)
                    union all
                   (select post_id, created_at, 'body' as matched_in
                      from source_post
                     where (visibility_code = 'public'
                            or corporate_entity_id::text = any($2::text[]))
                       and created_at <= $3
                       and {_SOURCE_ELIGIBILITY}
                       and lower(left(source_post_search_text(post_body), 16384))
                               like '%' || lower($1) || '%'
                     limit 32)
                    union all
                   (select post_id, created_at, 'body' as matched_in
                      from source_post
                     where (visibility_code = 'public'
                            or corporate_entity_id::text = any($2::text[]))
                       and created_at <= $3
                       and {_SOURCE_ELIGIBILITY}
                       and to_tsvector('simple', source_post_search_text(post_body))
                               @@ plainto_tsquery('simple', $1)
                     limit 32)
                    union all
                   (select post_id, created_at, 'source_field' as matched_in
                      from source_post
                     where (visibility_code = 'public'
                            or corporate_entity_id::text = any($2::text[]))
                       and created_at <= $3
                       and {_SOURCE_ELIGIBILITY}
                       and concat_ws(' ', source_system_code, source_record_key,
                                      source_author_code, source_author_name,
                                      source_company_code, source_company_name,
                                      source_process_unit_code, source_process_unit_name,
                                      source_sales_pool_code, source_sales_pool_name,
                                      source_customer_code, source_customer_name,
                                      source_project_code, source_project_name)
                               ilike '%' || $1 || '%'
                     limit 32)
                   ) matches
             order by created_at desc, post_id desc
            limit 32
            """,
            term,
            authorized_entity_ids,
            cutoff,
        )
        for row in candidate_rows:
            post_id = str(row["post_id"])
            candidate_scores[post_id] = candidate_scores.get(post_id, 0.0) + _MATCH_WEIGHT[row["matched_in"]]
    candidate_budget = min(_POST_CHAT_CANDIDATE_LIMIT, max(limit, limit * 4))
    candidate_ids = sorted(candidate_scores, key=lambda post_id: candidate_scores[post_id], reverse=True)

    # A keyword match only proves one post's text is relevant -- the
    # account asking almost always wants to know what happened before and
    # after that event too, not just this one snapshot. Expand the single
    # best match through its direct Event Lineage neighbors
    # (`post_lineage_edge`, `lineageweave.reconstruct`'s output), mirroring
    # `find_linked_post_ids`'s `.direct` set used by the post-scoped chat
    # flow. Only the top match is expanded -- expanding every keyword hit
    # would let a loosely related term drag in an unrelated lineage chain.
    lineage_neighbor_ids: list[str] = []
    lineage_anchor_id = candidate_ids[0] if candidate_ids else None
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
        )[:candidate_budget]
    else:
        candidate_ids = candidate_ids[:candidate_budget]
    lineage_neighbor_id_set = frozenset(lineage_neighbor_ids)

    rows = await conn.fetch(
        f"""
        select post_id, post_title, post_body, visibility_code, corporate_entity_id,
               created_at,
               source_system_code, source_record_key, source_author_code, source_author_name,
               source_company_code, source_company_name, source_process_unit_code,
               source_process_unit_name, source_sales_pool_code, source_sales_pool_name,
               source_customer_code, source_customer_name,
               source_project_code, source_project_name
          from source_post
         where (visibility_code = 'public'
            or corporate_entity_id::text = any($1::text[]))
           and created_at <= $4
           and {_SOURCE_ELIGIBILITY}
         order by array_position($2::uuid[], post_id) nulls last,
                  created_at desc, post_id desc
         limit $3
        """,
        list(authorized_corporate_entity_ids),
        candidate_ids,
        limit,
        cutoff,
    )
    visible_rows = [row for row in rows if can_see_post(row)][:limit]
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
        sources.append(
            ChatSourceDocument(
                post_id,
                row["post_title"],
                normalized_body,
                graph_facts=graph_facts if index == 0 else (),
                evidence_facts=_source_hint_facts(row)
                + semantic_facts.get(post_id, ())
                + lineage_fact,
                occurred_at=_timestamp_text(row),
                timeline_kind=(
                    "lineage_neighbor"
                    if post_id in lineage_neighbor_id_set and anchor_is_visible
                    else "lineage_anchor"
                    if post_id == lineage_anchor_id
                    else "keyword_match"
                ),
            )
        )
    return sources


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
        "select question_text, answer_text, knowledge_cutoff from post_chat_result "
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
        "_knowledge_cutoff": header.get("knowledge_cutoff"),
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
    *,
    knowledge_cutoff: datetime | None = None,
) -> dict[str, Any]:
    """Replace the stored exchange for ``(post_id, question)`` and return it."""
    norm = normalize_chat_question(question)
    if not norm:
        raise ValueError("question is empty after normalize")
    cutoff = _ask_cutoff(knowledge_cutoff)
    computed_at = max(datetime.now(timezone.utc), cutoff)
    await conn.execute(
        "delete from post_chat_result where post_id = $1 and question_norm = $2",
        post_id,
        norm,
    )
    await conn.execute(
        "insert into post_chat_result "
        "(post_id, question_norm, question_text, answer_text, computed_at, knowledge_cutoff) "
        "values ($1, $2, $3, $4, $5, $6)",
        post_id,
        norm,
        question.strip(),
        answer_text,
        computed_at,
        cutoff,
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
