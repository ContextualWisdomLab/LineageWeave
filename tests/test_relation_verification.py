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
    RelationVerificationClient,
    STATUS_CORROBORATED,
    STATUS_UNCORROBORATED,
    NullRelationVerificationClient,
    SearxngRelationVerificationClient,
    corroborating_evidence_url,
)


class _ResultsHandler(BaseHTTPRequestHandler):
    received_query: str = ""

    def do_GET(self) -> None:  # noqa: N802 -- BaseHTTPRequestHandler API
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        type(self).received_query = query.get("q", [""])[0]
        if "NoList" in type(self).received_query:
            payload = {"query": type(self).received_query, "results": {}}
        elif "Skip" in type(self).received_query:
            payload = {"query": type(self).received_query, "results": [None]}
        elif "NoEvidence" in type(self).received_query:
            payload = {
                "query": type(self).received_query,
                "results": [{"url": "https://example.com/item", "content": ""}],
            }
        elif "Acme" in type(self).received_query:
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
    client = NullRelationVerificationClient()
    assert client.available is False
    with pytest.raises(RuntimeError):
        client.verify("Acme Corp", "Voice of Customer")


def test_protocol_stub_raises_instead_of_returning_a_fake_result() -> None:
    """The protocol's executable stub must fail if called directly."""
    with pytest.raises(NotImplementedError):
        RelationVerificationClient.verify(object(), "Acme", "Voice of Customer")


def test_searxng_client_reports_corroborated_with_evidence_url() -> None:
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
    server, base = _serve()
    try:
        client = SearxngRelationVerificationClient(base_url=base)
        result = client.verify("Totally Fictitious Nonexistent Org", "Voice of Customer")
    finally:
        server.shutdown()

    assert result.status_code == STATUS_UNCORROBORATED
    assert result.evidence_url is None


@pytest.mark.parametrize("organization_name", ["NoList", "Skip", "NoEvidence"])
def test_searxng_client_fails_closed_for_unusable_results(organization_name: str) -> None:
    """Malformed and unciting search results remain explicitly uncorroborated."""
    server, base = _serve()
    try:
        result = SearxngRelationVerificationClient(base_url=base).verify(
            organization_name, "Voice of Customer"
        )
    finally:
        server.shutdown()

    assert result.status_code == STATUS_UNCORROBORATED
    assert result.evidence_url is None


def test_query_echo_on_a_search_host_is_not_corroboration() -> None:
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
    assert (
        corroborating_evidence_url(
            "Acme Corp",
            {"url": "https://www.acme.example/news", "title": "News", "content": ""},
        )
        == "https://www.acme.example/news"
    )


def test_short_name_token_inside_another_word_is_not_corroboration() -> None:
    """A search snippet must contain the organization token as a word."""
    assert (
        corroborating_evidence_url(
            "Alpha Corp",
            {
                "url": "https://unrelated.example/news",
                "title": "Alphabetical index",
                "content": "An alphabetical index of sample terms.",
            },
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


def test_fixture_descriptors_do_not_corrobate_an_unrelated_search_hit() -> None:
    """Generic synthetic-data words must not stand in for organization identity."""
    assert (
        corroborating_evidence_url(
            "Zzqxvthorp Fictitious Nonexistent Org",
            {
                "url": "https://learn.microsoft.com/writing-style",
                "title": "Fictitious names and addresses",
                "content": "Documentation explains fictitious and nonexistent examples.",
            },
        )
        is None
    )


def test_missing_url_and_all_generic_tokens_are_not_evidence() -> None:
    """Missing URLs and names made only of fixture words cannot cite evidence."""
    assert corroborating_evidence_url("Acme Corp", {"content": "Acme"}) is None
    assert (
        corroborating_evidence_url(
            "Fictitious Nonexistent Org",
            {"url": "https://example.com/item", "content": "Fictitious"},
        )
        is None
    )


def test_hangul_org_name_token_is_corroboration() -> None:
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
    with pytest.raises(ValueError, match="unsupported Searxng base URL scheme"):
        SearxngRelationVerificationClient(base_url="file:///etc/passwd")
