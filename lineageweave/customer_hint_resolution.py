"""Resolves an opaque source-system customer code (e.g. an ERP customer
number) to the real-world company it refers to, using the text of posts
that share the code as evidence.

This is a different problem from
:mod:`lineageweave.organization_name_resolution`: that module expands an
abbreviated name that is itself mentioned in the text ("AGP" ->
"Aurora Grid Power"). A source-system code like a customer number never
appears in a post's own prose at all -- it is only a foreign-key-shaped
hint column value (``source_post.source_customer_code``) -- so there is no
raw name to expand, only surrounding post content to read.

Same pluggable-client, never-fake-a-missing-channel discipline as every
other channel in this package: the default :class:`NullCustomerHintResolutionClient`
makes the channel unavailable rather than guessing.
"""

from __future__ import annotations

from typing import Protocol

from .http_client import chat_completion_content, post_json
from .organization_name_resolution import parse_resolution_response

_RESOLUTION_PROMPT_TEMPLATE = """\
The excerpts below are from business records that all share the same
internal customer reference code "{hint_code}". This code never appears
in the records' own text -- it is only an internal lookup value -- so you
must infer the real-world company/organization these records are about
from what the text itself describes (who is visited, who is the
counterparty, whose facility or representatives are named).

Using ONLY what the text supports, determine that organization's full,
real-world name.

Reply with ONLY the full organization name on a single line, in its most
natural real-world form. If the text gives you no way to determine the
name with real confidence, reply with exactly: UNKNOWN

Excerpts:
{context}
"""


class CustomerHintResolutionClient(Protocol):
    """Proposes a real-world company name for an opaque customer code."""

    available: bool

    def resolve(self, hint_code: str, context_text: str) -> str | None:
        """Return the proposed company name, or ``None`` when undetermined.

        Implementations must raise if they cannot resolve. Protocol stubs
        raise ``NotImplementedError`` so a no-op body is never treated as
        a successful "undetermined" result.
        """
        raise NotImplementedError


class NullCustomerHintResolutionClient:
    """No LLM orchestrator configured -- hint resolution is unavailable."""

    available = False

    def resolve(self, hint_code: str, context_text: str) -> str | None:
        """Implement the resolve operation for this channel."""
        raise RuntimeError("NullCustomerHintResolutionClient cannot resolve; check .available first")


class ContextualOrchestratorCustomerHintResolutionClient:
    """Calls ``POST {base_url}/v1/chat/completions`` with ``mode="auto"``."""

    available = True

    def __init__(
        self, base_url: str, api_key: str, *, reasoning_effort: str = "auto", timeout: float = 30.0
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._reasoning_effort = reasoning_effort
        self._timeout = timeout

    def resolve(self, hint_code: str, context_text: str) -> str | None:
        """Resolve the customer code against the given post excerpts."""
        prompt = _RESOLUTION_PROMPT_TEMPLATE.format(hint_code=hint_code, context=context_text)
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
        return parse_resolution_response(content)
