"""Account-owned persistence for Ask conversations on one visible post.

ADR 0235 reuses the ADR 0126 list/select/new contract with a required
post_id scope. Conversation ids are never Global Ask session ids.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import asyncpg

from .post_eligibility import SOURCE_POST_ELIGIBILITY_SQL


class PostAskConversationNotFound(LookupError):
    """The requested conversation is absent, on another post, or another account."""


class PostAskEvidenceChanged(RuntimeError):
    """A gathered source became unauthorized before the new turn could commit."""


async def conversation_exists(
    conn: asyncpg.Connection,
    user_account_id: str,
    post_id: str,
    conversation_id: UUID,
) -> bool:
    """Return whether this account owns the conversation on ``post_id``."""
    return bool(
        await conn.fetchval(
            """
            select exists(
                select 1
                  from post_ask_session
                 where post_ask_session_id = $1
                   and user_account_id = $2
                   and post_id = $3
            )
            """,
            conversation_id,
            user_account_id,
            post_id,
        )
    )


async def list_conversations(
    conn: asyncpg.Connection,
    user_account_id: str,
    post_id: str,
    *,
    limit: int = 50,
    before_created_at: datetime | None = None,
    before_conversation_id: UUID | None = None,
) -> dict[str, Any]:
    """Return this account's conversations on ``post_id``, newest-created first."""
    if (before_created_at is None) != (before_conversation_id is None):
        raise ValueError("before_created_at and before_conversation_id must be provided together")
    rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        """
        select session.post_ask_session_id,
               (select left(turn.question_text, 80)
                  from post_ask_turn turn
                 where turn.post_ask_session_id = session.post_ask_session_id
                 order by turn.turn_ordinal
                 limit 1) as conversation_title,
               session.created_at,
               session.updated_at,
               count(turn.turn_ordinal)::int as turn_count
          from post_ask_session session
         left join post_ask_turn turn
            on turn.post_ask_session_id = session.post_ask_session_id
         where session.user_account_id = $1
           and session.post_id = $2
           and (
               $3 is null
               or $4 is null
               or session.created_at < $3
               or (session.created_at = $3 and session.post_ask_session_id < $4)
           )
         group by session.post_ask_session_id, session.created_at, session.updated_at
         order by session.created_at desc, session.post_ask_session_id desc
         limit $5
        """,
        user_account_id,
        post_id,
        before_created_at,
        before_conversation_id,
        limit + 1,
    )
    page_rows = rows[:limit]
    next_cursor = None
    if len(rows) > limit and page_rows:
        last = page_rows[-1]
        next_cursor = {
            "created_at": last["created_at"],
            "conversation_id": str(last["post_ask_session_id"]),
        }
    return {
        "conversations": [
            {
                "conversation_id": str(row["post_ask_session_id"]),
                "title": row["conversation_title"],
                "updated_at": row["updated_at"],
                "turn_count": row["turn_count"],
            }
            for row in page_rows
        ],
        "next_cursor": next_cursor,
    }


