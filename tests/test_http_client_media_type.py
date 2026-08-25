"""Response media-type contract tests for bounded JSON consumers."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from lineageweave.http_client import HttpClientError, get_json


class _MediaTypeHandler(BaseHTTPRequestHandler):
    response_media_type = "application/json"

    def do_GET(self) -> None:  # noqa: N802 -- BaseHTTPRequestHandler API
        body = json.dumps({"ok": True}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", type(self).response_media_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A002 -- stdlib API
        del format, args


def _serve() -> tuple[HTTPServer, str]:
    server = HTTPServer(("127.0.0.1", 0), _MediaTypeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    return server, f"http://{host}:{port}"


def test_get_json_accepts_expected_media_type_with_parameters() -> None:
    _MediaTypeHandler.response_media_type = "application/json; charset=utf-8"
    server, base_url = _serve()
    try:
        result = get_json(
            f"{base_url}/projection",
            timeout=2,
            expected_response_media_type="application/json",
        )
    finally:
        server.shutdown()
        server.server_close()

    assert result == {"ok": True}


def test_get_json_rejects_unexpected_media_type_before_json_decode() -> None:
    _MediaTypeHandler.response_media_type = "application/json"
    server, base_url = _serve()
    try:
        with pytest.raises(HttpClientError, match="unexpected response media type"):
            get_json(
                f"{base_url}/projection",
                timeout=2,
                expected_response_media_type=(
                    "application/vnd.contextualwisdomlab."
                    "naruon-calendar.v1+json"
                ),
            )
    finally:
        server.shutdown()
        server.server_close()


def test_get_json_rejects_invalid_expected_media_type_configuration() -> None:
    with pytest.raises(ValueError, match="expected_response_media_type"):
        get_json(
            "https://naruon.example/api/calendar/events",
            timeout=2,
            expected_response_media_type="text/html; charset=utf-8",
        )
