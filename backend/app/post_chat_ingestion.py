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
from typing import Any, Callable

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
    session_id: str | None = None,
    metadata: dict[str, str] | None = None,
) -> list[ChatSourceDocument]:
    """Post `post_id` itself, plus every linked post the requesting account
    can actually see -- numbered in the order returned, which is the
    order `post_chat`'s citations refer back to. Every source's body is
    normalized (HTML tags/base64 images never reach the reason-and-cite
    LLM call raw) before becoming a `ChatSourceDocument` -- see
    `lineageweave.post_content_normalization`. `vision_client` defaults
    to unavailable (embedded images become an explicit placeholder, not
    a dropped or raw-base64 source) so this function stays callable
    without a live provider.
    """
    if vision_client is None:
        vision_client = NullImageContentClient()

    this_post = await conn.fetchrow(
        "select post_id, post_title, post_body, created_at "
        "from source_post where post_id = $1",
        post_id,
    )
    if this_post is None:
        return []
    source_metadata = dict(metadata or {})
    source_metadata["source_post_id"] = str(this_post["post_id"])
    sources = [
            ChatSourceDocument(
                str(this_post["post_id"]),
                this_post["post_title"],
                normalize_post_body(
                this_post["post_body"],
                vision_client=vision_client,
                session_id=session_id,
                    metadata=source_metadata,
                ).text,
                occurred_at=(
                    this_post["created_at"].isoformat()
                    if this_post.get("created_at") is not None
                    else None
                ),
                lineage_relation="anchor",
            )
        ]

    linked = await find_linked_post_ids(conn, post_id)
    candidate_ids = linked.direct | linked.indirect
    if not candidate_ids:
        return sources

    rows = await conn.fetch(
        "select post_id, post_title, post_body, visibility_code, corporate_entity_id, created_at "
        "from source_post where post_id = any($1::uuid[])",
        list(candidate_ids),
    )
    for row in rows:
        if can_see_post(row):
            source_metadata = dict(metadata or {})
            source_metadata["source_post_id"] = str(row["post_id"])
            sources.append(
                ChatSourceDocument(
                    str(row["post_id"]),
                    row["post_title"],
                    normalize_post_body(
                        row["post_body"],
                        vision_client=vision_client,
                        session_id=session_id,
                        metadata=source_metadata,
                    ).text,
                    occurred_at=(
                        row["created_at"].isoformat()
                        if row.get("created_at") is not None
                        else None
                    ),
                    lineage_relation=(
                        "direct_lineage"
                        if str(row["post_id"]) in linked.direct
                        else "indirect_knowledge_graph"
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
