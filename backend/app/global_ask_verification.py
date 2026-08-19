"""External corroboration for Global Ask claims without weakening source authority.

The primary Global Ask answer remains grounded only in authorized LineageWeave
posts. This module is an explicit open-world verification lane: when the caller
opts in, it sends the caller's question (never the private internal answer body)
to the configured self-hosted Searxng instance, then asks contextual-orchestrator
to classify the already-produced answer against only the retrieved public-web
evidence. External evidence never becomes a LineageWeave post or RBAC/ABAC
authority.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote, urlparse

from lineageweave.http_client import HttpClientError, get_json, post_json

MAX_EXTERNAL_RESULTS = 6
MAX_EXTERNAL_SNIPPET_CHARS = 2_000
MAX_EXTERNAL_QUERY_CHARS = 1_500
DEFAULT_VERIFICATION_TIMEOUT_SECONDS = 120.0

STATUS_NOT_REQUESTED = "not_requested"
STATUS_SUPPORTED = "supported"
STATUS_REFUTED = "refuted"
STATUS_INSUFFICIENT = "insufficient_evidence"
STATUS_UNAVAILABLE = "unavailable"
_ALLOWED_STATUSES = frozenset({STATUS_SUPPORTED, STATUS_REFUTED, STATUS_INSUFFICIENT})
_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


@dataclass(frozen=True)
class ExternalEvidence:
    """One bounded public-web result used only by the verification lane."""

    title: str
    url: str
    snippet: str


@dataclass(frozen=True)
class ExternalVerificationResult:
    """External-evidence judgment separated from the source-grounded answer."""

    status_code: str
    evidence_urls: tuple[str, ...] = ()
    rationale: str | None = None


class GlobalAskExternalVerifier(Protocol):
    """Classify an answer against independently retrieved external evidence."""

    available: bool

    def verify(self, question: str, answer_text: str) -> ExternalVerificationResult:
        """Return a bounded external-evidence judgment for ``answer_text``."""
        raise NotImplementedError


class NullGlobalAskExternalVerifier:
    """Explicitly unavailable external verification channel."""

    available = False

    def verify(self, question: str, answer_text: str) -> ExternalVerificationResult:
        """Return unavailable without fabricating evidence."""
        return ExternalVerificationResult(status_code=STATUS_UNAVAILABLE)


def _safe_external_url(raw_url: object) -> str | None:
    """Accept only ordinary HTTP(S) evidence URLs with a network host."""
    if not isinstance(raw_url, str):
        return None
    candidate = raw_url.strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return candidate


def _bounded_search_query(question: str) -> str:
    """Build a deterministic bounded public-search query from caller text only."""
    return " ".join(question.split())[:MAX_EXTERNAL_QUERY_CHARS]


def _parse_search_results(payload: object) -> list[ExternalEvidence]:
    """Convert Searxng JSON into bounded, safe external evidence records."""
    if not isinstance(payload, dict):
        return []
    raw_results = payload.get("results")
    if not isinstance(raw_results, list):
        return []
    evidence: list[ExternalEvidence] = []
    seen_urls: set[str] = set()
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        url = _safe_external_url(item.get("url"))
        if url is None or url in seen_urls:
            continue
        seen_urls.add(url)
        title = item.get("title") if isinstance(item.get("title"), str) else "External evidence"
        snippet = item.get("content") if isinstance(item.get("content"), str) else ""
        evidence.append(
            ExternalEvidence(
                title=title.strip()[:300] or "External evidence",
                url=url,
                snippet=snippet.strip()[:MAX_EXTERNAL_SNIPPET_CHARS],
            )
        )
        if len(evidence) == MAX_EXTERNAL_RESULTS:
            break
    return evidence


def _parse_judgment(content: object) -> dict[str, object] | None:
    """Parse strict JSON, tolerating only an optional outer Markdown JSON fence."""
    if not isinstance(content, str):
        return None
    match = _JSON_FENCE.search(content)
    candidate = match.group(1) if match else content
    try:
        parsed = json.loads(candidate.strip())
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


_VERIFICATION_PROMPT = """\
You are verifying an already-produced product answer against ONLY the external
web evidence below. Do not use memory or outside knowledge. Classify the answer
as exactly one of: supported, refuted, insufficient_evidence.

