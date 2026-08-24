from __future__ import annotations

import pytest

from lineageweave import http_client


def test_request_rejects_private_connected_peer_before_sending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Socket:
        def getpeername(self) -> tuple[str, int]:
            return "127.0.0.1", 443

    class Connection:
        sock = Socket()
        requested = False

        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def connect(self) -> None:
            pass

        def request(self, *_args, **_kwargs) -> None:
            self.requested = True

        def close(self) -> None:
            pass

    monkeypatch.setattr(http_client.http.client, "HTTPConnection", Connection)

    with pytest.raises(ValueError, match="non-public network target"):
        http_client._request(
            "GET",
            "http://example.test/evidence",
            body=None,
            headers={},
            timeout=1,
            require_public_peer=True,
        )


def test_request_sends_after_public_connected_peer_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Socket:
        def getpeername(self) -> tuple[str, int]:
            return "93.184.216.34", 80

    class Response:
        status = 200

        def getheader(self, _name: str) -> str:
            return "2"

        def read(self, _length: int) -> bytes:
            return b"ok"

    class Connection:
        sock = Socket()
        requested = False

        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def connect(self) -> None:
            pass

        def request(self, *_args, **_kwargs) -> None:
            self.requested = True

        def getresponse(self) -> Response:
            return Response()

        def close(self) -> None:
            pass

    monkeypatch.setattr(http_client.http.client, "HTTPConnection", Connection)

    assert http_client._request(
        "GET",
        "http://example.test/evidence",
        body=None,
        headers={},
        timeout=1,
        require_public_peer=True,
    ) == (200, b"ok")


@pytest.mark.parametrize("raw", [b"not-json", b"\xff"])
def test_json_helpers_reject_non_json_and_wrong_shapes(
    monkeypatch: pytest.MonkeyPatch, raw: bytes
) -> None:
    monkeypatch.setattr(http_client, "_request", lambda *_args, **_kwargs: (200, raw))
    with pytest.raises(http_client.HttpClientError, match="non-JSON") as error:
        http_client.get_json("https://gateway.example/health", timeout=1)
    assert isinstance(error.value.__cause__, (UnicodeDecodeError, http_client.json.JSONDecodeError))

    monkeypatch.setattr(http_client, "_request", lambda *_args, **_kwargs: (200, b"[]"))
    with pytest.raises(http_client.HttpClientError, match="JSON object"):
        http_client.post_json("https://gateway.example/v1", {}, headers={}, timeout=1)

    monkeypatch.setattr(http_client, "_request", lambda *_args, **_kwargs: (200, b"{}"))
    with pytest.raises(http_client.HttpClientError, match="JSON array"):
        http_client.get_json_list("https://gateway.example/items", timeout=1)


@pytest.mark.parametrize(
    "helper",
    [
        http_client.post_json,
        http_client.post_form,
        http_client.get_json,
        http_client.get_json_list,
    ],
)
def test_json_helpers_raise_on_http_errors(
    monkeypatch: pytest.MonkeyPatch, helper
) -> None:
    monkeypatch.setattr(http_client, "_request", lambda *_args, **_kwargs: (503, b"{}"))
    kwargs = {"timeout": 1}
    if helper is http_client.post_json:
        kwargs.update(payload={}, headers={})
    elif helper is http_client.post_form:
        kwargs.update(fields={}, headers={})
    with pytest.raises(http_client.HttpClientError, match="HTTP 503"):
        if helper in (http_client.post_json, http_client.post_form):
            helper("https://gateway.example/endpoint", **kwargs)
        else:
            helper("https://gateway.example/endpoint", **kwargs)


def test_json_helpers_accept_optional_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, ...]] = []

    def request(*args, **kwargs):
        calls.append((args, kwargs))
        return 200, b"{}"

    monkeypatch.setattr(http_client, "_request", request)
    assert http_client.get_json("https://gateway.example", timeout=1) == {}
    assert http_client.post_form("https://gateway.example", {}, timeout=1) == {}
    assert len(calls) == 2


def test_request_hides_raw_provider_transport_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class _BrokenConnection:
        sock = None

        def __init__(self, *args, **kwargs) -> None:
            return None

        def request(self, *args, **kwargs) -> None:
            raise TimeoutError("provider secret must not escape")

        def close(self) -> None:
            return None

    monkeypatch.setattr(http_client.http.client, "HTTPConnection", _BrokenConnection)
    with pytest.raises(http_client.HttpClientError, match="provider transport unavailable") as error:
        http_client.post_json(
            "http://gateway.example/v1/chat/completions",
            {"messages": []},
            headers={},
            timeout=1,
        )
    assert "provider secret" not in str(error.value)
    assert isinstance(error.value.__cause__, TimeoutError)
