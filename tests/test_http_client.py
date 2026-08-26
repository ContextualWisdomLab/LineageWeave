from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from lineageweave.http_client import (
    HttpClientError,
    chat_completion_content,
    get_json,
    get_json_list,
    post_form,
    post_json,
)
from lineageweave.observability import traced
from tests.test_observability import attach_inmemory_tracer


@pytest.mark.parametrize(
    "body",
    [
        {"error": "raw-provider-secret"},
        {"choices": []},
        {"choices": [{"message": {"content": 123}}]},
        {"choices": [{"message": {"content": ["raw-provider-secret"]}}]},
    ],
)
def test_chat_completion_content_rejects_unsafe_or_malformed_envelopes(body: object) -> None:
    with pytest.raises((TypeError, ValueError)) as error:
        chat_completion_content(body)

    assert "raw-provider-secret" not in str(error.value)


def test_chat_completion_content_returns_text_without_rewriting_it() -> None:
    assert chat_completion_content({"choices": [{"message": {"content": "  []  "}}]}) == "  []  "


class _JsonHandler(BaseHTTPRequestHandler):
    received: dict = {}

    def do_GET(self) -> None:  # noqa: N802 -- BaseHTTPRequestHandler API
        type(self).received = {
            "path": self.path,
            "method": "GET",
            "authorization": self.headers.get("authorization"),
            "traceparent": self.headers.get("traceparent"),
            "session": self.headers.get("x-lineageweave-session-id"),
        }
        if "/users" in self.path:
            payload: object = [{"id": "sub-1", "username": "demo.analyst"}]
        else:
            payload = {"ok": True, "path": self.path}
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 -- BaseHTTPRequestHandler API
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length)
        type(self).received = {
            "path": self.path,
            "authorization": self.headers.get("authorization"),
            "content_type": self.headers.get("content-type"),
            "payload": raw.decode("utf-8"),
            "traceparent": self.headers.get("traceparent"),
        }
        echo = raw.decode("utf-8")
        try:
            echo_obj: object = json.loads(echo)
        except json.JSONDecodeError:
            echo_obj = echo
        body = json.dumps({"ok": True, "echo": echo_obj}).encode("utf-8")
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


class _LargeJsonHandler(BaseHTTPRequestHandler):
    include_length = True

    def do_GET(self) -> None:  # noqa: N802 -- BaseHTTPRequestHandler API
        body = json.dumps({"payload": "x" * 512}).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        if type(self).include_length:
            self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
        server.server_close()

    assert body == {
        "ok": True,
        "echo": {"model": "demo", "input": "hello"},
    }
    assert _JsonHandler.received["path"] == "/v1/embeddings"
    assert _JsonHandler.received["authorization"] == "Bearer test-token"


def test_get_json_fetches_json_from_http_endpoint() -> None:
    _JsonHandler.received = {}
    server, base = _serve(_JsonHandler)
    try:
        body = get_json(
            f"{base}/.well-known/openid-configuration",
            headers={"authorization": "Bearer test-token"},
            timeout=2.0,
        )
    finally:
        server.shutdown()
        server.server_close()

    assert body == {
        "ok": True,
        "path": "/.well-known/openid-configuration",
    }
    assert _JsonHandler.received["authorization"] == "Bearer test-token"


def _traceparent_trace_id(header: str | None) -> str:
    assert header is not None
    parts = header.split("-")
    assert len(parts) == 4
    assert parts[0] == "00"
    assert len(parts[1]) == 32
    assert len(parts[2]) == 16
    return parts[1]


def test_post_json_and_get_json_inject_parent_traceparent(monkeypatch) -> None:
    """Shipped HTTP client injects the parent TraceId as W3C traceparent."""
    attach_inmemory_tracer(monkeypatch)
    captured: dict[str, str | None] = {}
    server, base = _serve(_JsonHandler)
    try:
        with traced("lineageweave.test.parent"):
            from opentelemetry import trace

            parent_trace_id = format(
                trace.get_current_span().get_span_context().trace_id, "032x"
            )
            _JsonHandler.received = {}
            post_json(
                f"{base}/v1/chat/completions",
                {},
                headers={},
                timeout=2.0,
                service_peer_name="contextual-orchestrator",
            )
            captured["post"] = _JsonHandler.received.get("traceparent")
            _JsonHandler.received = {}
            get_json(
                f"{base}/v1/models",
                timeout=2.0,
                service_peer_name="tepp",
            )
            captured["get"] = _JsonHandler.received.get("traceparent")
            _JsonHandler.received = {}
            get_json_list(
                f"{base}/admin/users",
                timeout=2.0,
                service_peer_name="tepp",
            )
            captured["list"] = _JsonHandler.received.get("traceparent")
    finally:
        server.shutdown()
        server.server_close()

    assert parent_trace_id != "0" * 32
    assert _traceparent_trace_id(captured["post"]) == parent_trace_id
    assert _traceparent_trace_id(captured["get"]) == parent_trace_id
    assert _traceparent_trace_id(captured["list"]) == parent_trace_id


