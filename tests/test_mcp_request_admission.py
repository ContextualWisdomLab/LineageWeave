"""Request-byte admission regressions for the MCP Streamable HTTP boundary."""

from __future__ import annotations

import json
from typing import Any

import pytest

from backend.app.mcp_admission import BoundedRequestBodyApp


class _RecordingApp:
    """Record the replayed request body and terminal replay message."""

    def __init__(self, *, read_after_body: bool = False) -> None:
        self.body = b""
        self.calls = 0
        self.read_after_body = read_after_body
        self.terminal_message: dict[str, Any] | None = None

    async def __call__(self, scope, receive, send) -> None:
        self.calls += 1
        if scope["type"] == "http" and scope.get("method") == "POST":
            while True:
                message = await receive()
                if message["type"] != "http.request":
                    self.terminal_message = message
                    break
                self.body += message.get("body", b"")
                if not message.get("more_body", False):
                    if self.read_after_body:
                        self.terminal_message = await receive()
                    break
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})


async def _invoke(
    app,
    *,
    headers: list[tuple[bytes, bytes]],
    chunks: list[Any] | None = None,
    messages: list[dict[str, Any]] | None = None,
    method: str = "POST",
    scope_type: str = "http",
) -> tuple[int, dict[str, Any], list[dict[str, Any]]]:
    """Invoke an ASGI app with exact messages and decode its response."""
    scope = {
        "type": scope_type,
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "https",
        "path": "/mcp",
        "raw_path": b"/mcp",
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 443),
    }
    if messages is None:
        body_chunks = chunks if chunks is not None else [b""]
        messages = [
            {
                "type": "http.request",
                "body": chunk,
                "more_body": index < len(body_chunks) - 1,
            }
            for index, chunk in enumerate(body_chunks)
        ]
    queued_messages = list(messages)
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return queued_messages.pop(0)

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    await app(scope, receive, send)
    start = next(message for message in sent if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")
        for message in sent
        if message["type"] == "http.response.body"
    )
    return int(start["status"]), json.loads(body) if body else {}, sent


def test_nonpositive_limit_is_rejected_at_construction() -> None:
    """An invalid resource envelope cannot create an admission boundary."""
    with pytest.raises(ValueError, match="maximum_bytes must be positive"):
        BoundedRequestBodyApp(_RecordingApp(), maximum_bytes=0)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("scope_type", "method"),
    [("lifespan", "POST"), ("http", "GET")],
)
async def test_non_post_traffic_passes_through_unchanged(
    scope_type: str,
    method: str,
) -> None:
    """Only MCP POST bodies are buffered by the admission layer."""
    downstream = _RecordingApp()
    app = BoundedRequestBodyApp(downstream, maximum_bytes=8)

    status, payload, _ = await _invoke(
        app,
        headers=[],
        chunks=[b""],
        method=method,
        scope_type=scope_type,
    )

    assert status == 204
    assert payload == {}
    assert downstream.calls == 1


@pytest.mark.asyncio
async def test_over_limit_declared_length_is_rejected_before_downstream() -> None:
    downstream = _RecordingApp()
    app = BoundedRequestBodyApp(downstream, maximum_bytes=8)

    status, payload, sent = await _invoke(
        app,
        headers=[
            (b"content-type", b"application/json"),
            (b"content-length", b"9"),
        ],
        chunks=[b"123456789"],
    )

    assert status == 413
    assert payload == {"error_code": "mcp_request_too_large"}
    assert (b"cache-control", b"no-store") in sent[0]["headers"]
    assert downstream.calls == 0


@pytest.mark.asyncio
async def test_chunked_body_is_bounded_without_content_length() -> None:
    downstream = _RecordingApp()
    app = BoundedRequestBodyApp(downstream, maximum_bytes=8)

    status, payload, _ = await _invoke(
        app,
        headers=[(b"content-type", b"application/json")],
        chunks=[b"1234", b"5678", b"9"],
    )

    assert status == 413
    assert payload == {"error_code": "mcp_request_too_large"}
    assert downstream.calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers",
    [
        [(b"content-length", b"-1")],
        [(b"content-length", b"not-a-number")],
        [(b"content-length", b"\xff")],
        [(b"content-length", b"9" * 5000)],
        [(b"content-length", b"3"), (b"content-length", b"4")],
        [(b"content-length", b"3"), (b"transfer-encoding", b"chunked")],
    ],
)
async def test_ambiguous_or_invalid_length_fails_closed(headers) -> None:
    downstream = _RecordingApp()
    app = BoundedRequestBodyApp(downstream, maximum_bytes=8)

    status, payload, _ = await _invoke(app, headers=headers, chunks=[b"123"])

    assert status == 400
    assert payload == {"error_code": "mcp_invalid_content_length"}
    assert downstream.calls == 0


@pytest.mark.asyncio
async def test_declared_and_actual_length_must_match() -> None:
    """A truncated or smuggled body cannot cross the admission boundary."""
    downstream = _RecordingApp()
    app = BoundedRequestBodyApp(downstream, maximum_bytes=8)

    status, payload, _ = await _invoke(
        app,
        headers=[(b"content-length", b"4")],
        chunks=[b"123"],
    )

    assert status == 400
    assert payload == {"error_code": "mcp_content_length_mismatch"}
    assert downstream.calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("messages", "expected_error"),
    [
        ([{"type": "http.disconnect"}], "mcp_request_disconnected"),
        ([{"type": "unexpected"}], "mcp_invalid_request_body"),
        (
            [{"type": "http.request", "body": "not-bytes", "more_body": False}],
            "mcp_invalid_request_body",
        ),
    ],
)
async def test_invalid_asgi_body_stream_fails_closed(messages, expected_error) -> None:
    """Disconnects and malformed ASGI messages never reach OAuth or JSON parsing."""
    downstream = _RecordingApp()
    app = BoundedRequestBodyApp(downstream, maximum_bytes=8)

    status, payload, _ = await _invoke(app, headers=[], messages=messages)

    assert status == 400
    assert payload == {"error_code": expected_error}
    assert downstream.calls == 0


@pytest.mark.asyncio
async def test_under_limit_body_is_replayed_byte_exactly() -> None:
    downstream = _RecordingApp(read_after_body=True)
    app = BoundedRequestBodyApp(downstream, maximum_bytes=8)

    status, payload, _ = await _invoke(
        app,
        headers=[(b"Content-Length", b"8")],
        chunks=[b"123", b"45678"],
    )

    assert status == 204
    assert payload == {}
    assert downstream.calls == 1
    assert downstream.body == b"12345678"
    assert downstream.terminal_message == {"type": "http.disconnect"}


@pytest.mark.asyncio
async def test_under_limit_stream_without_declared_length_is_replayed() -> None:
    """Chunked/streamed requests remain supported when their actual bytes are bounded."""
    downstream = _RecordingApp()
    app = BoundedRequestBodyApp(downstream, maximum_bytes=8)

    status, payload, _ = await _invoke(
        app,
        headers=[(b"transfer-encoding", b"chunked")],
        chunks=[b"12", b"345"],
    )

    assert status == 204
    assert payload == {}
    assert downstream.body == b"12345"
