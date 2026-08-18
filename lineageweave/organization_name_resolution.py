"""Resolves an abbreviated or slang organization name (e.g. "AGP") to
its full canonical name using LLM context, then cross-verifies the
proposed name against external web search before it is trusted --
:mod:`lineageweave.corporate_hierarchy_resolution`'s character-similarity
matching cannot bridge this gap on its own: an initialism/acronym shares
almost no substring with its expansion, so no similarity threshold
recovers it. This module runs first, so its output feeds
``resolve_corporate_entity`` a name with a real chance of matching, not
instead of it.

Grounded in SKOS (Miles & Bechhofer, 2009): ``skos:prefLabel`` (a
resource's single preferred/canonical label) and ``skos:altLabel`` (an
alternative label -- exactly the abbreviation/synonym case) are the
standard vocabulary for this raw-name/canonical-name pair. See
docs/adr/0008-organization-abbreviation-resolution.md.

Same pluggable-client, never-fake-a-missing-channel discipline as every
other channel in this package -- and, specifically, an LLM's proposed
canonical name is never trusted on its own: it is only usable once
:mod:`lineageweave.relation_verification`'s external-search check
corroborates it, reusing that module's client rather than duplicating a
second web-search integration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .http_client import post_json
from .relation_verification import (
    STATUS_PENDING,
    RelationVerificationClient,
)


@dataclass(frozen=True)
class OrganizationNameResolution:
    """One raw name's resolution outcome, ready to persist to
    ``organization_name_resolution``.

    Attributes:
        raw_organization_name: the abbreviated/slang name as mentioned
            in the source text (``skos:altLabel``).
        resolved_organization_name: the LLM's proposed full/canonical
            name (``skos:prefLabel``).
        verification_status_code: ``relation_verification_status``
            lookup code -- whether external search corroborated the
            resolved name, reusing the same category and semantics
            :mod:`lineageweave.relation_verification` already defines.
        verification_evidence_url: the corroborating search result's
            URL, or ``None`` when uncorroborated or verification itself
            was unavailable.
    """

    raw_organization_name: str
    resolved_organization_name: str
    verification_status_code: str
    verification_evidence_url: str | None


class OrganizationNameResolutionClient(Protocol):
    """Proposes a full/canonical name for an abbreviated organization mention."""

    available: bool

    def resolve(self, raw_name: str, context_text: str) -> str | None:
        """Return the proposed canonical name, or ``None`` when the
        model cannot determine one from the given context.

        Implementations must raise if the call itself fails (network
        error, malformed response) -- a failed call is not the same
        outcome as "the model looked and found nothing to propose."
        Protocol stubs raise ``NotImplementedError`` so a no-op body is
        never treated as a successful empty result.
        """
        raise NotImplementedError


class NullOrganizationNameResolutionClient:
    """No LLM orchestrator configured -- name resolution is unavailable."""

    available = False

    def resolve(self, raw_name: str, context_text: str) -> str | None:
        """Resolve the raw organization name against the available evidence."""
        raise RuntimeError(
            "NullOrganizationNameResolutionClient cannot resolve; check .available first"
        )


_RESOLUTION_PROMPT_TEMPLATE = """\
The text below mentions an organization by the short/abbreviated name
"{raw_name}" (this may be a Korean-style contraction, an initialism, or
another kind of shorthand -- e.g. "AGP" is a synthetic contraction
for "Aurora Grid Power").

Using ONLY what the text itself supports (do not guess from the
abbreviation's letters/syllables alone if the text gives no supporting
context), determine the organization's full, real-world name.

Reply with ONLY the full organization name on a single line, in its
most natural real-world form. If the text gives you no way to determine
the full name with real confidence, reply with exactly: UNKNOWN

Text: {context}
"""


def parse_resolution_response(content: str) -> str | None:
    """Parses the LLM's reply into a proposed canonical name, or `None`
    when it declined (``UNKNOWN``) or replied with nothing usable.

    A one-line reply is the contract; only the first line is trusted --
    a multi-line reply means the model did not follow instructions, and
    trusting the wrong line would risk persisting prose as a name.
    """
    stripped = content.strip()
    if not stripped or stripped.upper() == "UNKNOWN":
        return None
    first_line = stripped.splitlines()[0].strip()
    if not first_line or first_line.upper() == "UNKNOWN":
        return None
    return first_line


class ContextualOrchestratorOrganizationNameResolutionClient:
    """Calls ``POST {base_url}/v1/chat/completions`` with ``mode="auto"``."""

    available = True

    def __init__(
        self, base_url: str, api_key: str, *, reasoning_effort: str = "medium", timeout: float = 30.0
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._reasoning_effort = reasoning_effort
        self._timeout = timeout

    def resolve(self, raw_name: str, context_text: str) -> str | None:
        """Resolve the raw organization name against the available evidence."""
        prompt = _RESOLUTION_PROMPT_TEMPLATE.format(raw_name=raw_name, context=context_text)
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
        content = body["choices"][0]["message"]["content"]
        return parse_resolution_response(content)


def resolve_and_verify_organization_name(
    raw_name: str,
    context_text: str,
    resolution_client: OrganizationNameResolutionClient,
    verification_client: RelationVerificationClient,
) -> OrganizationNameResolution | None:
    """Runs the full resolve-then-verify pipeline for one raw name.

    Returns ``None`` when resolution is unavailable, the model proposed
    nothing, or it proposed back the same string it was given (not a
    real resolution) -- the caller keeps using the raw name as-is in
    every one of these cases, the same missing-vs-negative discipline
    every other channel in this package follows. A verified result's
    ``verification_status_code`` is only ever ``verify_corroborated`` /
    ``verify_uncorroborated`` (real search ran) or ``verify_pending``
    (search itself is unavailable, not that it ran and found nothing) --
    never fabricated.
    """
    if not resolution_client.available:
        return None
    candidate = resolution_client.resolve(raw_name, context_text)
    if candidate is None:
        return None
    resolved_name = candidate.strip()
    if not resolved_name or resolved_name == raw_name.strip():
        return None

    if not verification_client.available:
        return OrganizationNameResolution(
            raw_organization_name=raw_name,
            resolved_organization_name=resolved_name,
            verification_status_code=STATUS_PENDING,
            verification_evidence_url=None,
        )

    result = verification_client.verify(resolved_name, raw_name)
    return OrganizationNameResolution(
        raw_organization_name=raw_name,
        resolved_organization_name=resolved_name,
        verification_status_code=result.status_code,
        verification_evidence_url=result.evidence_url,
    )
