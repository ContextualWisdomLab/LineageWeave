"""Bounded, authorization-preserving Global Ask application service."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any

from backend.app.auth import CurrentAccount
from backend.app.global_ask_media import GlobalAskContentBlock, load_global_ask_content_blocks
from backend.app.post_chat_ingestion import gather_chat_sources
from lineageweave.http_client import HttpClientError
from lineageweave.post_chat import (
    ChatSourceDocument,
    PostChatClient,
    cited_post_summaries,
)

MAX_QUESTION_CHARS = 2_000
MAX_SEARCH_TERMS = 8
MAX_SEARCH_ROWS_PER_TERM = 24
MAX_GLOBAL_SOURCES = 6
MAX_SOURCE_BODY_CHARS = 4_000
_POST_READ = "post_read"
_STOP_TERMS = frozenset(
    {
        "what",
        "which",
        "where",
        "when",
        "who",
        "why",
        "how",
        "the",
        "this",
        "that",
        "post",
        "posts",
        "무엇",
        "관련",
        "질문",
        "게시글",
        "글",
    }
)

_SEARCH_SQL = """
select p.post_id, p.post_title, p.post_body, p.visibility_code, p.corporate_entity_id,
       p.author_account_id, p.process_unit_id, p.voc_type_code,
       p.thread_group_key, p.secondary_grouping_key, ce.corporate_entity_code,
       pu.process_unit_code, p.created_at,
       (case when lower(p.post_title) like '%' || lower($2) || '%' then 3 else 0 end
        + case when lower(left(p.post_body, 16384)) like '%' || lower($2) || '%' then 1 else 0 end)
       as relevance_score
  from source_post p
  join corporate_entity ce on ce.corporate_entity_id = p.corporate_entity_id
  left join process_unit pu on pu.process_unit_id = p.process_unit_id
 where (p.visibility_code = 'public' or p.corporate_entity_id = any($1::uuid[]))
   and (lower(p.post_title) like '%' || lower($2) || '%'
        or lower(left(p.post_body, 16384)) like '%' || lower($2) || '%')
 order by relevance_score desc, p.created_at desc, p.post_id desc
 limit $3
"""

_FALLBACK_SQL = """
select p.post_id, p.post_title, p.post_body, p.visibility_code, p.corporate_entity_id,
       p.author_account_id, p.process_unit_id, p.voc_type_code,
       p.thread_group_key, p.secondary_grouping_key, ce.corporate_entity_code,
       pu.process_unit_code, p.created_at,
       0 as relevance_score
  from source_post p
  join corporate_entity ce on ce.corporate_entity_id = p.corporate_entity_id
  left join process_unit pu on pu.process_unit_id = p.process_unit_id
 where p.visibility_code = 'public' or p.corporate_entity_id = any($1::uuid[])
 order by p.created_at desc, p.post_id desc
 limit 1
"""


class GlobalAskError(RuntimeError):
    """Base class for safe, user-actionable Global Ask failures."""


class GlobalAskForbiddenError(GlobalAskError):
    """Caller is authenticated but lacks the product read permission."""


class GlobalAskNoEvidenceError(GlobalAskError):
    """No source post is visible to the caller."""


class GlobalAskUnavailableError(GlobalAskError):
    """The configured reason-and-cite channel could not answer safely."""


@dataclass(frozen=True)
class GlobalAskAnswer:
    """Structured Global Ask answer and its complete bounded evidence identity."""

    answer_text: str
    anchor_post_id: str
    cited_post_ids: tuple[str, ...]
    cited_posts: tuple[dict[str, str], ...]
    source_post_ids: tuple[str, ...]
    timeline: tuple[dict[str, str], ...] = ()
    content_blocks: tuple[GlobalAskContentBlock, ...] = ()


def _timeline(sources: list[ChatSourceDocument]) -> tuple[dict[str, str], ...]:
    """Return the authorized source bundle as a dated, relation-labelled timeline."""
    dated = [source for source in sources if source.occurred_at]

    def sort_key(source: ChatSourceDocument) -> tuple[datetime, str]:
        assert source.occurred_at is not None
        try:
            occurred_at = datetime.fromisoformat(source.occurred_at.replace("Z", "+00:00"))
        except ValueError:
            occurred_at = datetime.max.replace(tzinfo=timezone.utc)
        return occurred_at, source.post_id

    return tuple(
        {
            "post_id": source.post_id,
            "post_title": source.post_title,
            "occurred_at": source.occurred_at,
            "lineage_relation": source.lineage_relation,
        }
        for source in sorted(dated, key=sort_key)
    )


def validate_global_question(question: str) -> str:
    """Strip and validate a Global Ask question before retrieval or LLM use."""
    normalized = question.strip()
    if not normalized:
        raise ValueError("question is required")
    if len(normalized) > MAX_QUESTION_CHARS:
        raise ValueError(f"question must be at most {MAX_QUESTION_CHARS} characters")
    return normalized


def extract_search_terms(question: str) -> tuple[str, ...]:
    """Extract a deterministic, Unicode-aware, bounded set of retrieval terms."""
    terms: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"[^\W_]+(?:-[^\W_]+)*", question, flags=re.UNICODE):
        normalized = token.casefold()
        if len(normalized) < 2 or normalized in _STOP_TERMS or normalized in seen:
            continue
        seen.add(normalized)
        terms.append(normalized)
        if len(terms) == MAX_SEARCH_TERMS:
            break
    return tuple(terms)


def _can_see_post(account: CurrentAccount, post: Any) -> bool:
    """Apply the same public-or-affiliated ABAC rule as the REST API."""
    if post["visibility_code"] == "public":
        return True
    return str(post["corporate_entity_id"]) in account.corporate_entity_ids


async def _select_anchor(conn: Any, account: CurrentAccount, question: str) -> Any | None:
    """Choose the highest-scoring visible anchor, with a bounded recent fallback."""
    candidates: dict[str, Any] = {}
    aggregate_scores: dict[str, float] = {}
    entity_ids = list(account.corporate_entity_ids)
    search_terms = extract_search_terms(question)
    for term in search_terms:
        rows = await conn.fetch(_SEARCH_SQL, entity_ids, term, MAX_SEARCH_ROWS_PER_TERM)
        for row in rows:
            if not _can_see_post(account, row):
                continue
            post_id = str(row["post_id"])
            candidates[post_id] = row
            aggregate_scores[post_id] = aggregate_scores.get(post_id, 0.0) + float(
                row.get("relevance_score", 0)
            )
    if candidates:
        return max(
            candidates.values(),
            key=lambda row: (
                aggregate_scores[str(row["post_id"])],
                row["created_at"],
                str(row["post_id"]),
            ),
        )
    if search_terms:
        return None
    rows = await conn.fetch(_FALLBACK_SQL, entity_ids)
    return next((row for row in rows if _can_see_post(account, row)), None)


def _bounded_sources(sources: list[ChatSourceDocument]) -> list[ChatSourceDocument]:
    """Bound source count and text while retaining each source's identity."""
    bounded: list[ChatSourceDocument] = []
    seen: set[str] = set()
    for source in sources:
        if source.post_id in seen:
            continue
        seen.add(source.post_id)
        body = source.post_body[:MAX_SOURCE_BODY_CHARS]
        bounded.append(replace(source, post_body=body))
        if len(bounded) == MAX_GLOBAL_SOURCES:
            break
    return bounded


