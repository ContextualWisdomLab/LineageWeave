"""In-popup LLM chat, answering "what happened between these linked
events" using a post's own content plus its Event-Lineage-linked posts as
context -- with citations back to the specific source post(s) an answer
drew from, the data shape the frontend's sliding evidence panel needs.

Deliberately two explicit steps, not one undifferentiated prompt --
retrieval-augmented generation (Lewis et al., 2020): a *retrieve* step
(the caller -- ``backend/app/post_chat_ingestion.py`` -- assembles the
post's own content plus its lineage/Knowledge-Graph-linked posts as
numbered source documents) and a *reason-and-cite* step (this module's
client, prompted to answer using ONLY the numbered sources and to cite
which source numbers each part of its answer drew from). This is the
Agentic-workflow shape the product brief asks for (retrieve context ->
reason -> cite) without adding a full agent-framework dependency for what
two functions and a structured prompt already do -- Pydantic AI remains
an acceptable implementation choice if a future phase's chat needs
multi-turn tool use this simple two-step pipeline doesn't cover.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Protocol

from .http_client import post_json

CANONICAL_CHAT_QUESTION = "What happened between these events?"
CANONICAL_INVOLVED_QUESTION = "Who is involved?"
CANONICAL_COMMITMENT_QUESTION = "What is the next commitment?"

_TRAILING_PUNCT = re.compile(r"[?.!\s]+$")
_CANONICAL_QUESTION_NORM = "what happened between these events"
_INVOLVED_QUESTION_NORM = "who is involved"
_COMMITMENT_QUESTION_NORM = "what is the next commitment"


def normalize_chat_question(question: str) -> str:
    """Whitespace/case fold plus trailing-punctuation strip.

    Seeded Ask matches this form, never a live paraphrase. ``What
    happened?`` is an alias of the popup placeholder so a short type-in
    still hits the stored fixture answer. ``Who's involved?`` aliases
    the second seeded chip that names Keymen. ``What's the next
    commitment?`` aliases the third chip that names the Calendar ticket.
    """
    folded = _TRAILING_PUNCT.sub("", " ".join(question.strip().lower().split()))
    if folded == "what happened":
        return _CANONICAL_QUESTION_NORM
    if folded in {"who's involved", "who is involved here"}:
        return _INVOLVED_QUESTION_NORM
    if folded in {"what's the next commitment", "what is the next commitment here"}:
        return _COMMITMENT_QUESTION_NORM
    return folded


@dataclass(frozen=True)
class ChatSourceDocument:
    """One numbered source document available to the chat's reasoning step."""

    post_id: str
    post_title: str
    post_body: str


@dataclass(frozen=True)
class ChatAnswer:
    """The chat's answer plus which source post(s) it drew from -- the
    evidence-panel citation data.
    """

    answer_text: str
    cited_post_ids: tuple[str, ...] = field(default_factory=tuple)


def cited_post_summaries(
    sources: list[ChatSourceDocument] | tuple[ChatSourceDocument, ...],
    cited_post_ids: tuple[str, ...] | list[str],
) -> list[dict[str, str]]:
    """Titles for cited ids, in citation order. Unknown ids are dropped.

    The sliding evidence chip must show the source post's title, not a
    truncated UUID -- a missing title is omitted, never invented.
    """
    titles = {source.post_id: source.post_title for source in sources}
    return [
        {"post_id": post_id, "post_title": titles[post_id]}
        for post_id in cited_post_ids
        if post_id in titles
    ]


class PostChatClient(Protocol):
    """Answers a question using only the given numbered source documents."""

    available: bool

    def answer(self, question: str, sources: list[ChatSourceDocument]) -> ChatAnswer:
        """Answer ``question`` using only ``sources``, with citations.

        Implementations must raise if they cannot answer. Protocol stubs
        raise ``NotImplementedError`` so a no-op body is never treated as
        a successful empty result.
        """
        raise NotImplementedError


class NullPostChatClient:
    """No LLM orchestrator configured -- chat is unavailable."""

    available = False

    def answer(self, question: str, sources: list[ChatSourceDocument]) -> ChatAnswer:
        raise RuntimeError("NullPostChatClient cannot answer; check .available first")


_CHAT_PROMPT_TEMPLATE = """\
Answer the question below using ONLY the numbered source documents
provided -- do not use outside knowledge, and do not answer if the
sources don't actually support an answer (say so instead of guessing).

For every part of your answer, track which source number(s) it came from.

Reply with ONLY a JSON object (no markdown fences, no prose) with exactly
these fields:
  "answer_text": string -- your answer, in prose
  "cited_source_numbers": array of integers -- every source number (1-based)
    your answer actually drew from

Sources:
{sources_block}

Question: {question}
"""

_CODE_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _strip_code_fence(content: str) -> str:
    match = _CODE_FENCE_PATTERN.search(content)
    return match.group(1) if match else content


def _render_sources_block(sources: list[ChatSourceDocument]) -> str:
    return "\n\n".join(
        f"[Source {i}] (post_id={source.post_id})\nTitle: {source.post_title}\n{source.post_body}"
        for i, source in enumerate(sources, start=1)
    )


def parse_chat_response(content: str, sources: list[ChatSourceDocument]) -> ChatAnswer | None:
    """Parses the LLM's JSON object response into a `ChatAnswer`.

    Cited source numbers outside `1..len(sources)` are dropped rather than
    causing the whole response to fail -- a hallucinated citation number
    is a real, correctable model error, and dropping just that one
    citation is safer than discarding an otherwise-valid answer, or
    keeping a citation the evidence panel could never actually resolve to
    a source post.
    """
    try:
        parsed = json.loads(_strip_code_fence(content).strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None

    answer_text = parsed.get("answer_text")
    if not isinstance(answer_text, str) or not answer_text.strip():
        return None

    cited_numbers_raw = parsed.get("cited_source_numbers") or []
    if not isinstance(cited_numbers_raw, list):
        cited_numbers_raw = []
    cited_post_ids = tuple(
        sources[n - 1].post_id
        for n in cited_numbers_raw
        if isinstance(n, int) and 1 <= n <= len(sources)
    )
    return ChatAnswer(answer_text=answer_text.strip(), cited_post_ids=cited_post_ids)


class ContextualOrchestratorPostChatClient:
    """Calls ``POST {base_url}/v1/chat/completions`` with ``mode="verify"``
    -- a chat answer with citations is exactly the checked-judgment shape
    ``mode="verify"`` exists for (one worker call plus one checked
    verifier judgment), same reasoning ``adjudication_client`` already
    uses, not ``keyman_extraction``/``entity_relationship_classification``'s
    single-pass ``mode="route"`` structured extraction.
    """

    available = True

    def __init__(
        self, base_url: str, api_key: str, *, reasoning_effort: str = "high", timeout: float = 60.0
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._reasoning_effort = reasoning_effort
        self._timeout = timeout

    def answer(self, question: str, sources: list[ChatSourceDocument]) -> ChatAnswer:
        prompt = _CHAT_PROMPT_TEMPLATE.format(
            sources_block=_render_sources_block(sources), question=question
        )
        body = post_json(
            f"{self._base_url}/v1/chat/completions",
            {
                "messages": [{"role": "user", "content": prompt}],
                "mode": "verify",
                "reasoning_effort": self._reasoning_effort,
            },
            headers={"authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
        )
        content = body["choices"][0]["message"]["content"]
        answer = parse_chat_response(content, sources)
        if answer is None:
            raise ValueError(f"chat response did not match the required format: {content!r}")
        return answer
