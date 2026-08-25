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

from .http_client import chat_completion_content, post_json

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
    """One numbered post and its persisted evidence for chat reasoning."""

    post_id: str
    post_title: str
    post_body: str
    graph_facts: tuple[str, ...] = field(default_factory=tuple)
    evidence_facts: tuple[str, ...] = field(default_factory=tuple)
    source_post_revision_id: str | None = None
    evidence_available_at: str | None = None
    knowledge_cutoff: str | None = None
    live_changed_after_cutoff: bool = False
    historical_body_unavailable: bool = False
    unavailable_channels: tuple[str, ...] = field(default_factory=tuple)


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
) -> list[dict[str, str | bool | list[str] | None]]:
    """Titles for cited ids, in citation order. Unknown ids are dropped.

    The sliding evidence chip must show the source post's title, not a
    truncated UUID -- a missing title is omitted, never invented.
    """
    by_id = {source.post_id: source for source in sources}
    citations: list[dict[str, str | bool | list[str] | None]] = []
    for post_id in cited_post_ids:
        source = by_id.get(post_id)
        if source is None:
            continue
        citation: dict[str, str | bool | list[str] | None] = {
            "post_id": post_id,
            "post_title": source.post_title,
        }
        if source.knowledge_cutoff is not None:
            citation.update(
                {
                    "source_post_revision_id": source.source_post_revision_id,
                    "evidence_available_at": source.evidence_available_at,
                    "knowledge_cutoff": source.knowledge_cutoff,
                    "live_changed_after_cutoff": source.live_changed_after_cutoff,
                    "historical_body_unavailable": source.historical_body_unavailable,
                    "unavailable_channels": list(source.unavailable_channels),
                }
            )
        citations.append(citation)
    return citations


def historical_body_limitations(
    sources: list[ChatSourceDocument] | tuple[ChatSourceDocument, ...],
) -> list[dict[str, object]]:
    """Return explicit cutoff limitations without exposing a live replacement."""

    return [
        {
            "post_id": source.post_id,
            "limitation_code": "historical_body_unavailable",
            "unavailable_channels": list(source.unavailable_channels),
        }
        for source in sources
        if source.historical_body_unavailable
    ]


def ask_grounding_status(
    sources: list[ChatSourceDocument] | tuple[ChatSourceDocument, ...],
    knowledge_cutoff: str | None,
) -> str:
    """Classify live, complete-cutoff, or partial-cutoff source grounding."""

    if knowledge_cutoff is None:
        return "live_only"
    if not sources or any(source.historical_body_unavailable for source in sources):
        return "partially_cutoff_grounded"
    return "fully_cutoff_grounded"


def _buyer_evidence_kind(fact: str) -> str:
    if fact.startswith("time axis:"):
        return "time_axis"
    if fact.startswith("project:"):
        return "semantic_project"
    if fact.startswith("actor:"):
        return "semantic_role"
    if fact.startswith("Keyman mention:"):
        return "semantic_keyman"
    return "source_field"


def _buyer_evidence_text(fact: str) -> str:
    cleaned = re.sub(r"\s*\|\s*(?:ontology_iri|extraction_method|confidence):\s*[^|\[]+", "", fact)
    cleaned = re.sub(r"\s*\[provenance=[^]]+\]", "", cleaned)
    return " ".join(cleaned.split())


def cited_post_evidence(
    sources: list[ChatSourceDocument] | tuple[ChatSourceDocument, ...],
    cited_post_ids: tuple[str, ...] | list[str],
) -> list[dict[str, object]]:
    """Return buyer-safe persisted evidence for cited posts.

    Provider names, ontology IRIs, and storage provenance are prompt metadata,
    not Buyer UI content. The evidence value itself remains visible so the
    cited post can be opened and checked against its full body.
    """
    by_id = {source.post_id: source for source in sources}
    result: list[dict[str, object]] = []
    for post_id in cited_post_ids:
        source = by_id.get(post_id)
        if source is None:
            continue
        facts: list[dict[str, str]] = []
        seen: set[str] = set()
        for fact in source.evidence_facts:
            text = _buyer_evidence_text(fact)
            if not text or text in seen:
                continue
            seen.add(text)
            facts.append({"kind": _buyer_evidence_kind(fact), "text": text})
        result.append({"post_id": post_id, "facts": facts})
    return result


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
        """Answer the question using the supplied source documents."""
        raise RuntimeError("NullPostChatClient cannot answer; check .available first")


