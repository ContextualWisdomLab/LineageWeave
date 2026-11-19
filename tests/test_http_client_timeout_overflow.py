"""Native timeout conversion stays inside the safe shared transport boundary."""
from __future__ import annotations

import socket

import pytest

from lineageweave import http_client


@pytest.mark.parametrize("scheme", ["http", "https"])
@pytest.mark.parametrize("timeout", [1e20, 1e308])
@pytest.mark.parametrize("operation", ["post_json", "post_form", "get_json", "get_json_list"])
def test_native_timeout_overflow_is_safe_and_closes_connection(
    monkeypatch: pytest.MonkeyPatch,
    scheme: str,
    timeout: float,
    operation: str,
) -> None:
    """All public helpers normalize real settimeout overflow before connecting."""
    closed: list[object] = []
    original_close = http_client.http.client.HTTPConnection.close

    def close(connection: object) -> None:
        closed.append(connection)
        original_close(connection)

    def forbid_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("native timeout overflow must precede connect")

    monkeypatch.setattr(http_client.http.client.HTTPConnection, "close", close)
    monkeypatch.setattr(socket.socket, "connect", forbid_connect)
    url = f"{scheme}://127.0.0.1:1/synthetic-private-path?synthetic=private-query"
    helper = getattr(http_client, operation)
    try:
        with pytest.raises(http_client.HttpClientError) as captured:
            if operation in {"post_json", "post_form"}:
                helper(url, {}, headers={}, timeout=timeout)
            else:
                helper(url, timeout=timeout)
        assert type(captured.value.__cause__) is OverflowError
        assert str(captured.value) == "provider transport unavailable"
        assert "synthetic-private" not in str(captured.value)
    finally:
        assert len(closed) == 1
        assert closed[0].sock is None


def test_unexpected_programming_type_error_is_not_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The scoped numeric fix does not catch arbitrary programming exceptions."""
    fault = TypeError("synthetic programming defect")
    closed: list[object] = []
    original_close = http_client.http.client.HTTPConnection.close

    def request(*args: object, **kwargs: object) -> None:
        raise fault

    def close(connection: object) -> None:
        closed.append(connection)
        original_close(connection)

    monkeypatch.setattr(http_client.http.client.HTTPConnection, "request", request)
    monkeypatch.setattr(http_client.http.client.HTTPConnection, "close", close)
    with pytest.raises(TypeError) as captured:
        http_client.get_json("http://127.0.0.1:1/synthetic", timeout=1)
    assert captured.value is fault
    assert len(closed) == 1 and closed[0].sock is None
