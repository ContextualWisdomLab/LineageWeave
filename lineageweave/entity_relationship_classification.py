"""Pluggable entity-relationship classification: for each organization
named in a post's text, what is that organization's relationship to the
post author's own organization -- partner, competitor, customer,
customer's-customer, market, or supplier?

Grounded in relation extraction from text (Zelenko, Aone, & Richardella,
2003): classifying the semantic relation between a document's subject and
a named entity mentioned in it, rather than treating the entity as an
undifferentiated string. This maps onto the product's own six-way
vocabulary -- ``rel_voc``/``rel_vom``/``rel_vop``/``rel_vocc``/``rel_voco``/
``rel_vos`` (``rel_`` prefixed: ``common_lookup_value.lookup_code`` is
unique GLOBALLY across categories, and bare ``voc``/``vom`` are already
claimed by ``source_post.voc_type_code``'s own category) -- which in practice
collapses to "customer" and "competitor" most of the time; ``rel_vos``
(supplier) is the unusual case that still needs to classify correctly
because it is rare, not because it never happens.

Same pluggable-client, never-fake-a-missing-channel discipline as
``keyman_extraction``: :class:`NullEntityRelationshipClient` makes the
channel unavailable, never guesses a relationship type.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol

from .http_client import chat_completion_content, post_json

# post_counterparty_entity.relationship_type_code values (common_lookup_value,
# category "entity_relationship_type"). VOC/VOM/VOP/VOCC/VOCO are the
# vocabulary the org already has but rarely applies consistently; VOS is
# the "edge case some situations present" the product brief calls out.
# Prefixed "rel_" because common_lookup_value.lookup_code is unique GLOBALLY
# across every category (documented in migrations/0001_initial_schema.sql),
# and bare "voc"/"vom" are already claimed by source_post.voc_type_code's own
# "voc_type" category -- a post's own type and a specific counterparty's
# relationship type are different columns that happen to draw on the same
# VOC/VOM-style abbreviations, so they need distinct literal codes.
VOC = "rel_voc"  # Voice of Customer -- this org buys from the post author's org
VOM = "rel_vom"  # Voice of Market -- a general market signal, no single counterparty
VOP = "rel_vop"  # Voice of Partner
VOCC = "rel_vocc"  # Voice of Customer's Customer -- one hop further down the chain
VOCO = "rel_voco"  # Voice of Competitor
VOS = "rel_vos"  # Voice of Supplier -- the uncommon edge case
_VALID_RELATIONSHIP_CODES = frozenset({VOC, VOM, VOP, VOCC, VOCO, VOS})


@dataclass(frozen=True)
class OrganizationRelationship:
    """One organization's classified relationship to the post author's org."""

    organization_name: str
    relationship_type_code: str


class EntityRelationshipClient(Protocol):
    """Classifies each named organization's relationship to the post author."""

    available: bool

    def classify(
        self, post_title: str, post_body: str, organization_names: list[str]
    ) -> list[OrganizationRelationship]:
        """Return one relationship code per named organization.

        Implementations must raise if they cannot classify. Protocol stubs
        raise ``NotImplementedError`` so a no-op body is never treated as
        a successful empty result (a missing signal is not zero relations).
        """
        raise NotImplementedError


class NullEntityRelationshipClient:
    """No LLM orchestrator configured -- relationship classification is unavailable."""

    available = False

    def classify(
        self, post_title: str, post_body: str, organization_names: list[str]
    ) -> list[OrganizationRelationship]:
        """Classify the relationship expressed by the supplied context."""
        raise RuntimeError(
            "NullEntityRelationshipClient cannot classify; check .available first"
        )


_CLASSIFICATION_PROMPT_TEMPLATE = """\
Read the post below. For each organization named in the list, classify its
relationship to the post author's own organization using EXACTLY one of
these codes:
  rel_voc  = this organization is a customer buying from the post author's org
  rel_vom  = the mention is a general market signal, not a specific counterparty
  rel_vop  = this organization is a partner
  rel_vocc = this organization is a customer OF one of the post author's own
             customers (one hop further down the chain), not a direct customer
  rel_voco = this organization is a competitor
  rel_vos  = this organization is a supplier to the post author's org

An organization can genuinely be more than one of these across different
parts of its business (e.g. a current customer that also competes with the
post author in a different product line) -- pick whichever relationship
the text actually describes for THIS post, not a general assumption about
the organization.

Reply with ONLY a JSON array (no markdown fences, no prose), where each
element has exactly these fields:
  "organization_name": exactly one of the names from the list below
  "relationship_type_code": one of rel_voc, rel_vom, rel_vop, rel_vocc, rel_voco, rel_vos

Organizations to classify: {organization_names}

Post title: {title}
Post body: {body}
"""

_CODE_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _strip_code_fence(content: str) -> str:
    """Implement the _strip_code_fence operation for this channel."""
    match = _CODE_FENCE_PATTERN.search(content)
    return match.group(1) if match else content


def parse_classification_response(
    content: str, organization_names: list[str]
) -> list[OrganizationRelationship]:
    """Parses the LLM's JSON array response into `OrganizationRelationship`s.

    An entry naming an organization not in `organization_names`, or with a
    `relationship_type_code` outside the six valid codes, is skipped rather
    than guessed at -- same discipline as `keyman_extraction.parse_keyman_response`:
    a wrong classification corrupts downstream Knowledge Graph edges, so a
    dropped entry is safer than an invented one.
    """
    try:
        parsed = json.loads(_strip_code_fence(content).strip())
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []

    valid_names = set(organization_names)
    results: list[OrganizationRelationship] = []
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        name = entry.get("organization_name")
        code = entry.get("relationship_type_code")
        if not isinstance(name, str) or name not in valid_names:
            continue
        if code not in _VALID_RELATIONSHIP_CODES:
            continue
        results.append(OrganizationRelationship(organization_name=name, relationship_type_code=code))
    return results


class ContextualOrchestratorEntityRelationshipClient:
    """Calls ``POST {base_url}/v1/chat/completions`` with ``mode="auto"``."""

    available = True

    def __init__(
        self, base_url: str, api_key: str, *, reasoning_effort: str = "auto", timeout: float = 180.0
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._reasoning_effort = reasoning_effort
        self._timeout = timeout

    def classify(
        self, post_title: str, post_body: str, organization_names: list[str]
    ) -> list[OrganizationRelationship]:
        """Classify the relationship expressed by the supplied context."""
        if not organization_names:
            return []
        prompt = _CLASSIFICATION_PROMPT_TEMPLATE.format(
            organization_names=json.dumps(organization_names, ensure_ascii=False),
            title=post_title,
            body=post_body,
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
        return parse_classification_response(content, organization_names)