async def _visible_post_ids_batch(
    conn: asyncpg.Connection,
    conversation_id: UUID,
    turn_ordinals: list[int],
    can_see_post: Callable[[asyncpg.Record], bool],
    *,
    source: bool,
) -> dict[int, tuple[list[str], dict[str, asyncpg.Record]]]:
    """Reauthorize every turn's sources or citations in one query.

    Fetches all `turn_ordinals` at once instead of one query per turn, so a
    conversation's query count stays constant regardless of how many turns
    it has. Returns each turn's currently-visible post ids and rows, keyed
    by turn ordinal; a turn with no visible rows still gets an empty entry.
    """
    by_turn: dict[int, tuple[list[str], dict[str, asyncpg.Record]]] = {
        ordinal: ([], {}) for ordinal in turn_ordinals
    }
    if not turn_ordinals:
        return by_turn
    if source:
        rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            f"""
        select relation.turn_ordinal as turn_ordinal,
               relation.source_post_id::text as post_id, relation.source_ordinal as ordinal,
               post.post_title, post.visibility_code, post.corporate_entity_id,
               post.process_unit_id,
               post.author_account_id, post.source_detail_state_code
          from post_ask_turn_source relation
          join source_post post on post.post_id = relation.source_post_id
         where relation.post_ask_session_id = $1
           and relation.turn_ordinal = any($2::int[])
           and ({SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')})
         order by relation.turn_ordinal, relation.source_ordinal
        """,
            conversation_id,
            turn_ordinals,
        )
    else:
        rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            f"""
        select relation.turn_ordinal as turn_ordinal,
               relation.cited_post_id::text as post_id, relation.citation_ordinal as ordinal,
               post.post_title, post.visibility_code, post.corporate_entity_id,
               post.process_unit_id,
               post.author_account_id, post.source_detail_state_code
          from post_ask_turn_citation relation
          join source_post post on post.post_id = relation.cited_post_id
         where relation.post_ask_session_id = $1
           and relation.turn_ordinal = any($2::int[])
           and ({SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')})
         order by relation.turn_ordinal, relation.citation_ordinal
        """,
            conversation_id,
            turn_ordinals,
        )
    for row in rows:
        if not can_see_post(row):
            continue
        ordinal = int(row["turn_ordinal"])
        post_id = str(row["post_id"])
        ids, id_map = by_turn[ordinal]
        ids.append(post_id)
        id_map[post_id] = row
    return by_turn


