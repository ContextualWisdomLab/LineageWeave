"""Trust-boundary tests for bounded MCP request admission."""

from __future__ import annotations

import json

import pytest

from backend.app.mcp_admission import BoundedRequestBodyApp


class Recorder:
    """Capture the single replayed body."""

    def __init__(self) -> None:
        self.body = None

    async def __call__(self, _scope, receive, send) -> None:
        """Read once and return an empty success response."""
        self.body = await receive()
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})


async def invoke(headers, messages, *, method="POST", scope_type="http"):
    """Invoke one ASGI request and return status, payload, and downstream."""
    downstream = Recorder()
    app = BoundedRequestBodyApp(downstream, maximum_bytes=8)
    queue = list(messages)
    sent = []

    async def receive():
        """Return the next supplied ASGI message."""
        return queue.pop(0)

    async def send(message):
        """Capture an ASGI response message."""
        sent.append(message)

    await app({"type": scope_type, "method": method, "headers": headers}, receive, send)
    status = next(
        item["status"] for item in sent if item["type"] == "http.response.start"
    )
    body = b"".join(
        item.get("body", b"") for item in sent if item["type"] == "http.response.body"
    )
    return status, json.loads(body) if body else {}, downstream


def test_nonpositive_limit_fails_closed() -> None:
    """A nonpositive envelope cannot be constructed."""
    with pytest.raises(ValueError):
        BoundedRequestBodyApp(Recorder(), maximum_bytes=0)


@pytest.mark.anyio
async def test_bounded_body_replays_exact_bytes() -> None:
    """An admitted chunked body reaches the SDK once and byte-exact."""
    status, payload, downstream = await invoke(
        [],
        [
            {"type": "http.request", "body": b"123", "more_body": True},
            {"type": "http.request", "body": b"45", "more_body": False},
        ],
    )
    assert (status, payload) == (204, {})
    assert downstream.body == {
        "type": "http.request",
        "body": b"12345",
        "more_body": False,
    }


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("headers", "messages", "status", "code"),
    [
        ([(b"content-length", b"9")], [], 413, "mcp_request_too_large"),
        (
            [(b"content-length", b"3"), (b"content-length", b"3")],
            [],
            400,
            "mcp_invalid_content_length",
        ),
        ([(b"content-length", b"-1")], [], 400, "mcp_invalid_content_length"),
        (
            [(b"content-length", b"4")],
            [{"type": "http.request", "body": b"123", "more_body": False}],
            400,
            "mcp_content_length_mismatch",
        ),
        (
            [],
            [{"type": "http.request", "body": b"123456789", "more_body": False}],
            413,
            "mcp_request_too_large",
        ),
        ([], [{"type": "http.disconnect"}], 400, "mcp_request_disconnected"),
        ([], [{"type": "unexpected"}], 400, "mcp_invalid_request_body"),
        (
            [],
            [{"type": "http.request", "body": "bad", "more_body": False}],
            400,
            "mcp_invalid_request_body",
        ),
    ],
)
async def test_invalid_or_oversized_body_never_reaches_sdk(
    headers, messages, status, code
) -> None:
    """Ambiguous, malformed, and oversized inputs fail before parsing."""
    actual_status, payload, downstream = await invoke(headers, messages)
    assert (actual_status, payload) == (status, {"error_code": code})
    assert downstream.body is None


@pytest.mark.anyio
async def test_non_post_traffic_passes_through() -> None:
    """Admission buffering applies only to POST requests."""
    status, _, downstream = await invoke(
        [], [{"type": "http.request", "body": b"", "more_body": False}], method="GET"
    )
    assert status == 204
    assert downstream.body["body"] == b""
