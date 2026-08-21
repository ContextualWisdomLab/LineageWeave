"""Account-owned persistence for the Global Ask transcript."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import asyncpg


class GlobalAskConversationNotFound(LookupError):
    """The requested conversation is absent or owned by another account."""


def conversation_title(question: str) -> str:
    """Use the first question as a bounded, readable transcript label."""
    compact = " ".join(question.strip().split())
    return compact[:80] or "New conversation"


async def conversation_exists(
    conn: asyncpg.Connection, user_account_id: str, conversation_id: UUID
) -> bool:
    return bool(
        await conn.fetchval(
            "select exists(select 1 from global_ask_session where global_ask_session_id = $1 and user_account_id = $2)",
            conversation_id,
            user_account_id,
        )
    )


async def list_conversations(
    conn: asyncpg.Connection,
    user_account_id: str,
    *,
    limit: int = 50,
    before_updated_at: datetime | None = None,
    before_conversation_id: UUID | None = None,
) -> dict[str, Any]:
    rows = await conn.fetch(  # nosemgrep: placeholders bind all values; SQL text is static.
        """
        select session.global_ask_session_id,
               coalesce(
                   (select left(turn.question_text, 80)
                      from global_ask_turn turn
                     where turn.global_ask_session_id = session.global_ask_session_id
                     order by turn.turn_ordinal
                     limit 1),
                   'New conversation'
               ) as conversation_title,
               session.updated_at,
               count(turn.turn_ordinal)::int as turn_count
          from global_ask_session session
         left join global_ask_turn turn
            on turn.global_ask_session_id = session.global_ask_session_id
         where session.user_account_id = $1
           and (
               $2 is null
               or $3 is null
               or session.updated_at < $2
               or (session.updated_at = $2 and session.global_ask_session_id < $3)
           )
         group by session.global_ask_session_id, session.updated_at
         order by session.updated_at desc, session.global_ask_session_id desc
         limit $4
        """,
        user_account_id,
        before_updated_at,
        before_conversation_id,
        limit + 1,
    )
    page_rows = rows[:limit]
    next_cursor = None
    if len(rows) > limit and page_rows:
        last = page_rows[-1]
        next_cursor = {
            "updated_at": last["updated_at"],
            "conversation_id": str(last["global_ask_session_id"]),
        }
    return {
        "conversations": [
            {
                "conversation_id": str(row["global_ask_session_id"]),
                "title": row["conversation_title"],
                "updated_at": row["updated_at"],
                "turn_count": row["turn_count"],
            }
            for row in page_rows
        ],
        "next_cursor": next_cursor,
    }


async def _visible_post_ids(
    conn: asyncpg.Connection,
    conversation_id: UUID,
    turn_ordinal: int,
    can_see_post: Callable[[asyncpg.Record], bool],
    *,
    source: bool,
) -> tuple[list[str], dict[str, asyncpg.Record]]:
    if source:
        rows = await conn.fetch(  # nosemgrep: identifiers are fixed literals in this branch.
            """
        select relation.source_post_id::text as post_id, relation.source_ordinal as ordinal,
               post.post_title, post.visibility_code, post.corporate_entity_id,
               post.author_account_id, post.source_detail_state_code
          from global_ask_turn_source relation
          join source_post post on post.post_id = relation.source_post_id
         where relation.global_ask_session_id = $1
           and relation.turn_ordinal = $2
         order by relation.source_ordinal
        """,
            conversation_id,
            turn_ordinal,
        )
    else:
        rows = await conn.fetch(  # nosemgrep: identifiers are fixed literals in this branch.
            """
        select relation.cited_post_id::text as post_id, relation.citation_ordinal as ordinal,
               post.post_title, post.visibility_code, post.corporate_entity_id,
               post.author_account_id, post.source_detail_state_code
          from global_ask_turn_citation relation
          join source_post post on post.post_id = relation.cited_post_id
         where relation.global_ask_session_id = $1
           and relation.turn_ordinal = $2
         order by relation.citation_ordinal
        """,
            conversation_id,
            turn_ordinal,
        )
    visible = [row for row in rows if can_see_post(row)]
    return [str(row["post_id"]) for row in visible], {str(row["post_id"]): row for row in visible}


async def fetch_conversation(
    conn: asyncpg.Connection,
    user_account_id: str,
    conversation_id: UUID,
    can_see_post: Callable[[asyncpg.Record], bool],
    *,
    turn_limit: int = 50,
    before_turn_ordinal: int | None = None,
) -> dict[str, Any] | None:
    header = await conn.fetchrow(
        """
        select global_ask_session_id
          from global_ask_session
         where global_ask_session_id = $1 and user_account_id = $2
        """,
        conversation_id,
        user_account_id,
    )
    if header is None:
        return None

    title_question = await conn.fetchval(
        """
        select question_text
          from global_ask_turn
         where global_ask_session_id = $1
         order by turn_ordinal
         limit 1
        """,
        conversation_id,
    )
    if before_turn_ordinal is None:
        turns = await conn.fetch(  # nosemgrep: placeholders bind all values; SQL text is static.
            """
        select turn_ordinal, question_text, answer_text, next_action
          from global_ask_turn
         where global_ask_session_id = $1
         order by turn_ordinal desc
         limit $2
            """,
            conversation_id,
            turn_limit + 1,
        )
    else:
        turns = await conn.fetch(  # nosemgrep: placeholders bind all values; SQL text is static.
            """
        select turn_ordinal, question_text, answer_text, next_action
          from global_ask_turn
         where global_ask_session_id = $1
           and turn_ordinal < $2
         order by turn_ordinal desc
         limit $3
            """,
            conversation_id,
            before_turn_ordinal,
            turn_limit + 1,
        )
    has_older = len(turns) > turn_limit
    turns = list(turns[:turn_limit])
    turns.reverse()
    exchanges: list[dict[str, Any]] = []
    for turn in turns:
        ordinal = int(turn["turn_ordinal"])
        source_ids, _ = await _visible_post_ids(
            conn, conversation_id, ordinal, can_see_post, source=True
        )
        cited_ids, cited_rows = await _visible_post_ids(
            conn, conversation_id, ordinal, can_see_post, source=False
        )
        evidence_rows = await conn.fetch(
            """
            select cited_post_id::text as post_id, fact_kind, fact_text
              from global_ask_turn_evidence
             where global_ask_session_id = $1 and turn_ordinal = $2
             order by cited_post_id, fact_ordinal
            """,
            conversation_id,
            ordinal,
        )
        evidence: dict[str, list[dict[str, str]]] = {}
        for row in evidence_rows:
            post_id = str(row["post_id"])
            if post_id in cited_rows:
                evidence.setdefault(post_id, []).append(
                    {"kind": row["fact_kind"], "text": row["fact_text"]}
                )
        exchanges.append(
            {
                "turn_id": f"{conversation_id}:{ordinal}",
                "question_text": turn["question_text"],
                "answer_text": turn["answer_text"],
                "cited_post_ids": cited_ids,
                "cited_posts": [
                    {"post_id": post_id, "post_title": cited_rows[post_id]["post_title"]}
                    for post_id in cited_ids
                ],
                "cited_post_evidence": [
                    {"post_id": post_id, "facts": evidence[post_id]}
                    for post_id in cited_ids
                    if evidence.get(post_id)
                ],
                "source_post_ids": source_ids,
                "next_action": turn["next_action"],
            }
        )
    title = conversation_title(title_question) if title_question else "New conversation"
    return {
        "conversation_id": str(header["global_ask_session_id"]),
        "title": title,
        "exchanges": exchanges,
        "older_cursor": str(turns[0]["turn_ordinal"]) if has_older and turns else None,
    }


async def persist_turn(
    conn: asyncpg.Connection,
    user_account_id: str,
    conversation_id: UUID | None,
    question: str,
    answer_text: str,
    next_action: str | None,
    source_post_ids: Iterable[str],
    cited_post_ids: Iterable[str],
    cited_post_evidence: Iterable[dict[str, Any]],
) -> UUID:
    source_ids = list(dict.fromkeys(str(post_id) for post_id in source_post_ids))
    source_set = set(source_ids)
    cited_ids = list(dict.fromkeys(str(post_id) for post_id in cited_post_ids if str(post_id) in source_set))
    evidence_by_post = {
        str(item["post_id"]): item.get("facts") or []
        for item in cited_post_evidence
        if str(item["post_id"]) in cited_ids
    }
    async with conn.transaction():
        if conversation_id is None:
            conversation_id = uuid4()
            await conn.execute(
                "insert into global_ask_session (global_ask_session_id, user_account_id) values ($1, $2)",
                conversation_id,
                user_account_id,
            )
        else:
            conversation = await conn.fetchrow(
                """
                select global_ask_session_id
                  from global_ask_session
                 where global_ask_session_id = $1 and user_account_id = $2
                 for update
                """,
                conversation_id,
                user_account_id,
            )
            if conversation is None:
                raise GlobalAskConversationNotFound

        ordinal = int(
            await conn.fetchval(
                "select coalesce(max(turn_ordinal), 0) + 1 from global_ask_turn where global_ask_session_id = $1",
                conversation_id,
            )
        )
        await conn.execute(
            """
            insert into global_ask_turn
                (global_ask_session_id, turn_ordinal, question_text, answer_text, next_action)
            values ($1, $2, $3, $4, $5)
            """,
            conversation_id,
            ordinal,
            question,
            answer_text,
            next_action,
        )
        for source_ordinal, post_id in enumerate(source_ids):
            await conn.execute(
                "insert into global_ask_turn_source (global_ask_session_id, turn_ordinal, source_ordinal, source_post_id) values ($1, $2, $3, $4)",
                conversation_id,
                ordinal,
                source_ordinal,
                post_id,
            )
        for citation_ordinal, post_id in enumerate(cited_ids):
            await conn.execute(
                "insert into global_ask_turn_citation (global_ask_session_id, turn_ordinal, citation_ordinal, cited_post_id) values ($1, $2, $3, $4)",
                conversation_id,
                ordinal,
                citation_ordinal,
                post_id,
            )
            for fact_ordinal, fact in enumerate(evidence_by_post.get(post_id, ())):
                fact_kind = str(fact.get("kind", "source_field"))
                fact_text = str(fact.get("text", "")).strip()
                if not fact_text:
                    continue
                await conn.execute(
                    """
                    insert into global_ask_turn_evidence
                        (global_ask_session_id, turn_ordinal, cited_post_id,
                         fact_ordinal, fact_kind, fact_text)
                    values ($1, $2, $3, $4, $5, $6)
                    """,
                    conversation_id,
                    ordinal,
                    post_id,
                    fact_ordinal,
                    fact_kind,
                    fact_text,
                )
        await conn.execute(
            "update global_ask_session set updated_at = now() where global_ask_session_id = $1",
            conversation_id,
        )
    assert conversation_id is not None
    return conversation_id
