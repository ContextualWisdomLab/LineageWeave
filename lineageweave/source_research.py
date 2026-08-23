"""Research explicit URL and patent leads without promoting search hits to facts.

ADR 0133 keeps discovery, retrieval, crawling, and contextual-orchestrator
judgment as separate evidence channels.  This module has no provider-specific
model choice and no local confidence heuristic.
"""

from __future__ import annotations

import ipaddress
import json
import re
import socket
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Protocol
from urllib.parse import quote, urlparse

from .http_client import (
    HttpClientError,
    _request,
    chat_completion_content,
    get_json,
    post_json,
)

_URL = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_PATENT = re.compile(r"(?:특허|patent|pat\.)", re.IGNORECASE)
_MAX_QUERY_CHARS = 300
_MAX_PAGE_BYTES = 1_000_000
_MAX_PASSAGE_CHARS = 4_000
_MAX_RESULTS = 5
_JUDGMENT_STATUSES = frozenset({"supported", "refuted", "not_enough_information"})


@dataclass(frozen=True)
class ResearchLead:
    """One source-grounded reference that may warrant external research."""

    lead_type_code: str
    query_text: str
    evidence_text: str
    source_content_unit_id: str | None = None
    source_image_region_id: str | None = None


@dataclass(frozen=True)
class RetrievedPassage:
    """Bounded text crawled from one public search result."""

    url: str
    title: str
    text: str


@dataclass(frozen=True)
class ResearchJudgment:
    """Judge outcome; an actor is absent unless cited evidence names it."""

    status_code: str
    sharing_actor_name: str | None
    rationale: str
    cited_urls: tuple[str, ...]


class SourceResearchJudge(Protocol):
    """Adjudicates a lead against retrieved passages."""

    available: bool

    def judge(
        self, lead: ResearchLead, passages: list[RetrievedPassage]
    ) -> ResearchJudgment:
        """Return a supported, refuted, or insufficient-evidence judgment."""
        raise NotImplementedError  # pragma: no cover - protocol declaration


class NullSourceResearchJudge:
    """No contextual-orchestrator channel is configured."""

    available = False

    def judge(
        self, lead: ResearchLead, passages: list[RetrievedPassage]
    ) -> ResearchJudgment:
        """Refuse to fabricate a research judgment."""
        raise RuntimeError(
            "NullSourceResearchJudge cannot judge; check .available first"
        )


def discover_research_leads(
    unit_texts: list[str | tuple[str, str | None, str | None]],
) -> tuple[ResearchLead, ...]:
    """Find explicit URLs and patent-bearing units, preserving source text."""
    leads: list[ResearchLead] = []
    seen: set[tuple[str, str, str | None, str | None]] = set()
    normalized_sources: list[tuple[str, str | None, str | None]] = []
    for source in unit_texts:
        if isinstance(source, str):
            raw_text, content_unit_id, image_region_id = source, None, None
        else:
            raw_text, content_unit_id, image_region_id = source
        normalized_sources.append(
            (" ".join(raw_text.split()), content_unit_id, image_region_id)
        )
    for source_index, (text, content_unit_id, image_region_id) in enumerate(
        normalized_sources
    ):
        if not text:
            continue
        for match in _URL.finditer(text):
            url = match.group(0).rstrip(".,);]")
            key = ("source_reference_url", url, content_unit_id, image_region_id)
            if key not in seen:
                seen.add(key)
                leads.append(
                    ResearchLead(
                        key[0],
                        url,
                        text[:_MAX_QUERY_CHARS],
                        content_unit_id,
                        image_region_id,
                    )
                )
        if _PATENT.search(text):
            query = " ".join(
                candidate_text
                for candidate_text, _unit_id, _region_id in normalized_sources[
                    max(0, source_index - 1) : min(
                        len(normalized_sources), source_index + 2
                    )
                ]
                if candidate_text
            )[:_MAX_QUERY_CHARS]
            key = (
                "source_reference_patent",
                query.casefold(),
                content_unit_id,
                image_region_id,
            )
            if key not in seen:
                seen.add(key)
                leads.append(
                    ResearchLead(key[0], query, text, content_unit_id, image_region_id)
                )
    return tuple(leads)


def _public_host(hostname: str) -> bool:
    """Resolve a crawl target and reject loopback/private/link-local addresses."""
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(hostname, None)}
    except socket.gaierror:
        return False
    if not addresses:
        return False
    return all(ipaddress.ip_address(address).is_global for address in addresses)


