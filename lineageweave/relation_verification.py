"""Verifies whether an LLM-inferred Ontology relation has any real-world
corroborating evidence, via an external web search -- catching the case
where :mod:`lineageweave.entity_relationship_classification` (or any other
LLM-driven relation inference over the Knowledge Graph) names an
organization or relationship that does not actually exist, rather than
letting a hallucinated node/edge sit in the graph indistinguishable from a
verified one.

Grounded in FEVER-style open-domain claim verification (Thorne, Vlachos,
Christodoulopoulos, & Mittal, 2018): retrieve external evidence for a
claim, then classify the claim as supported, refuted, or not-enough-info
against what was retrieved. This module implements the practical subset
that fits a same-request check -- retrieval plus a presence/absence
signal (:data:`STATUS_CORROBORATED` / :data:`STATUS_UNCORROBORATED`) --
not full NLI-based entailment scoring against the retrieved passages;
that upgrade is a real one once real usage shows the presence/absence
signal under- or over-trusting results in practice, not implemented here
because nothing yet demonstrates the need for it over this cheaper stage.

Same pluggable-client, never-fake-a-missing-channel discipline as every
other channel in this package: :class:`NullRelationVerificationClient`
makes the channel unavailable, never fabricates a verification result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote, urlparse

from .http_client import get_json

STATUS_PENDING = "verify_pending"
STATUS_CORROBORATED = "verify_corroborated"
STATUS_UNCORROBORATED = "verify_uncorroborated"


@dataclass(frozen=True)
class RelationVerificationResult:
    """One claim's verification outcome.

    Attributes:
        status_code: one of ``STATUS_CORROBORATED`` / ``STATUS_UNCORROBORATED``
            -- ``common_lookup_value.lookup_code`` for category
            ``relation_verification_status``.
        evidence_url: the first corroborating search result's URL, or
            ``None`` when uncorroborated (there is nothing to cite).
    """

    status_code: str
    evidence_url: str | None


class RelationVerificationClient(Protocol):
    """Checks a claimed organization/relationship against external search."""

    available: bool

    def verify(self, organization_name: str, relationship_label: str) -> RelationVerificationResult:
        """Search for corroborating evidence of ``organization_name``
        having the relationship ``relationship_label`` describes.

        Implementations must raise if the search itself fails (network
        error, non-JSON response) -- a failed search is not the same
        claim as "searched and found nothing," and must not be recorded
        as ``STATUS_UNCORROBORATED``. Protocol stubs raise
        ``NotImplementedError`` so a no-op body is never treated as a
        successful result.
        """
        raise NotImplementedError


class NullRelationVerificationClient:
    """No search provider configured -- the verification channel is skipped."""

    available = False

    def verify(self, organization_name: str, relationship_label: str) -> RelationVerificationResult:  # pragma: no cover
        raise RuntimeError(
            "NullRelationVerificationClient has no search channel; check .available first"
        )


class SearxngRelationVerificationClient:
    """Queries a self-hosted Searxng instance's JSON API for corroborating
    evidence of a claimed organization/relationship.

    The presence/absence signal is deliberately coarse: any search result
    for "``<organization_name>`` ``<relationship_label>``" is treated as
    corroboration that the named organization has a real-world footprint
    consistent with the claim, not proof the specific relationship is
    true (a genuinely false relationship between two REAL organizations
    would still return results about each organization separately). This
    catches the failure mode actually observed from LLM classification --
    an invented organization name with zero web footprint -- rather than
    claiming to adjudicate relationship truth from search snippets alone.
    """

    available = True

    def __init__(self, base_url: str, *, timeout: float = 15.0) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError(f"unsupported Searxng base URL scheme: {parsed.scheme or 'missing'}")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def verify(self, organization_name: str, relationship_label: str) -> RelationVerificationResult:
        query = f"{organization_name} {relationship_label}"
        body = get_json(
            f"{self._base_url}/search?q={quote(query, safe='')}&format=json",
            timeout=self._timeout,
        )
        results = body.get("results")
        if not isinstance(results, list) or not results:
            return RelationVerificationResult(status_code=STATUS_UNCORROBORATED, evidence_url=None)
        first = results[0]
        evidence_url = first.get("url") if isinstance(first, dict) else None
        return RelationVerificationResult(status_code=STATUS_CORROBORATED, evidence_url=evidence_url)
