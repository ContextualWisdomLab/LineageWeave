"""Finds a post's Event-Lineage-linked posts -- direct (`post_lineage_edge`,
`lineageweave.reconstruct`'s output) and indirect (Knowledge Graph, shared
Keyman/organization, per `lineageweave.knowledge_graph`) -- and assembles
the chat's *retrieve* step (Lewis et al., 2020) from them: numbered source
documents `lineageweave.post_chat`'s reason-and-cite step answers from.
ABAC is re-checked per candidate post here, never trusted from the
Knowledge Graph traversal alone -- a KG edge says two posts are related,
not that the requesting account may see both.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import asyncpg

from lineageweave.knowledge_graph import (
    NODE_POST,
    adjacency_from_edges,
    node_key,
    parse_node_key,
    random_walk_with_restart,
    select_related_nodes,
)
from lineageweave.post_chat import ChatSourceDocument

from .knowledge_graph import load_visible_subgraph


@dataclass(frozen=True)
class LinkedPostIds:
    """A post's Event-Lineage neighbors, kept distinguishable by how they
    were found -- direct thread relations vs. indirect shared-entity
    relations are different claims about why two posts are related.
    """

    direct: frozenset[str]
    indirect: frozenset[str]


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
        "select distinct person_id from post_person_mention where post_id = $1", post_id
    )
    person_ids = [row["person_id"] for row in person_rows]
    sibling_post_ids = [post_id]
    if person_ids:
        sibling_rows = await conn.fetch(
            "select distinct post_id from post_person_mention where person_id = any($1::uuid[])",
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
) -> list[ChatSourceDocument]:
    """Post `post_id` itself, plus every linked post the requesting account
    can actually see -- numbered in the order returned, which is the
    order `post_chat`'s citations refer back to.
    """
    this_post = await conn.fetchrow(
        "select post_id, post_title, post_body from source_post where post_id = $1", post_id
    )
    if this_post is None:
        return []
    sources = [ChatSourceDocument(str(this_post["post_id"]), this_post["post_title"], this_post["post_body"])]

    linked = await find_linked_post_ids(conn, post_id)
    candidate_ids = linked.direct | linked.indirect
    if not candidate_ids:
        return sources

    rows = await conn.fetch(
        "select post_id, post_title, post_body, visibility_code, corporate_entity_id "
        "from source_post where post_id = any($1::uuid[])",
        list(candidate_ids),
    )
    for row in rows:
        if can_see_post(row):
            sources.append(ChatSourceDocument(str(row["post_id"]), row["post_title"], row["post_body"]))

    return sources
