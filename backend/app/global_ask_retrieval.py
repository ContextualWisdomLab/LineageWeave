"""Semantic and Knowledge-Graph candidate nomination for Global Ask.

Candidate nomination is deliberately non-authoritative. This module returns
post identifiers only. The caller must re-run the normal source-post visibility
predicate before exposing body text or evidence.
"""

from __future__ import annotations

import re
from typing import Any

import asyncpg

from lineageweave.claim_verification import ontology_lookup_codes_for_question

_STOP_WORDS = frozenset(
    {
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
_TOKEN = re.compile(r"[^\W_]+(?:-[^\W_]+)*", re.UNICODE)
_EVIDENCE_POST_IDS = re.compile(r"\[evidence_post_id=([^]]+)\]")


def global_ask_query_terms(question: str | None, *, maximum_terms: int = 8) -> tuple[str, ...]:
    """Return bounded, de-duplicated lexical terms from a Global Ask query."""

    if maximum_terms <= 0:
        return ()
    return tuple(
        dict.fromkeys(
            token.casefold()
            for token in _TOKEN.findall(question or "")
            if len(token) >= 2 and token.casefold() not in _STOP_WORDS
        )
    )[:maximum_terms]


async def semantic_candidate_post_ids(
    conn: asyncpg.Connection,
    question: str | None,
    *,
    maximum_candidates: int = 128,
) -> list[str]:
    """Nominate posts from persisted semantic and Knowledge-Graph evidence.

    Project mentions, responsibility/affiliation evidence, Keyman names,
    organization/team catalogs, and graph edge/type vocabulary are searched.
    Ontology lookup codes are applied only to graph lookup-code columns; they
    are not compared to ontology IRIs. The function never returns source text.
    """

    if maximum_candidates <= 0:
        return []
    terms = global_ask_query_terms(question)
    ontology_codes = ontology_lookup_codes_for_question(question or "")
    if not terms and not ontology_codes:
        return []
    rows = await conn.fetch(
        """
        with query_terms as (
            select unnest($1::text[]) as term
        ), candidate_post as (
            select mention.post_id, post.created_at
              from post_project_mention mention
              join source_post post on post.post_id = mention.post_id
             where exists (
                    select 1 from query_terms term
                     where concat_ws(' ', mention.project_name,
                                           mention.evidence_text,
                                           mention.ontology_iri,
                                           mention.extraction_method)
                           ilike '%' || term.term || '%'
                )
            union all
            select role.post_id, post.created_at
              from post_summary_role role
              join source_post post on post.post_id = role.post_id
             where exists (
                    select 1 from query_terms term
                     where concat_ws(' ', role.actor_name,
                                           role.responsibility,
                                           role.affiliated_organization_name)
                           ilike '%' || term.term || '%'
                )
            union all
            select mention.post_id, post.created_at
              from post_person_mention mention
              join cataloged_person person on person.person_id = mention.person_id
              join source_post post on post.post_id = mention.post_id
             where exists (
                    select 1 from query_terms term
                     where concat_ws(' ', person.person_name,
                                           person.last_known_job_title,
                                           mention.mention_context)
                           ilike '%' || term.term || '%'
                )
            union all
            select mention.post_id, post.created_at
              from post_organization_mention mention
              join corporate_entity entity
                on entity.corporate_entity_id = mention.corporate_entity_id
              join source_post post on post.post_id = mention.post_id
             where exists (
                    select 1 from query_terms term
                     where entity.entity_name ilike '%' || term.term || '%'
                )
            union all
            select mention.post_id, post.created_at
              from post_team_mention mention
              join cataloged_team team on team.team_id = mention.team_id
              join source_post post on post.post_id = mention.post_id
             where exists (
                    select 1 from query_terms term
                     where concat_ws(' ', team.team_name,
                                           team.affiliated_organization_name)
                           ilike '%' || term.term || '%'
                )
            union all
            select evidence.evidence_post_id as post_id, post.created_at
              from knowledge_graph_edge edge
              join knowledge_graph_edge_evidence evidence
                on evidence.knowledge_graph_edge_id = edge.knowledge_graph_edge_id
              join source_post post on post.post_id = evidence.evidence_post_id
             where edge.edge_type_code = any($2::text[])
                or edge.source_node_type_code = any($2::text[])
                or edge.target_node_type_code = any($2::text[])
                or exists (
                    select 1 from query_terms term
                     where concat_ws(' ', edge.edge_type_code,
                                           edge.source_node_type_code,
                                           edge.target_node_type_code)
                           ilike '%' || term.term || '%'
                )
        )
        select post_id::text as post_id
          from candidate_post
         group by post_id
         order by max(created_at) desc, post_id desc
         limit $3
        """,
        list(terms),
        list(ontology_codes),
        maximum_candidates,
    )
    return list(dict.fromkeys(str(row["post_id"]) for row in rows))


def graph_fact_evidence_post_ids(fact: str) -> frozenset[str]:
    """Extract all persisted evidence-post identifiers named by one graph fact."""

    match = _EVIDENCE_POST_IDS.search(fact)
    if match is None:
        return frozenset()
    return frozenset(
        value.strip() for value in match.group(1).split(",") if value.strip()
    )


def public_external_claim_facts(
    row: Any,
    semantic_facts: tuple[str, ...],
    graph_facts: tuple[str, ...],
    public_post_ids: frozenset[str],
) -> tuple[str, ...]:
    """Return externally searchable facts only for a public source post.

    Source hints, people/Keyman facts, TEPP results, and fast-mlsirm reports are
    absent by construction. A graph fact is eligible only if every persisted
    evidence post named by that edge is public in the authorized result set.
    """

    if row.get("visibility_code") != "public":
        return ()
    public_graph_facts = tuple(
        fact
        for fact in graph_facts
        if (evidence_ids := graph_fact_evidence_post_ids(fact))
        and evidence_ids.issubset(public_post_ids)
        and "node_person" not in fact
    )
    public_semantic_facts = tuple(
        fact
        for fact in semantic_facts
        if fact.startswith("project:")
        and "node_person" not in fact
        and not fact.startswith(("actor:", "Keyman mention:"))
    )
    return tuple(dict.fromkeys(public_semantic_facts + public_graph_facts))


__all__ = [
    "global_ask_query_terms",
    "graph_fact_evidence_post_ids",
    "public_external_claim_facts",
    "semantic_candidate_post_ids",
]