async def fetch_conversation(
    conn: asyncpg.Connection,
    user_account_id: str,
    post_id: str,
    conversation_id: UUID,
    can_see_post: Callable[[asyncpg.Record], bool],
    *,
    turn_limit: int = 50,
    before_turn_ordinal: int | None = None,
) -> dict[str, Any] | None:
    """Return one owned transcript with currently authorized citations."""
    header = await conn.fetchrow(
        """
        select post_ask_session_id
          from post_ask_session
         where post_ask_session_id = $1
           and user_account_id = $2
           and post_id = $3
        """,
        conversation_id,
        user_account_id,
        post_id,
    )
    if header is None:
        return None

    title_question = await conn.fetchval(
        """
        select question_text
          from post_ask_turn
         where post_ask_session_id = $1
         order by turn_ordinal
         limit 1
        """,
        conversation_id,
    )
    if before_turn_ordinal is None:
        turns = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            """
        select turn_ordinal, question_text, answer_text
          from post_ask_turn
         where post_ask_session_id = $1
         order by turn_ordinal desc
         limit $2
            """,
            conversation_id,
            turn_limit + 1,
        )
    else:
        turns = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            """
        select turn_ordinal, question_text, answer_text
          from post_ask_turn
         where post_ask_session_id = $1
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
    ordinals = [int(turn["turn_ordinal"]) for turn in turns]
    sources_by_turn = await _visible_post_ids_batch(
        conn, conversation_id, ordinals, can_see_post, source=True
    )
    citations_by_turn = await _visible_post_ids_batch(
        conn, conversation_id, ordinals, can_see_post, source=False
    )
    exchanges: list[dict[str, Any]] = []
    for turn in turns:
        ordinal = int(turn["turn_ordinal"])
        source_ids, _ = sources_by_turn[ordinal]
        cited_ids, cited_rows = citations_by_turn[ordinal]
        exchanges.append(
            {
                "turn_id": f"{conversation_id}:{ordinal}",
                "question_text": turn["question_text"],
                "answer_text": turn["answer_text"],
                "cited_post_ids": cited_ids,
                "cited_posts": [
                    {"post_id": post_id_value, "post_title": cited_rows[post_id_value]["post_title"]}
                    for post_id_value in cited_ids
                ],
                "source_post_ids": source_ids,
            }
        )
    title = title_question[:80] if title_question else None
    return {
        "conversation_id": str(header["post_ask_session_id"]),
        "title": title,
        "exchanges": exchanges,
        "older_cursor": str(turns[0]["turn_ordinal"]) if has_older and turns else None,
    }


async def _ensure_sources_visible(
    conn: asyncpg.Connection,
    source_post_ids: list[str],
    can_see_post: Callable[[asyncpg.Record], bool],
) -> None:
    """Lock and re-authorize every source before dependent rows are inserted."""
    # Safe SQL: the only interpolation is the repository-owned eligibility
    # expression; every request value remains an asyncpg parameter.
    rows = await conn.fetch(  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
        f"""
        select post.post_id::text as post_id, post.post_title,
               post.visibility_code, post.corporate_entity_id,
               post.process_unit_id,
               post.author_account_id, post.source_detail_state_code
          from source_post post
         where post.post_id = any($1::uuid[])
           and ({SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')})
         for share of post
        """,
        source_post_ids,
    )
    if len(rows) != len(source_post_ids) or any(
        not can_see_post(row) for row in rows
    ):
        raise PostAskEvidenceChanged


async def persist_turn(
    conn: asyncpg.Connection,
    user_account_id: str,
    post_id: str,
    conversation_id: UUID | None,
    question: str,
    answer_text: str,
    source_post_ids: Iterable[str],
    cited_post_ids: Iterable[str],
    can_see_post: Callable[[asyncpg.Record], bool] | None = None,
) -> UUID:
    """Append one completed turn and return the conversation id."""
    source_ids = list(dict.fromkeys(str(post_id_value) for post_id_value in source_post_ids))
    source_set = set(source_ids)
    cited_ids = list(
        dict.fromkeys(str(post_id_value) for post_id_value in cited_post_ids if str(post_id_value) in source_set)
    )
    async with conn.transaction():
        if can_see_post is not None:
            await _ensure_sources_visible(conn, source_ids, can_see_post)
        if conversation_id is None:
            conversation_id = uuid4()
            await conn.execute(
                """
                insert into post_ask_session (post_ask_session_id, post_id, user_account_id)
                values ($1, $2, $3)
                """,
                conversation_id,
                post_id,
                user_account_id,
            )
        else:
            conversation = await conn.fetchrow(
                """
                select post_ask_session_id
                  from post_ask_session
                 where post_ask_session_id = $1
                   and user_account_id = $2
                   and post_id = $3
                 for update
                """,
                conversation_id,
                user_account_id,
                post_id,
            )
            if conversation is None:
                raise PostAskConversationNotFound

        ordinal = int(
            await conn.fetchval(
                "select coalesce(max(turn_ordinal), 0) + 1 from post_ask_turn where post_ask_session_id = $1",
                conversation_id,
            )
        )
        await conn.execute(
            """
            insert into post_ask_turn
                (post_ask_session_id, turn_ordinal, question_text, answer_text)
            values ($1, $2, $3, $4)
            """,
            conversation_id,
            ordinal,
            question,
            answer_text,
        )
        for source_ordinal, source_post_id in enumerate(source_ids):
            await conn.execute(
                """
                insert into post_ask_turn_source
                    (post_ask_session_id, turn_ordinal, source_ordinal, source_post_id)
                values ($1, $2, $3, $4)
                """,
                conversation_id,
                ordinal,
                source_ordinal,
                source_post_id,
            )
        for citation_ordinal, cited_post_id in enumerate(cited_ids):
            await conn.execute(
                """
                insert into post_ask_turn_citation
                    (post_ask_session_id, turn_ordinal, citation_ordinal, cited_post_id)
                values ($1, $2, $3, $4)
                """,
                conversation_id,
                ordinal,
                citation_ordinal,
                cited_post_id,
            )
        await conn.execute(
            "update post_ask_session set updated_at = now() where post_ask_session_id = $1",
            conversation_id,
        )
    assert conversation_id is not None
    return conversation_id
