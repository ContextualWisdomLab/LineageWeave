"""Request-byte admission regressions for the MCP Streamable HTTP boundary."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from backend.app.mcp_admission import BoundedRequestBodyApp


class _RecordingApp:
    """Record the replayed request body when admission succeeds."""

    def __init__(self) -> None:
        self.body = b""
        self.calls = 0

    async def __call__(self, scope, receive, send) -> None:
        self.calls += 1
        while True:
            message = await receive()
            if message["type"] != "http.request":
                break
            self.body += message.get("body", b"")
            if not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})


async def _invoke(
    app,
    *,
    headers: list[tuple[bytes, bytes]],
    chunks: list[bytes],
) -> tuple[int, dict[str, Any]]:
    """Invoke an ASGI app with an exact chunked request and decode its response."""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "https",
        "path": "/mcp",
        "raw_path": b"/mcp",
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 443),
    }
    messages = [
        {
            "type": "http.request",
            "body": chunk,
            "more_body": index < len(chunks) - 1,
        }
        for index, chunk in enumerate(chunks)
    ]
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return messages.pop(0)

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    await app(scope, receive, send)
    start = next(message for message in sent if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")
        for message in sent
        if message["type"] == "http.response.body"
    )
    return int(start["status"]), json.loads(body) if body else {}


@pytest.mark.asyncio
async def test_over_limit_declared_length_is_rejected_before_downstream() -> None:
    downstream = _RecordingApp()
    app = BoundedRequestBodyApp(downstream, maximum_bytes=8)

    status, payload = await _invoke(
        app,
        headers=[
            (b"content-type", b"application/json"),
            (b"content-length", b"9"),
        ],
        chunks=[b"123456789"],
    )

    assert status == 413
    assert payload == {"error_code": "mcp_request_too_large"}
    assert downstream.calls == 0


@pytest.mark.asyncio
async def test_chunked_body_is_bounded_without_content_length() -> None:
    downstream = _RecordingApp()
    app = BoundedRequestBodyApp(downstream, maximum_bytes=8)

    status, payload = await _invoke(
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
        [(b"content-length", b"3"), (b"content-length", b"4")],
        [(b"content-length", b"3"), (b"transfer-encoding", b"chunked")],
    ],
)
async def test_ambiguous_or_invalid_length_fails_closed(headers) -> None:
    downstream = _RecordingApp()
    app = BoundedRequestBodyApp(downstream, maximum_bytes=8)

    status, payload = await _invoke(app, headers=headers, chunks=[b"123"])

    assert status == 400
    assert payload == {"error_code": "mcp_invalid_content_length"}
    assert downstream.calls == 0


@pytest.mark.asyncio
async def test_under_limit_body_is_replayed_byte_exactly() -> None:
    downstream = _RecordingApp()
    app = BoundedRequestBodyApp(downstream, maximum_bytes=8)

    status, payload = await _invoke(
        app,
        headers=[(b"content-length", b"8")],
        chunks=[b"123", b"45678"],
    )

    assert status == 204
    assert payload == {}
    assert downstream.calls == 1
    assert downstream.body == b"12345678"
