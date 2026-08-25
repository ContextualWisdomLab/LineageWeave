"""Evidence-constrained semantic query rewriting through contextual-orchestrator."""

from __future__ import annotations

import json
from typing import ClassVar, Protocol

from .http_client import chat_completion_content, post_json


class SemanticQueryClient(Protocol):
    """Port for rewriting a natural-language question into retrieval phrases."""

    available: bool

    def rewrite(self, question: str) -> tuple[str, ...]:
        """Return bounded literal phrases selected from ``question``."""
        raise NotImplementedError


class NullSemanticQueryClient:
    """Unavailable query-rewrite channel; callers retain the original query."""

    available = False

    def rewrite(self, question: str) -> tuple[str, ...]:
        """Raise because no orchestrator-backed rewriter is configured."""
        raise RuntimeError("semantic query rewriting is not available")


class ContextualOrchestratorSemanticQueryClient:
    """Select literal retrieval phrases through contextual-orchestrator."""

    available = True
    _SCHEMA: ClassVar[dict[str, object]] = {
        "type": "object",
        "properties": {
            "search_phrases": {
                "type": "array",
                "minItems": 1,
                "maxItems": 32,
                "items": {"type": "string", "minLength": 1},
            }
        },
        "required": ["search_phrases"],
        "additionalProperties": False,
    }

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 180.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    @classmethod
    def request_payload(cls, question: str) -> dict[str, object]:
        """Return the strict, provider-neutral rewrite request."""
        return {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Select the smallest set of literal phrases from the supplied question "
                        "that name its requested entities, projects, people, organizations, "
                        "relationships, or ontology concepts. Preserve each phrase exactly as it "
                        "appears in the question. Do not translate, expand, infer, or add facts. "
                        "Exclude conversational framing only when the remaining literal phrases "
                        "still preserve the requested subject. Return JSON only."
                    ),
                },
                {"role": "user", "content": question},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "semantic_search_phrases",
                    "strict": True,
                    "schema": cls._SCHEMA,
                },
            },
            "mode": "auto",
            "reasoning_effort": "auto",
            "max_tokens": 512,
        }

    def rewrite(self, question: str) -> tuple[str, ...]:
        """Return only exact question substrings from a valid response."""
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("semantic query requires a non-empty question")
        response = post_json(
            f"{self._base_url}/v1/chat/completions",
            self.request_payload(normalized_question),
            headers={"authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
        )
        parsed = json.loads(chat_completion_content(response))
        raw_phrases = parsed.get("search_phrases") if isinstance(parsed, dict) else None
        if not isinstance(raw_phrases, list):
            raise ValueError("semantic query response has no search_phrases array")
        phrases: list[str] = []
        seen: set[str] = set()
        for value in raw_phrases:
            if not isinstance(value, str):
                raise ValueError("semantic query phrase is not text")
            phrase = value.strip()
            key = phrase.casefold()
            if not phrase or phrase not in normalized_question:
                raise ValueError("semantic query phrase is not a literal question substring")
            if key not in seen:
                phrases.append(phrase)
                seen.add(key)
        if not phrases:
            raise ValueError("semantic query response contains no valid phrase")
        if len(phrases) > 32:
            raise ValueError("semantic query response contains too many phrases")
        return tuple(phrases)