Use supported only when the retrieved evidence materially supports the answer's
important factual claims. Use refuted only when the retrieved evidence directly
contradicts an important factual claim. Otherwise use insufficient_evidence.

Return ONLY JSON with exactly these fields:
  "status_code": "supported" | "refuted" | "insufficient_evidence"
  "cited_evidence_numbers": array of 1-based integers
  "rationale": string, concise and specific to the retrieved evidence

Question: {question}
Answer being checked: {answer_text}

External evidence:
{evidence_block}
"""


class SearxngOrchestratorGlobalAskVerifier:
    """Retrieve through Searxng and judge only against retrieved web evidence."""

    available = True

    def __init__(
        self,
        searxng_base_url: str,
        orchestrator_base_url: str,
        orchestrator_api_key: str,
        *,
        search_timeout: float = 15.0,
        verification_timeout: float = DEFAULT_VERIFICATION_TIMEOUT_SECONDS,
    ) -> None:
        searx = urlparse(searxng_base_url)
        orchestrator = urlparse(orchestrator_base_url)
        if searx.scheme not in {"http", "https"} or not searx.netloc:
            raise ValueError("Searxng base URL must be HTTP(S)")
        if orchestrator.scheme not in {"http", "https"} or not orchestrator.netloc:
            raise ValueError("contextual-orchestrator base URL must be HTTP(S)")
        if not orchestrator_api_key:
            raise ValueError("contextual-orchestrator API key is required")
        self._searxng_base_url = searxng_base_url.rstrip("/")
        self._orchestrator_base_url = orchestrator_base_url.rstrip("/")
        self._orchestrator_api_key = orchestrator_api_key
        self._search_timeout = search_timeout
        self._verification_timeout = verification_timeout

    def verify(self, question: str, answer_text: str) -> ExternalVerificationResult:
        """Return supported/refuted/insufficient from bounded external evidence."""
        query = _bounded_search_query(question)
        if not query:
            return ExternalVerificationResult(status_code=STATUS_INSUFFICIENT)
        try:
            payload = get_json(
                f"{self._searxng_base_url}/search?q={quote(query, safe='')}&format=json",
                timeout=self._search_timeout,
            )
        except (HttpClientError, OSError, ValueError):
            return ExternalVerificationResult(status_code=STATUS_UNAVAILABLE)
        evidence = _parse_search_results(payload)
        if not evidence:
            return ExternalVerificationResult(status_code=STATUS_INSUFFICIENT)
        evidence_block = "\n\n".join(
            f"[Evidence {index}]\nTitle: {item.title}\nURL: {item.url}\nSnippet: {item.snippet}"
            for index, item in enumerate(evidence, start=1)
        )
        prompt = _VERIFICATION_PROMPT.format(
            question=question,
            answer_text=answer_text,
            evidence_block=evidence_block,
        )
        try:
            body = post_json(
                f"{self._orchestrator_base_url}/v1/chat/completions",
                {
                    "messages": [{"role": "user", "content": prompt}],
                    "mode": "conduct",
                    "reasoning_effort": "high",
                },
                headers={"authorization": f"Bearer {self._orchestrator_api_key}"},
                timeout=self._verification_timeout,
            )
            parsed = _parse_judgment(body["choices"][0]["message"]["content"])
        except (HttpClientError, KeyError, OSError, TypeError, ValueError):
            return ExternalVerificationResult(status_code=STATUS_UNAVAILABLE)
        if parsed is None or parsed.get("status_code") not in _ALLOWED_STATUSES:
            return ExternalVerificationResult(status_code=STATUS_UNAVAILABLE)
        raw_numbers = parsed.get("cited_evidence_numbers")
        numbers = raw_numbers if isinstance(raw_numbers, list) else []
        cited_urls = tuple(
            dict.fromkeys(
                evidence[number - 1].url
                for number in numbers
                if isinstance(number, int) and 1 <= number <= len(evidence)
            )
        )
        rationale = parsed.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            rationale = None
        return ExternalVerificationResult(
            status_code=str(parsed["status_code"]),
            evidence_urls=cited_urls,
            rationale=rationale.strip()[:2_000] if rationale else None,
        )
