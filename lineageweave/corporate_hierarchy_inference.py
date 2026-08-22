"""Infers where a newly-mentioned organization sits in a Group -> Company
-> Plant style hierarchy (e.g. "Acme Electronics South Plant" -> parent "Acme Electronics
한국" -> parent "Acme Group") when it does not already match an existing
``corporate_entity`` row -- the standing "통합 고객사 계열 tree AI"
(integrated customer affiliate tree) requirement this product has
always named, closing the gap that
:mod:`lineageweave.corporate_hierarchy_resolution`'s similarity
matching leaves open: matching only ever finds an ALREADY-cataloged
entity, it never creates one, so a unseen dataset's first mention of any
new counterparty organization stays permanently unresolved.

Grounded in the same collective-entity-resolution framing
(Bhattacharya & Getoor, 2007) already cited for
``corporate_hierarchy_resolution`` -- this module is the natural
extension of that same resolution pipeline to entity *creation* when no
existing candidate matches, not a separate technique. The hierarchy
itself is the same SKOS ``skos:broader``/``skos:narrower`` structure
``corporate_entity_level`` (ADR 0004) already uses on top of the
``parent_entity_id`` self-reference.

Same pluggable-client, never-fake-a-missing-channel, never-trust-an-
unverified-guess discipline as every other channel in this package: a
proposed new entity is only ever created after
:mod:`lineageweave.relation_verification`'s external-search
corroboration, the same reused verification client
:mod:`lineageweave.organization_name_resolution` already established
this pattern for.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from .http_client import chat_completion_content, post_json

LEVEL_GROUP = "group"
LEVEL_COMPANY = "company"
LEVEL_PLANT = "plant"
_VALID_LEVEL_CODES = frozenset({LEVEL_GROUP, LEVEL_COMPANY, LEVEL_PLANT})

@lru_cache(maxsize=1)
def required_corporate_level_codes() -> frozenset[str]:
    """Return the level codes every migrated database registers."""
    return _VALID_LEVEL_CODES


@dataclass(frozen=True)
class HierarchyProposal:
    """One organization's proposed place in the hierarchy.

    Attributes:
        level_code: ``corporate_entity_level`` lookup code -- one of
            ``group`` / ``company`` / ``plant``.
        parent_name: the immediate parent organization's name the text
            supports, or ``None`` when this organization has no parent
            in the hierarchy the text gives evidence for (a standalone
            group-level entity, or the text simply does not say).
    """

    level_code: str
    parent_name: str | None


class CorporateHierarchyInferenceClient(Protocol):
    """Proposes a hierarchy placement for a newly-seen organization name."""

    available: bool

    def infer(self, organization_name: str, context_text: str) -> HierarchyProposal | None:
        """Return a proposed placement, or ``None`` when the model
        cannot determine one from the given context with real
        confidence.

        Implementations must raise if the call itself fails -- a failed
        call is not the same outcome as "the model looked and proposed
        nothing." Protocol stubs raise ``NotImplementedError`` so a
        no-op body is never treated as a successful empty result.
        """
        raise NotImplementedError


class NullCorporateHierarchyInferenceClient:
    """No LLM orchestrator configured -- hierarchy inference is unavailable."""

    available = False

    def infer(self, organization_name: str, context_text: str) -> HierarchyProposal | None:
        """Infer a corporate hierarchy proposal from the supplied context."""
        raise RuntimeError(
            "NullCorporateHierarchyInferenceClient cannot infer; check .available first"
        )


_INFERENCE_PROMPT_TEMPLATE = """\
The text below names an organization, "{organization_name}", that is
not yet in our corporate hierarchy catalog. Using ONLY what the text
itself supports (never invent a hierarchy the text gives no evidence
for), determine:

1. Its level: exactly one of "group" (a top-level conglomerate/group
   with no parent), "company" (a company, possibly part of a group),
   or "plant" (a specific plant/site/branch/subsidiary of a company).
2. Its immediate parent organization's name, if the text names or
   clearly implies one (e.g. "Acme Electronics South Plant" implies its parent is
   "Acme Electronics"). Use null when the text gives no parent to infer, or
   when this organization is itself a top-level group.

Reply with ONLY a JSON object (no markdown fences, no prose):
  "level": exactly "group", "company", or "plant"
  "parent_name": string, or null

If you cannot determine even the level with real confidence from the
text, reply with exactly: UNKNOWN

Text: {context}
"""


def parse_inference_response(content: str) -> HierarchyProposal | None:
    """Parses the LLM's JSON reply into a `HierarchyProposal`.

    Returns `None` for `UNKNOWN`, malformed JSON, or a level outside the
    three valid codes -- a model that did not follow the contract gets
    treated as "no proposal," never a guessed default.
    """
    stripped = content.strip()
    if not stripped or stripped.upper() == "UNKNOWN":
        return None
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    level = parsed.get("level")
    if level not in _VALID_LEVEL_CODES:
        return None
    parent_raw = parsed.get("parent_name")
    parent_name = parent_raw.strip() if isinstance(parent_raw, str) and parent_raw.strip() else None
    return HierarchyProposal(level_code=level, parent_name=parent_name)


class ContextualOrchestratorHierarchyInferenceClient:
    """Calls ``POST {base_url}/v1/chat/completions`` with ``mode="auto"``."""

    available = True

    # 2026-08-22: same root cause as ContextualOrchestratorKeymanExtractionClient
    # and ContextualOrchestratorOrganizationNameResolutionClient -- mode="auto"
    # can route to deep multi-agent orchestration past 30s, and this call sits
    # in the same synchronous Keyman-extraction chain that reproduced a real
    # TimeoutError here.
    def __init__(
        self, base_url: str, api_key: str, *, reasoning_effort: str = "auto", timeout: float = 600.0
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._reasoning_effort = reasoning_effort
        self._timeout = timeout

    def infer(self, organization_name: str, context_text: str) -> HierarchyProposal | None:
        """Infer a corporate hierarchy proposal from the supplied context."""
        prompt = _INFERENCE_PROMPT_TEMPLATE.format(
            organization_name=organization_name, context=context_text
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
        return parse_inference_response(content)
