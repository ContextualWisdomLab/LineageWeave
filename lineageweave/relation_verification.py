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

import re
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import quote, urlparse

from .http_client import get_json

_SEARCH_HOST_MARKERS = (
    "google.",
    "bing.",
    "yahoo.",
    "duckduckgo.",
    "baidu.",
    "yandex.",
    "searx",
)
# Distinctive name tokens only. Latin legal suffixes ("Corp", "Ltd") and
# 1-syllable Hangul particles must not corroborate a random host that
# happens to contain them.
_ORG_TOKEN = re.compile(r"[A-Za-z]{4,}|[가-힣]{2,}")
_ORG_TOKEN_STOPWORDS = frozenset(
    {
        "corp",
        "ltd",
        "inc",
        "llc",
        "gmbh",
        "plc",
        "company",
        "group",
        "holdings",
        "limited",
        "foundation",
        "the",
        "and",
    }
)
_HANGUL_TOKEN = re.compile(r"[가-힣]+")
_KOREAN_PARTICLE_SUFFIX = re.compile(
    r"(?:에게서|한테서|에서는|으로는|이라고|에서|에게|한테|께서|부터|까지|처럼|보다|만큼|"
    r"으로|이랑|라고|이|가|은|는|을|를|의|에|께|와|과|도|만|로|랑|하고)+"
)

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
        """Reject verification because this client has no search transport."""
        raise RuntimeError(
            "NullRelationVerificationClient has no search channel; check .available first"
        )


class SearxngRelationVerificationClient:
    """Queries a self-hosted Searxng instance's JSON API for corroborating
    evidence of a claimed organization/relationship.

    The presence/absence signal is deliberately coarse: a result whose
    host or snippet contains every distinctive token in the organization
    name is treated as corroboration that the named organization has a
    real-world footprint consistent with the claim, not proof the specific
    relationship is true (a genuinely false relationship between two REAL
    organizations would still return results about each organization
    separately). Requiring every token prevents an unrelated page that
    happens to contain one common word from corroborating an invented name.
    This catches the failure mode actually observed from LLM
    classification -- an invented organization name with zero web
    footprint -- rather than claiming to adjudicate relationship truth from
    search snippets alone.
    """

    available = True

    def __init__(self, base_url: str, *, timeout: float = 15.0) -> None:
        """Configure a validated Searxng base URL and request timeout."""
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError(f"unsupported Searxng base URL scheme: {parsed.scheme or 'missing'}")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def verify(self, organization_name: str, relationship_label: str) -> RelationVerificationResult:
        """Return the first corroborating result, or an explicit negative result."""
        query = f"{organization_name} {relationship_label}"
        body = get_json(
            f"{self._base_url}/search?q={quote(query, safe='')}&format=json",
            timeout=self._timeout,
        )
        results = body.get("results")
        if not isinstance(results, list):
            return RelationVerificationResult(status_code=STATUS_UNCORROBORATED, evidence_url=None)
        for result in results:
            if not isinstance(result, dict):
                continue
            evidence_url = corroborating_evidence_url(organization_name, result)
            if evidence_url is not None:
                return RelationVerificationResult(status_code=STATUS_CORROBORATED, evidence_url=evidence_url)
        return RelationVerificationResult(status_code=STATUS_UNCORROBORATED, evidence_url=None)


def corroborating_evidence_url(organization_name: str, result: dict[str, Any]) -> str | None:
    """Return ``result['url']`` when it is a real-world footprint of ``organization_name``.

    Search engines echo the query in result titles, so "any hit" is not
    corroboration. A result counts only when every distinctive name token
    appears in the host or snippet, and the host is not itself a search
    page. The title is intentionally excluded because search engines echo
    the query there. Missing or empty URLs are not evidence.
    """
    url = result.get("url")
    if not isinstance(url, str) or not url.strip():
        return None
    host = urlparse(url).netloc.lower()
    if not host or any(marker in host for marker in _SEARCH_HOST_MARKERS):
        return None
    tokens = {
        token.lower()
        for token in _ORG_TOKEN.findall(organization_name)
        if token.lower() not in _ORG_TOKEN_STOPWORDS
    }
    if not tokens:
        return None
    haystack_tokens = {
        token.lower()
        for token in _ORG_TOKEN.findall(f"{host} {result.get('content') or ''}")
    }
    if all(
        any(_organization_token_matches(token, candidate) for candidate in haystack_tokens)
        for token in tokens
    ):
        return url
    return None


def _organization_token_matches(expected: str, observed: str) -> bool:
    """Match exact tokens, or a Hangul token followed only by Korean particles."""
    if expected == observed:
        return True
    if not _HANGUL_TOKEN.fullmatch(expected) or not observed.startswith(expected):
        return False
    return _KOREAN_PARTICLE_SUFFIX.fullmatch(observed[len(expected) :]) is not None
