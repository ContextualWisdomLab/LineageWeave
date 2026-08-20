"""Tests for lineageweave.relation_verification.

SearxngRelationVerificationClient's tests run against a real local HTTP
server (same pattern as tests/test_http_client.py), not a mocked
transport -- proving the actual URL construction and response-shape
handling, not just that a mock was called correctly. A real Searxng
instance is exercised separately, gated behind docker compose (this
repo's discipline: never fake a channel it can instead genuinely run).
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

from lineageweave.relation_verification import (
    STATUS_CORROBORATED,
    STATUS_UNCORROBORATED,
    NullRelationVerificationClient,
    SearxngRelationVerificationClient,
    corroborating_evidence_url,
)


class _ResultsHandler(BaseHTTPRequestHandler):
    received_query: str = ""

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        type(self).received_query = query.get("q", [""])[0]
        if "Acme" in type(self).received_query:
            payload = {
                "query": type(self).received_query,
                "results": [
                    {
                        "url": "https://acme.example.com/about",
                        "title": "Acme Corp",
                        "content": "Acme manufactures industrial transformers.",
                    }
                ],
            }
        else:
            payload = {"query": type(self).received_query, "results": []}
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A002 -- stdlib signature
        return


def _serve() -> tuple[HTTPServer, str]:
    server = HTTPServer(("127.0.0.1", 0), _ResultsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    return server, f"http://{host}:{port}"


def test_null_client_is_unavailable_not_silently_uncorroborated() -> None:
    """A missing search channel is unavailable, not a negative finding."""
    client = NullRelationVerificationClient()
    assert client.available is False
    with pytest.raises(RuntimeError):
        client.verify("Acme Corp", "Voice of Customer")


def test_searxng_client_reports_corroborated_with_evidence_url() -> None:
    """A matching result returns corroboration and its evidence URL."""
    server, base = _serve()
    try:
        client = SearxngRelationVerificationClient(base_url=base)
        result = client.verify("Acme Corp", "Voice of Customer")
    finally:
        server.shutdown()

    assert result.status_code == STATUS_CORROBORATED
    assert result.evidence_url == "https://acme.example.com/about"
    assert "Acme Corp" in _ResultsHandler.received_query
    assert "Voice of Customer" in _ResultsHandler.received_query


def test_searxng_client_reports_uncorroborated_with_no_evidence_url_when_search_is_empty() -> None:
    """An empty result set remains explicitly uncorroborated."""
    server, base = _serve()
    try:
        client = SearxngRelationVerificationClient(base_url=base)
        result = client.verify("Totally Fictitious Nonexistent Org", "Voice of Customer")
    finally:
        server.shutdown()

    assert result.status_code == STATUS_UNCORROBORATED
    assert result.evidence_url is None


def test_query_echo_on_a_search_host_is_not_corroboration() -> None:
    """A search-result URL and echoed title cannot become evidence."""
    assert (
        corroborating_evidence_url(
            "Zzqxvthorp Fictitious Nonexistent Org",
            {
                "url": "https://www.google.com/search?q=Zzqxvthorp",
                "title": "Zzqxvthorp Fictitious Nonexistent Org - Google Search",
                "content": "",
            },
        )
        is None
    )


def test_org_token_in_result_host_is_corroboration() -> None:
    """A distinctive organization token in the host is evidence."""
    assert (
        corroborating_evidence_url(
            "Acme Corp",
            {"url": "https://www.acme.example/news", "title": "News", "content": ""},
        )
        == "https://www.acme.example/news"
    )


def test_partial_multi_token_name_is_not_corroboration() -> None:
    """One generic token must not validate an invented multi-token name."""
    assert (
        corroborating_evidence_url(
            "Fictitious Nonexistent Org",
            {
                "url": "https://microsoft.example/news",
                "title": "Fictitious names, domains, and addresses",
                "content": "This page discusses fictitious names.",
            },
        )
        is None
    )


def test_all_distinctive_multi_token_name_parts_are_corroboration() -> None:
    """All distinctive name tokens may be distributed across host and content."""
    assert (
        corroborating_evidence_url(
            "Aurora Grid Power",
            {
                "url": "https://aurora-grid.example/news",
                "title": "Aurora Grid Power",
                "content": "Aurora Grid Power announced a delivery window.",
            },
        )
        == "https://aurora-grid.example/news"
    )


def test_title_only_full_name_is_not_corroboration() -> None:
    """A title echo alone is not an organization footprint."""
    assert (
        corroborating_evidence_url(
            "Aurora Grid Power",
            {
                "url": "https://news.example/item",
                "title": "Aurora Grid Power",
                "content": "",
            },
        )
        is None
    )


def test_compound_host_token_is_not_two_name_tokens() -> None:
    """A compound host word must not match separate organization tokens."""
    assert (
        corroborating_evidence_url(
            "Green House",
            {"url": "https://greenhouse.example/news", "title": "News", "content": ""},
        )
        is None
    )


def test_legal_suffix_alone_is_not_corroboration() -> None:
    """'Corp' is in almost every corporate host; it is not evidence."""
    assert (
        corroborating_evidence_url(
            "Acme Corp",
            {"url": "https://randomcorp.example/news", "title": "News", "content": ""},
        )
        is None
    )


def test_hangul_org_name_token_is_corroboration() -> None:
    """A complete Hangul organization token in content is evidence."""
    assert (
        corroborating_evidence_url(
            "한빛그리드",
            {
                "url": "https://news.example/item",
                "title": "News",
                "content": "한빛그리드 announced a delivery window.",
            },
        )
        == "https://news.example/item"
    )


def test_searxng_client_refuses_non_http_scheme() -> None:
    """The client rejects non-HTTP URLs before making a request."""
    with pytest.raises(ValueError, match="unsupported Searxng base URL scheme"):
        SearxngRelationVerificationClient(base_url="file:///etc/passwd")
