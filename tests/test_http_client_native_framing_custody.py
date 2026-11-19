"""Synthetic native-HTTP regressions for framing and detached-response custody."""
from __future__ import annotations

import http.client
import io
import json
from collections.abc import Iterator

import pytest

from lineageweave import http_client, post_chat


_BODY = json.dumps({"choices": [{"message": {"content": "Synthetic answer.\nCITED SOURCES: 1"}}]}).encode()
_NATIVE_CONNECTION = http.client.HTTPConnection
_NATIVE_RESPONSE = http.client.HTTPResponse


class _WireSocket:
    def __init__(self, wire: bytes) -> None:
        self.stream = io.BytesIO(wire)
        self.closed = False

    def sendall(self, _data: bytes) -> None:
        pass

    def makefile(self, mode: str) -> io.BytesIO:
        assert mode == "rb"
        return self.stream

    def close(self) -> None:
        # Native socket.close does not close an independently acquired makefile.
        self.closed = True


@pytest.fixture
def native_transport(monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    """Keep native response ownership while replacing only socket IO."""
    owned: list[tuple[http.client.HTTPConnection, _WireSocket, list[http.client.HTTPResponse]]] = []

    def deny_network(*_args: object, **_kwargs: object) -> None:
        pytest.fail("synthetic native HTTP test attempted real network IO")

    monkeypatch.setattr(http_client.http.client.socket, "create_connection", deny_network)
    monkeypatch.setattr(http_client.http.client.socket, "getaddrinfo", deny_network)

    def install(wire: bytes) -> tuple[http.client.HTTPConnection, _WireSocket, list[http.client.HTTPResponse]]:
        sock = _WireSocket(wire)
        conn = _NATIVE_CONNECTION("synthetic.invalid", timeout=1)
        conn.sock = sock  # type: ignore[assignment]
        responses: list[http.client.HTTPResponse] = []

        def capture(*args: object, **kwargs: object) -> http.client.HTTPResponse:
            response = _NATIVE_RESPONSE(*args, **kwargs)  # type: ignore[arg-type]
            responses.append(response)
            return response

        conn.response_class = capture  # type: ignore[assignment]
        monkeypatch.setattr(http_client.http.client, "HTTPConnection", lambda *a, **kw: conn)
        row = (conn, sock, responses)
        owned.append(row)
        return row

    try:
        yield install
    finally:
        for conn, sock, responses in owned:
            for response in responses:
                response.close()
            conn.close()
            assert sock.closed and sock.stream.closed


def _wire(headers: bytes, payload: bytes) -> bytes:
    return b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n" + headers + b"\r\n" + payload


def _framing_case(name: str) -> tuple[bytes, bool]:
    chunk = f"{len(_BODY):x}\r\n".encode() + _BODY + b"\r\n"
    length = f"Content-Length: {len(_BODY)}\r\n".encode()
    if name == "declared_complete":
        return _wire(length, _BODY), True
    if name == "declared_short":
        return _wire(f"Content-Length: {len(_BODY) + 17}\r\n".encode(), _BODY), False
    if name == "lengthless_complete":
        return _wire(b"Connection: close\r\n", _BODY), True
    suffix = name.removesuffix("_dual")
    tails = {"chunked_complete": b"0\r\n\r\n", "missing_terminal": b"", "invalid_next": b"NOT_HEX\r\n", "truncated_next": b"4\r\nx"}
    headers = b"Transfer-Encoding: chunked\r\n" + (length if name.endswith("_dual") else b"")
    return _wire(headers, chunk + tails[suffix]), suffix == "chunked_complete"


@pytest.mark.parametrize("consumer", ["bounded_get", "post_chat"])
@pytest.mark.parametrize("case", ["declared_complete", "declared_short", "lengthless_complete", "chunked_complete", "chunked_complete_dual", "missing_terminal", "missing_terminal_dual", "invalid_next", "invalid_next_dual", "truncated_next", "truncated_next_dual"])
def test_native_framing_rejects_incomplete_valid_json(native_transport: object, consumer: str, case: str) -> None:
    """Complete JSON cannot substitute for a complete native HTTP frame."""
    wire, complete = _framing_case(case)
    # Independent native full-read oracle over identical synthetic bytes.
    oracle = _NATIVE_RESPONSE(_WireSocket(wire))
    oracle.begin()
    try:
        if complete:
            assert oracle.read() == _BODY
        else:
            with pytest.raises(http.client.IncompleteRead):
                oracle.read()
    finally:
        oracle.close()
    conn, sock, responses = native_transport(wire)  # type: ignore[operator]

    def consume() -> object:
        if consumer == "bounded_get":
            return http_client.get_json("http://synthetic.invalid/data", timeout=1,
                maximum_response_bytes=len(_BODY) + 32,
                expected_response_media_type="application/json")
        return post_chat.ContextualOrchestratorPostChatClient(
            "http://synthetic.invalid", "synthetic-only-token").answer(
                "What happened?", [post_chat.ChatSourceDocument("synthetic-1", "Synthetic title", "Synthetic body")])

    if complete:
        result = consume()
        if consumer == "bounded_get":
            assert result == json.loads(_BODY)
        else:
            assert result.answer_text == "Synthetic answer."
            assert result.cited_post_ids == ("synthetic-1",)
    else:
        with pytest.raises(http_client.HttpClientError):
            consume()
    assert len(responses) == 1 and sock.closed and conn.sock is None


@pytest.mark.parametrize("connection_close", [False, True])
@pytest.mark.parametrize("case", ["valid", "media_rejection", "limit_rejection", "invalid_length"])
def test_native_detached_response_is_closed_on_return(native_transport: object, connection_close: bool, case: str) -> None:
    """Both the connection and its detached response must settle on error."""
    body = b'{"synthetic": true}'
    media = "text/plain" if case == "media_rejection" else "application/json"
    length = "-1" if case == "invalid_length" else str(len(body))
    wire = (f"HTTP/1.1 200 OK\r\nContent-Type: {media}\r\nContent-Length: {length}\r\n"
            + ("Connection: close\r\n" if connection_close else "") + "\r\n").encode() + body
    conn, sock, responses = native_transport(wire)  # type: ignore[operator]
    kwargs = {"timeout": 1, "maximum_response_bytes": 1 if case == "limit_rejection" else 1024,
              "expected_response_media_type": "application/json"}
    if case == "valid":
        assert http_client.get_json("http://synthetic.invalid/data", **kwargs) == {"synthetic": True}
    else:
        with pytest.raises(http_client.HttpClientError):
            http_client.get_json("http://synthetic.invalid/data", **kwargs)
    assert len(responses) == 1 and sock.closed and conn.sock is None
    # Strong reference above prevents fixture GC from hiding explicit custody.
    assert responses[0].isclosed(), "product returned with a detached response still open"
    assert sock.stream.closed


@pytest.mark.parametrize("dual", [False, True])
@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_native_chunked_limit_remains_inclusive(native_transport, dual: bool, offset: int) -> None:
    """Native terminal validation must not discard the existing decoded-body cap."""
    wire, complete = _framing_case("chunked_complete_dual" if dual else "chunked_complete")
    assert complete
    conn, sock, responses = native_transport(wire)
    kwargs = {"timeout": 1, "maximum_response_bytes": len(_BODY) + offset}
    if offset < 0:
        with pytest.raises(http_client.HttpClientError, match="response exceeds"):
            http_client.get_json("http://synthetic.invalid/data", **kwargs)
    else:
        assert http_client.get_json("http://synthetic.invalid/data", **kwargs) == json.loads(_BODY)
    assert len(responses) == 1 and responses[0].isclosed()
    assert sock.closed and sock.stream.closed and conn.sock is None
