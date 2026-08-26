"""SSRF and redirect rejection for public-resource retrieval."""

from __future__ import annotations

import ipaddress
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from lineageweave.public_resource_retrieval import (
    PublicResourceUnavailable,
    PublicTarget,
    PublicTargetRejected,
    classify_public_target,
    extract_visible_text,
    is_public_ip,
    retrieve_public_target,
)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://localhost/secret",
        "https://127.0.0.1/secret",
        "http://[::1]/secret",
        "http://10.0.0.8/internal",
        "http://192.168.1.4/internal",
        "http://169.254.169.254/latest/meta-data",
        "http://metadata.google.internal/",
        "http://example.local/page",
        "https://searx.example/search",
        "https://www.google.com/search?q=x",
        "http://user:pass@example.com/x",
        "",
        "not-a-url",
    ],
)
def test_classify_public_target_rejects_non_public_urls(url: str) -> None:
    assert classify_public_target(url) is None


def test_classify_public_target_accepts_public_https() -> None:
    target = classify_public_target("https://example.com/evidence?q=apollo")
    assert target is not None
    assert target.hostname == "example.com"
    assert target.port == 443
    assert target.request_path == "/evidence?q=apollo"
    assert target.host_header == "example.com"


def test_ipv6_target_uses_raw_connect_host_and_bracketed_host_header(monkeypatch) -> None:
    observed: dict[str, object] = {}

    class _Response:
        status = 200

        def getheader(self, name: str):
            return "text/plain" if name == "Content-Type" else None

        def read(self, amount: int) -> bytes:
            return b"Public corroboration."

    class _Connection:
        sock = object()

        def __init__(self, host: str, port: int, *, timeout: float) -> None:
            observed["host"] = host

        def connect(self) -> None:
            return None

        def request(self, method: str, path: str, *, headers: dict[str, str]) -> None:
            observed["headers"] = headers

        def getresponse(self) -> _Response:
            return _Response()

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        "lineageweave.public_resource_retrieval.http.client.HTTPConnection",
        _Connection,
    )
    target = PublicTarget(
        scheme="http",
        hostname="2001:4860:4860::8888",
        port=80,
        request_path="/evidence",
        original_url="http://[2001:4860:4860::8888]/evidence",
    )
    retrieve_public_target(target, ipaddress.ip_address("2001:4860:4860::8888"))
    assert observed["host"] == "2001:4860:4860::8888"
    assert observed["headers"] == {
        "host": "[2001:4860:4860::8888]",
        "accept": "text/html, text/plain;q=0.9",
        "user-agent": "LineageWeave-source-research/2.19",
    }


def test_is_public_ip_rejects_private_and_mapped_loopback() -> None:
    assert not is_public_ip(ipaddress.ip_address("127.0.0.1"))
    assert not is_public_ip(ipaddress.ip_address("10.1.2.3"))
    assert not is_public_ip(ipaddress.ip_address("::1"))
    assert not is_public_ip(ipaddress.ip_address("::ffff:127.0.0.1"))
    assert not is_public_ip(ipaddress.ip_address("fc00::1"))
    assert is_public_ip(ipaddress.ip_address("93.184.216.34"))


def test_extract_visible_text_drops_script_and_keeps_body() -> None:
    raw = (
        b"<html><head><title> Public Apollo </title>"
        b"<script>ignore me</script></head>"
        b"<body><p>Apollo is a public project.</p></body></html>"
    )
    title, excerpt = extract_visible_text(raw, "text/html")
    assert title == "Public Apollo"
    assert excerpt == "Apollo is a public project."
    assert "ignore" not in excerpt


class _RedirectHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        self.send_response(302)
        self.send_header("location", "http://127.0.0.1/private")
        self.end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return


class _HtmlHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        body = b"<html><head><title>Cited page</title></head><body><p>Public corroboration.</p></body></html>"
        self.send_response(200)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return


def _serve(handler: type[BaseHTTPRequestHandler]) -> tuple[HTTPServer, int]:
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = int(server.server_address[1])
    return server, port


def _target(port: int) -> PublicTarget:
    return PublicTarget(
        scheme="http",
        hostname="example.com",
        port=port,
        request_path="/evidence",
        original_url=f"https://example.com/evidence",
    )


def test_retrieve_public_target_rejects_redirects() -> None:
    server, port = _serve(_RedirectHandler)
    try:
        with pytest.raises(PublicTargetRejected, match="redirects"):
            retrieve_public_target(_target(port), ipaddress.ip_address("127.0.0.1"))
    finally:
        server.shutdown()


def test_retrieve_public_target_returns_visible_html() -> None:
    server, port = _serve(_HtmlHandler)
    try:
        resource = retrieve_public_target(_target(port), ipaddress.ip_address("127.0.0.1"))
    finally:
        server.shutdown()
    assert resource.title == "Cited page"
    assert resource.excerpt_text == "Public corroboration."
    assert resource.url == "https://example.com/evidence"


def test_retrieve_public_target_rejects_oversized_declared_length() -> None:
    class _HugeHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self.send_response(200)
            self.send_header("content-type", "text/plain")
            self.send_header("content-length", "999999")
            self.end_headers()

        def log_message(self, format: str, *args) -> None:  # noqa: A002
            return

    server, port = _serve(_HugeHandler)
    try:
        with pytest.raises(PublicTargetRejected, match="byte limit"):
            retrieve_public_target(
                _target(port),
                ipaddress.ip_address("127.0.0.1"),
                maximum_response_bytes=64,
            )
    finally:
        server.shutdown()


def test_retrieve_public_target_maps_http_errors() -> None:
    class _ErrorHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self.send_response(503)
            self.end_headers()

        def log_message(self, format: str, *args) -> None:  # noqa: A002
            return

    server, port = _serve(_ErrorHandler)
    try:
        with pytest.raises(PublicResourceUnavailable):
            retrieve_public_target(_target(port), ipaddress.ip_address("127.0.0.1"))
    finally:
        server.shutdown()
