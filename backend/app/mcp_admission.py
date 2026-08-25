"""Bound MCP request bodies before OAuth and JSON decoding."""

from __future__ import annotations

import json
from collections.abc import Sequence

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BoundedRequestBodyApp:
    """Reject ambiguous or oversized MCP POST bodies before parsing."""

    def __init__(self, app: ASGIApp, *, maximum_bytes: int) -> None:
        """Wrap ``app`` with one positive finite body-size limit."""
        if maximum_bytes <= 0:
            raise ValueError("maximum_bytes must be positive")
        self._app = app
        self._maximum_bytes = maximum_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Apply admission to HTTP POST and pass other traffic unchanged."""
        if scope["type"] != "http" or scope.get("method") != "POST":
            await self._app(scope, receive, send)
            return

        content_lengths = _header_values(scope, b"content-length")
        transfer_encodings = _header_values(scope, b"transfer-encoding")
        declared_length = _parse_content_length(
            content_lengths, transfer_encodings, maximum_bytes=self._maximum_bytes
        )
        if declared_length is _INVALID_LENGTH:
            await _send_error(send, 400, "mcp_invalid_content_length")
            return
        if declared_length is _TOO_LARGE:
            await _send_error(send, 413, "mcp_request_too_large")
            return
        if isinstance(declared_length, int) and declared_length > self._maximum_bytes:
            await _send_error(send, 413, "mcp_request_too_large")
            return

        body = bytearray()
        while True:
            message = await receive()
            message_type = message.get("type")
            if message_type == "http.disconnect":
                await _send_error(send, 400, "mcp_request_disconnected")
                return
            if message_type != "http.request":
                await _send_error(send, 400, "mcp_invalid_request_body")
                return
            chunk = message.get("body", b"")
            if not isinstance(chunk, bytes):
                await _send_error(send, 400, "mcp_invalid_request_body")
                return
            if len(body) + len(chunk) > self._maximum_bytes:
                await _send_error(send, 413, "mcp_request_too_large")
                return
            body.extend(chunk)
            if not message.get("more_body", False):
                break

        if isinstance(declared_length, int) and declared_length != len(body):
            await _send_error(send, 400, "mcp_content_length_mismatch")
            return

        replayed = False

        async def replay_receive() -> Message:
            """Replay the admitted body once, then preserve client lifecycle events."""
            nonlocal replayed
            if replayed:
                return await receive()
            replayed = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self._app(scope, replay_receive, send)


class _InvalidLength:
    """Sentinel distinguishing an invalid length from an absent one."""


_INVALID_LENGTH = _InvalidLength()


class _TooLarge:
    """Sentinel for a decimal length known to exceed the body limit."""


_TOO_LARGE = _TooLarge()


def _header_values(scope: Scope, name: bytes) -> tuple[bytes, ...]:
    """Return every raw value for one case-insensitive request header."""
    return tuple(
        value
        for header_name, value in scope.get("headers", [])
        if header_name.lower() == name
    )


def _parse_content_length(
    content_lengths: Sequence[bytes],
    transfer_encodings: Sequence[bytes],
    *,
    maximum_bytes: int | None = None,
) -> int | None | _InvalidLength | _TooLarge:
    """Return an unambiguous nonnegative length, absence, or invalid sentinel."""
    if len(content_lengths) > 1 or (content_lengths and transfer_encodings):
        return _INVALID_LENGTH
    if not content_lengths:
        return None
    try:
        decoded = content_lengths[0].decode("ascii")
    except UnicodeDecodeError:
        return _INVALID_LENGTH
    if not decoded or not decoded.isdecimal():
        return _INVALID_LENGTH
    normalized = decoded.lstrip("0") or "0"
    if maximum_bytes is not None and len(normalized) > len(str(maximum_bytes)):
        return _TOO_LARGE
    try:
        return int(decoded, 10)
    except ValueError:
        return _INVALID_LENGTH


async def _send_error(send: Send, status_code: int, error_code: str) -> None:
    """Send one bounded payload-safe admission error response."""
    body = json.dumps(
        {"error_code": error_code}, ensure_ascii=True, separators=(",", ":")
    ).encode("ascii")
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
        (b"cache-control", b"no-store"),
    ]
    await send(
        {"type": "http.response.start", "status": status_code, "headers": headers}
    )
    await send({"type": "http.response.body", "body": body})