def test_get_json_session_header_stays_on_orchestrator_peers(monkeypatch) -> None:
    """Searxng/CalDAV/OIDC GETs keep W3C context without the post session header."""
    from lineageweave.llm_context import use_llm_metadata

    attach_inmemory_tracer(monkeypatch)
    server, base = _serve(_JsonHandler)
    try:
        with use_llm_metadata({"lineageweave_post_session_id": "post-session-1"}):
            _JsonHandler.received = {}
            get_json(f"{base}/search", timeout=2.0, service_peer_name="searxng")
            searxng = dict(_JsonHandler.received)
            _JsonHandler.received = {}
            get_json(f"{base}/generic", timeout=2.0)
            generic = dict(_JsonHandler.received)
            _JsonHandler.received = {}
            get_json(
                f"{base}/v1/models",
                timeout=2.0,
                service_peer_name="contextual-orchestrator",
            )
            orchestrator = dict(_JsonHandler.received)
    finally:
        server.shutdown()
        server.server_close()

    assert searxng.get("session") is None
    assert searxng.get("traceparent")
    assert generic.get("session") is None
    assert generic.get("traceparent")
    assert orchestrator.get("session") == "post-session-1"
    assert orchestrator.get("traceparent")


@pytest.mark.parametrize("include_length", [True, False])
def test_get_json_rejects_responses_over_explicit_byte_limit(
    include_length: bool,
) -> None:
    _LargeJsonHandler.include_length = include_length
    server, base = _serve(_LargeJsonHandler)
    try:
        with pytest.raises(HttpClientError, match="response exceeds"):
            get_json(
                f"{base}/large",
                timeout=2.0,
                maximum_response_bytes=128,
            )
    finally:
        server.shutdown()
        server.server_close()


def test_get_json_rejects_invalid_response_byte_limit() -> None:
    with pytest.raises(ValueError, match="maximum_response_bytes"):
        get_json(
            "https://gateway.example/health",
            timeout=1.0,
            maximum_response_bytes=0,
        )


def test_post_form_posts_urlencoded_fields() -> None:
    _JsonHandler.received = {}
    server, base = _serve(_JsonHandler)
    try:
        body = post_form(
            f"{base}/token",
            {"grant_type": "password", "username": "demo.analyst"},
            timeout=2.0,
        )
    finally:
        server.shutdown()
        server.server_close()

    assert body["ok"] is True
    assert "grant_type=password" in _JsonHandler.received["payload"]
    assert _JsonHandler.received["content_type"] == (
        "application/x-www-form-urlencoded"
    )


def test_get_json_refuses_file_scheme() -> None:
    with pytest.raises(ValueError, match="non-http"):
        get_json("file:///etc/passwd", timeout=1.0)


def test_oidc_scripts_do_not_import_urllib_request() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    for relative in (
        "scripts/smoke_test_oidc.py",
        "scripts/seed_demo_data.py",
        "backend/app/auth.py",
        "backend/tests/test_api.py",
    ):
        text = (root / relative).read_text()
        import_lines = [
            line
            for line in text.splitlines()
            if line.lstrip().startswith(("import ", "from "))
        ]
        joined = "\n".join(import_lines)
        assert "urllib.request" not in joined, relative
        assert "urlopen" not in joined, relative


def test_dockerfiles_pin_digest_and_declare_non_root_user() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    for relative in (
        "docker/postgres-init/Dockerfile",
        "docker/keycloak/Dockerfile",
        "docker/searxng/Dockerfile",
        "backend/Dockerfile",
        "frontend/Dockerfile",
    ):
        text = (root / relative).read_text()
        assert "@sha256:" in text, (
            f"{relative} must pin the base image by digest"
        )
        assert "USER " in text, (
            f"{relative} must declare a non-root USER"
        )


def test_post_json_https_negotiates_tls_instead_of_plaintext() -> None:
    server, base = _serve(_JsonHandler)
    try:
        https_url = base.replace("http://", "https://", 1) + "/v1/embeddings"
        with pytest.raises(HttpClientError, match="provider transport unavailable") as error:
            post_json(https_url, {"model": "demo"}, headers={}, timeout=2.0)
        assert error.value.__cause__ is not None
    finally:
        server.shutdown()
        server.server_close()


def test_post_json_raises_on_http_error() -> None:
    server, base = _serve(_ErrorHandler)
    try:
        with pytest.raises(HttpClientError, match="HTTP 503"):
            post_json(f"{base}/fail", {}, headers={}, timeout=2.0)
    finally:
        server.shutdown()
        server.server_close()


def test_post_json_preserves_only_bounded_remote_failure_fields(monkeypatch) -> None:
    """Typed failure provenance excludes the remote message and response body."""

    monkeypatch.setattr(
        "lineageweave.http_client._request",
        lambda *_args, **_kwargs: (
            504,
            b'{"error":{"code":"request_deadline_exceeded","retryable":true,"message":"private"}}',
        ),
    )
    with pytest.raises(HttpClientError) as caught:
        post_json("https://orchestrator.example/v1/chat/completions", {}, headers={}, timeout=2.0)
    assert caught.value.http_status == 504
    assert caught.value.remote_error_code == "request_deadline_exceeded"
    assert caught.value.retryable is True
    assert "private" not in str(caught.value)