_CHAT_PROMPT_TEMPLATE = """\
Answer the question below using ONLY the numbered source documents
provided -- do not use outside knowledge, and do not answer if the
sources don't actually support an answer (say so instead of guessing).

Do not output a reasoning trace. Return the JSON object immediately.

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

_CHAT_REQUEST_PROMPT_TEMPLATE = """\
Answer the question using ONLY the numbered source documents below. Do not
use outside knowledge or guess. Be concise and preserve the evidence facts.
Write the answer first, then a new line exactly beginning CITED SOURCES:
followed by the 1-based source numbers separated by commas. Cite every
source the answer used; write NONE when the sources do not support an answer.

Sources:
{sources_block}

Question: {question}
"""


def _strip_code_fence(content: str) -> str:
    """Implement the _strip_code_fence operation for this channel."""
    match = _CODE_FENCE_PATTERN.search(content)
    return match.group(1) if match else content


def _render_sources_block(sources: list[ChatSourceDocument]) -> str:
    """Implement the _render_sources_block operation for this channel."""
    blocks: list[str] = []
    for i, source in enumerate(sources, start=1):
        body = source.post_body
        if len(body) > 4000:
            body = body[:4000] + "\n[Source body truncated; open the cited post for the full body.]"
        graph_block = ""
        evidence_block = ""
        if source.graph_facts:
            graph_block = (
                "\nPersisted Knowledge Graph facts (use only as evidence; each fact "
                "names its evidence post_id):\n"
                + "\n".join(f"- {fact}" for fact in source.graph_facts)
            )
        if source.evidence_facts:
            evidence_block = (
                "\nPersisted source/semantic evidence (use as evidence; do not treat "
                "raw source hints as resolved ontology assertions):\n"
                + "\n".join(f"- {fact}" for fact in source.evidence_facts)
            )
        blocks.append(
            f"[Source {i}] (post_id={source.post_id})\n"
            f"Title: {source.post_title}\n{body}{graph_block}{evidence_block}"
        )
    return "\n\n".join(blocks)


def _parse_plain_chat_response(
    content: str, sources: list[ChatSourceDocument]
) -> ChatAnswer | None:
    """Parse the provider-compatible answer/citation marker."""
    plain = _strip_code_fence(content).strip()
    match = re.search(r"(?im)^\s*CITED SOURCES\s*:\s*(.*)$", plain)
    if match is None:
        return None
    answer_text = re.sub(r"(?im)^\s*ANSWER\s*:\s*", "", plain[: match.start()]).strip()
    if not answer_text:
        return None
    cited_post_ids: list[str] = []
    raw_citations = match.group(1).strip()
    if raw_citations.upper() != "NONE":
        for raw_number in re.findall(r"\d+", raw_citations):
            source_index = int(raw_number) - 1
            if 0 <= source_index < len(sources):
                post_id = sources[source_index].post_id
                if post_id not in cited_post_ids:
                    cited_post_ids.append(post_id)
    return ChatAnswer(answer_text=answer_text, cited_post_ids=tuple(cited_post_ids))


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
    """Calls the orchestrator's evidence-preserving ``mode="auto"`` boundary.

    contextual-orchestrator resolves ``auto`` using its own capability/routing
    policy (ADR 0083); the prompt enforces evidence-only answers and citations.
    """

    available = True

    def __init__(
        self, base_url: str, api_key: str, *, reasoning_effort: str = "auto", timeout: float = 180.0
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._reasoning_effort = reasoning_effort
        self._timeout = timeout

    def answer(self, question: str, sources: list[ChatSourceDocument]) -> ChatAnswer:
        """Answer the question using the supplied source documents."""
        prompt = _CHAT_REQUEST_PROMPT_TEMPLATE.format(
            sources_block=_render_sources_block(sources), question=question
        )
        body = post_json(
            f"{self._base_url}/v1/chat/completions",
            {
                "messages": [{"role": "user", "content": prompt}],
                "mode": "auto",
                "reasoning_effort": self._reasoning_effort,
            },
            headers={"authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
        )
        content = chat_completion_content(body)
        answer = _parse_plain_chat_response(content, sources)
        if answer is None:
            raise ValueError("chat response did not match the required format")
        return answer