def _llm_request_context(anchor: Any, account: CurrentAccount) -> tuple[str, dict[str, str]]:
    """Build stable per-post correlation and non-secret evidence metadata."""
    post_id = str(anchor["post_id"])
    session_id = f"lineageweave:post:{post_id}"
    metadata = {
        "session_id": session_id,
        "post_id": post_id,
        "requesting_user_account_id": account.user_account_id,
    }
    for source_key, metadata_key in (
        ("author_account_id", "author_account_id"),
        ("corporate_entity_id", "corporate_entity_id"),
        ("corporate_entity_code", "corp_code"),
        ("process_unit_id", "process_unit_id"),
        ("process_unit_code", "pu_code"),
        ("voc_type_code", "voc_type_code"),
        ("thread_group_key", "thread_group_key"),
        ("secondary_grouping_key", "secondary_grouping_key"),
    ):
        value = anchor.get(source_key)
        if value not in (None, ""):
            metadata[metadata_key] = str(value)
    return session_id, metadata


async def answer_global_question(
    conn: Any,
    account: CurrentAccount,
    client: PostChatClient,
    question: str,
    *,
    vision_client: Any | None = None,
) -> GlobalAskAnswer:
    """Answer from caller-visible post and lineage evidence without persisting a write."""
    normalized_question = validate_global_question(question)
    if not account.has_permission(_POST_READ):
        raise GlobalAskForbiddenError("account lacks the post_read permission")
    anchor = await _select_anchor(conn, account, normalized_question)
    if anchor is None:
        raise GlobalAskNoEvidenceError("no authorized LineageWeave evidence is available")
    if not client.available:
        raise GlobalAskUnavailableError("contextual-orchestrator is unavailable")
    session_id, metadata = _llm_request_context(anchor, account)
    try:
        gathered_sources = await gather_chat_sources(
            conn,
            str(anchor["post_id"]),
            lambda row: _can_see_post(account, row),
            vision_client=vision_client,
            session_id=session_id,
            metadata=metadata,
        )
    except (HttpClientError, KeyError, OSError, TypeError, ValueError) as exc:
        raise GlobalAskUnavailableError(f"evidence retrieval failed: {exc}") from exc
    sources = _bounded_sources(gathered_sources)
    if not sources:
        raise GlobalAskNoEvidenceError("no authorized LineageWeave evidence is available")
    try:
        answer = await asyncio.to_thread(
            client.answer,
            normalized_question,
            sources,
            session_id=session_id,
            metadata=metadata,
        )
    except (HttpClientError, KeyError, OSError, TypeError, ValueError) as exc:
        raise GlobalAskUnavailableError(f"contextual-orchestrator failed: {exc}") from exc
    source_ids = tuple(source.post_id for source in sources)
    allowed_ids = set(source_ids)
    cited_ids = tuple(dict.fromkeys(post_id for post_id in answer.cited_post_ids if post_id in allowed_ids))
    if not cited_ids:
        raise GlobalAskUnavailableError(
            "contextual-orchestrator returned no citation from the authorized source bundle"
        )
    cited_posts = tuple(cited_post_summaries(sources, cited_ids))
    return GlobalAskAnswer(
        answer_text=answer.answer_text,
        anchor_post_id=str(anchor["post_id"]),
        cited_post_ids=cited_ids,
        cited_posts=cited_posts,
        source_post_ids=source_ids,
        timeline=_timeline(sources),
        content_blocks=await load_global_ask_content_blocks(
            conn,
            answer.answer_text,
            cited_ids,
            account.user_account_id,
        ),
    )