class _VisibleTextParser(HTMLParser):
    """Small stdlib HTML-to-visible-text projection for bounded pages."""

    def __init__(self) -> None:
        super().__init__()
        self._hidden = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Suppress text inside non-visible HTML elements."""
        if tag in {"script", "style", "noscript", "svg"}:
            self._hidden += 1

    def handle_endtag(self, tag: str) -> None:
        """Resume visible-text collection after a hidden element closes."""
        if tag in {"script", "style", "noscript", "svg"} and self._hidden:
            self._hidden -= 1

    def handle_data(self, data: str) -> None:
        """Collect nonblank text when the parser is outside hidden elements."""
        if not self._hidden and data.strip():
            self.parts.append(data.strip())


def crawl_public_page(url: str, *, timeout: float = 15.0) -> str:
    """Fetch bounded public HTML/text while rejecting SSRF and redirect escapes."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("research crawl requires an http(s) URL with a host")
    if not _public_host(parsed.hostname):
        raise ValueError("research crawl refuses a non-public network target")
    status, raw = _request(
        "GET",
        url,
        body=None,
        headers={
            "accept": "text/html,text/plain;q=0.9",
            "user-agent": "LineageWeaveResearch/1",
        },
        timeout=timeout,
        require_public_peer=True,
        max_response_bytes=_MAX_PAGE_BYTES,
    )
    if status in {301, 302, 303, 307, 308}:
        # Search results should provide canonical final URLs. Redirects remain
        # unavailable because the compact client does not expose Location.
        raise HttpClientError("research crawl redirect requires a canonical result URL")
    if status >= 400:
        raise HttpClientError(f"HTTP {status} from {parsed.hostname}")
    decoded = raw.decode("utf-8", errors="replace")
    parser = _VisibleTextParser()
    parser.feed(decoded)
    return " ".join(" ".join(parser.parts).split())[:_MAX_PASSAGE_CHARS]


class SearxngSourceResearchClient:
    """Search SearXNG, crawl public results, then return bounded passages."""

    available = True

    def __init__(self, base_url: str, *, timeout: float = 15.0) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("SearXNG research URL must be http(s)")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def retrieve(self, lead: ResearchLead) -> list[RetrievedPassage]:
        """Return crawlable public passages; failed candidates remain dropped."""
        query = lead.query_text
        body = get_json(
            # The long-running anonymous general pool is routinely suspended
            # by CAPTCHA/rate limits. The bundled Bing adapter is selected
            # explicitly while remaining a SearXNG-owned transport.
            f"{self._base_url}/search?q={quote(query, safe='')}&format=json&engines=bing",
            timeout=self._timeout,
        )
        results = body.get("results")
        if not isinstance(results, list):
            return []
        passages: list[RetrievedPassage] = []
        for result in results[:_MAX_RESULTS]:
            if not isinstance(result, dict):
                continue
            url = result.get("url")
            if not isinstance(url, str):
                continue
            parsed_url = urlparse(url)
            if (
                parsed_url.scheme not in {"http", "https"}
                or not parsed_url.hostname
                or not _public_host(parsed_url.hostname)
            ):
                continue
            try:
                text = crawl_public_page(url, timeout=self._timeout)
            except ValueError:
                continue
            except (HttpClientError, OSError):
                text = " ".join(str(result.get("content") or "").split())[
                    :_MAX_PASSAGE_CHARS
                ]
            if text:
                passages.append(
                    RetrievedPassage(
                        url=url, title=str(result.get("title") or ""), text=text
                    )
                )
        return passages


_JUDGE_PROMPT = """\
Judge the source lead using ONLY the retrieved passages. Return one JSON object
with status_code (supported, refuted, or not_enough_information),
sharing_actor_name (an explicitly named publisher/sharer or null), rationale,
and cited_urls. A URL existing is not proof of the claim. Do not infer an actor
from an address, domain suffix, or nearby name. Every cited URL must be one of
the supplied passages.

Lead: {lead}
Source evidence: {evidence}
Passages: {passages}
"""


class ContextualOrchestratorSourceResearchJudge:
    """Adjudicate research evidence through contextual-orchestrator."""

    available = True

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 900.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    def judge(
        self, lead: ResearchLead, passages: list[RetrievedPassage]
    ) -> ResearchJudgment:
        """Return a strictly validated evidence judgment."""
        body = post_json(
            f"{self._base_url}/v1/chat/completions",
            {
                "messages": [
                    {
                        "role": "user",
                        "content": _JUDGE_PROMPT.format(
                            lead=lead.query_text,
                            evidence=lead.evidence_text,
                            passages=json.dumps(
                                [passage.__dict__ for passage in passages],
                                ensure_ascii=False,
                            ),
                        ),
                    }
                ],
                "mode": "auto",
                "reasoning_effort": "auto",
                "response_format": {"type": "json_object"},
            },
            headers={"authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
        )
        try:
            parsed = json.loads(chat_completion_content(body))
        except json.JSONDecodeError as exc:
            raise ValueError("research judge returned invalid JSON") from exc
        status_code = parsed.get("status_code")
        actor = parsed.get("sharing_actor_name")
        rationale = parsed.get("rationale")
        cited_urls = parsed.get("cited_urls")
        allowed_urls = {passage.url for passage in passages}
        if status_code not in _JUDGMENT_STATUSES or not isinstance(rationale, str):
            raise ValueError("research judge returned an invalid judgment")
        if actor is not None and not isinstance(actor, str):
            raise ValueError("research judge returned an invalid actor")
        if not isinstance(cited_urls, list) or any(
            url not in allowed_urls for url in cited_urls
        ):
            raise ValueError("research judge cited evidence outside the retrieved set")
        if status_code != "not_enough_information" and not cited_urls:
            raise ValueError("research judge returned a finding without a citation")
        if actor and status_code != "supported":
            raise ValueError("research judge named an actor without supported evidence")
        if actor and not any(
            actor.casefold() in f"{passage.title} {passage.text}".casefold()
            for passage in passages
            if passage.url in cited_urls
        ):
            raise ValueError("research judge named an actor absent from cited evidence")
        return ResearchJudgment(
            status_code, actor, rationale, tuple(dict.fromkeys(cited_urls))
        )
