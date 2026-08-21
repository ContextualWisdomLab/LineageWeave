"""Verify LLM-inferred relations against external search evidence.

This module implements the retrieval-and-presence subset of FEVER-style claim
verification (Thorne, Vlachos, Christodoulopoulos, & Mittal, 2018). It catches
invented organization names without claiming that a search hit proves the
specific relationship. Missing search transport remains unavailable rather
than becoming a fabricated negative result.
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
# Distinctive name tokens only. Legal suffixes, fixture descriptors, and
# one-syllable Hangul particles cannot corroborate a random search result.
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
        "fictitious",
        "nonexistent",
        "placeholder",
        "sample",
        "example",
        "demo",
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
    """One claim's verification outcome and its optional evidence URL."""

    status_code: str
    evidence_url: str | None


class RelationVerificationClient(Protocol):
    """Check a claimed organization/relationship against external search."""

    available: bool

    def verify(
        self, organization_name: str, relationship_label: str
    ) -> RelationVerificationResult:
        """Return search evidence or raise when the search itself fails.

        A failed search is not the same claim as "searched and found nothing"
        and must not be recorded as :data:`STATUS_UNCORROBORATED`.
        """
        raise NotImplementedError


class NullRelationVerificationClient:
    """No search provider configured; the verification channel is skipped."""

    available = False

    def verify(
        self, organization_name: str, relationship_label: str
    ) -> RelationVerificationResult:  # pragma: no cover
        """Reject verification because this client has no search transport."""
        raise RuntimeError(
            "NullRelationVerificationClient has no search channel; check .available first"
        )


class SearxngRelationVerificationClient:
    """Query a self-hosted Searxng JSON API for corroborating evidence."""

    available = True

    def __init__(self, base_url: str, *, timeout: float = 15.0) -> None:
        """Configure a validated Searxng base URL and request timeout."""
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError(
                f"unsupported Searxng base URL scheme: {parsed.scheme or 'missing'}"
            )
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def verify(
        self, organization_name: str, relationship_label: str
    ) -> RelationVerificationResult:
        """Return the first corroborating result or an explicit negative."""
        query = f"{organization_name} {relationship_label}"
        body = get_json(
            f"{self._base_url}/search?q={quote(query, safe='')}&format=json",
            timeout=self._timeout,
        )
        results = body.get("results")
        if not isinstance(results, list):
            return RelationVerificationResult(
                status_code=STATUS_UNCORROBORATED, evidence_url=None
            )
        for result in results:
            if not isinstance(result, dict):
                continue
            evidence_url = corroborating_evidence_url(organization_name, result)
            if evidence_url is not None:
                return RelationVerificationResult(
                    status_code=STATUS_CORROBORATED, evidence_url=evidence_url
                )
        return RelationVerificationResult(
            status_code=STATUS_UNCORROBORATED, evidence_url=None
        )


def corroborating_evidence_url(
    organization_name: str, result: dict[str, Any]
) -> str | None:
    """Return a safe result URL when all distinctive name tokens are present.

    Search engines echo query text in titles, so only the result host and
    snippet are considered. A result must contain every distinctive token;
    missing, search-host, non-HTTP, and title-only URLs are not evidence.
    """
    url = result.get("url")
    if not isinstance(url, str) or not url.strip():
        return None
    try:
        parsed_url = urlparse(url)
        host = (parsed_url.hostname or "").lower()
    except ValueError:
        return None
    if parsed_url.scheme not in {"http", "https"}:
        return None
    if not host or any(marker in host for marker in _SEARCH_HOST_MARKERS):
        return None
    organization_tokens = [
        token.lower() for token in _ORG_TOKEN.findall(organization_name)
    ]
    tokens = {
        token for token in organization_tokens if token not in _ORG_TOKEN_STOPWORDS
    }
    if not tokens:
        return None
    haystack_tokens = {
        token.lower()
        for token in _ORG_TOKEN.findall(f"{host} {result.get('content') or ''}")
    }
    if all(
        any(
            _organization_token_matches(token, candidate)
            for candidate in haystack_tokens
        )
        for token in tokens
    ) or _concatenated_hangul_name_matches(organization_tokens, haystack_tokens):
        return url
    return None


def _concatenated_hangul_name_matches(
    expected_tokens: list[str], observed_tokens: set[str]
) -> bool:
    """Accept a spaced Hangul name when a page writes its parts contiguously."""
    if len(expected_tokens) < 2 or not all(
        _HANGUL_TOKEN.fullmatch(token) for token in expected_tokens
    ):
        return False
    compact_name = "".join(expected_tokens)
    return any(
        _organization_token_matches(compact_name, observed)
        for observed in observed_tokens
    )


def _organization_token_matches(expected: str, observed: str) -> bool:
    """Match exact tokens or a Hangul token followed only by particles."""
    if expected == observed:
        return True
    if not _HANGUL_TOKEN.fullmatch(expected) or not observed.startswith(expected):
        return False
    return _KOREAN_PARTICLE_SUFFIX.fullmatch(observed[len(expected) :]) is not None
