from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from lineageweave.http_client import HttpClientError, post_json


class _JsonHandler(BaseHTTPRequestHandler):
    received: dict = {}

    def do_POST(self) -> None:  # noqa: N802 -- BaseHTTPRequestHandler API
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length)
        type(self).received = {
            "path": self.path,
            "authorization": self.headers.get("authorization"),
            "payload": json.loads(raw.decode("utf-8")),
        }
        body = json.dumps({"ok": True, "echo": type(self).received["payload"]}).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A002 -- stdlib signature
        return


class _ErrorHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 -- BaseHTTPRequestHandler API
        self.send_response(503)
        self.send_header("content-length", "0")
        self.end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A002 -- stdlib signature
        return


def _serve(handler: type[BaseHTTPRequestHandler]) -> tuple[HTTPServer, str]:
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    return server, f"http://{host}:{port}"


def test_post_json_refuses_file_scheme() -> None:
    with pytest.raises(ValueError, match="non-http"):
        post_json("file:///etc/passwd", {}, headers={}, timeout=1.0)


def test_post_json_refuses_missing_hostname() -> None:
    with pytest.raises(ValueError, match="hostname"):
        post_json("https:///v1/embeddings", {}, headers={}, timeout=1.0)


def test_post_json_posts_json_to_http_endpoint() -> None:
    _JsonHandler.received = {}
    server, base = _serve(_JsonHandler)
    try:
        body = post_json(
            f"{base}/v1/embeddings",
            {"model": "demo", "input": "hello"},
            headers={"authorization": "Bearer test-token"},
            timeout=2.0,
        )
    finally:
        server.shutdown()

    assert body == {"ok": True, "echo": {"model": "demo", "input": "hello"}}
    assert _JsonHandler.received["path"] == "/v1/embeddings"
    assert _JsonHandler.received["authorization"] == "Bearer test-token"


def test_post_json_raises_on_http_error() -> None:
    server, base = _serve(_ErrorHandler)
    try:
        with pytest.raises(HttpClientError, match="HTTP 503"):
            post_json(f"{base}/fail", {}, headers={}, timeout=2.0)
    finally:
        server.shutdown()
