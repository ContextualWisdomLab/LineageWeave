from __future__ import annotations

import pytest

import lineageweave.http_client as http_client


def test_json_helpers_reject_non_json_and_wrong_shapes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(http_client, "_request", lambda *_args, **_kwargs: (200, b"not-json"))
    with pytest.raises(http_client.HttpClientError, match="non-JSON"):
        http_client.get_json("https://gateway.example/health", timeout=1)

    monkeypatch.setattr(http_client, "_request", lambda *_args, **_kwargs: (200, b"[]"))
    with pytest.raises(http_client.HttpClientError, match="JSON object"):
        http_client.post_json("https://gateway.example/v1", {}, headers={}, timeout=1)

    monkeypatch.setattr(http_client, "_request", lambda *_args, **_kwargs: (200, b"{}"))
    with pytest.raises(http_client.HttpClientError, match="JSON array"):
        http_client.get_json_list("https://gateway.example/items", timeout=1)


@pytest.mark.parametrize(
    "helper",
    [http_client.post_json, http_client.post_form, http_client.get_json, http_client.get_json_list],
)
def test_json_helpers_raise_on_http_errors(monkeypatch: pytest.MonkeyPatch, helper) -> None:
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
        return 200, b"{}" if kwargs["headers"].get("content-type") != "application/json" else b"{}"

    monkeypatch.setattr(http_client, "_request", request)
    assert http_client.get_json("https://gateway.example", timeout=1) == {}
    assert http_client.post_form("https://gateway.example", {}, timeout=1) == {}
    assert len(calls) == 2


def test_dropped_before_response_transport_is_retried_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A connection the path reaped before ANY response arrived is safe to
    retry (no result was produced or consumed); the observed failure was a
    long-silent judge call dropped by an intermediary port-forward.
    """
    import http.client as stdlib_http

    attempts: list[int] = []

    def flaky_once(*args, **kwargs):
        attempts.append(1)
        if len(attempts) < 2:
            raise stdlib_http.RemoteDisconnected("closed without response")
        return 200, b"{}"

    monkeypatch.setattr(http_client, "_request_once", flaky_once)
    monkeypatch.setattr(http_client.time, "sleep", lambda _s: None)
    assert http_client.post_json(
        "https://gateway.example/endpoint", {}, headers={}, timeout=1
    ) == {}
    assert len(attempts) == 2


def test_transport_retries_are_bounded_and_reraise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts: list[int] = []

    def always_reset(*args, **kwargs):
        attempts.append(1)
        raise ConnectionResetError("reset")

    monkeypatch.setattr(http_client, "_request_once", always_reset)
    monkeypatch.setattr(http_client.time, "sleep", lambda _s: None)
    with pytest.raises(ConnectionResetError):
        http_client.post_json(
            "https://gateway.example/endpoint", {}, headers={}, timeout=1
        )
    assert len(attempts) == 3


def test_http_error_statuses_are_never_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTP >= 400 is a definitive answer, not a transport accident."""
    attempts: list[int] = []

    def definitive(*args, **kwargs):
        attempts.append(1)
        return 500, b"{}"

    monkeypatch.setattr(http_client, "_request_once", definitive)
    with pytest.raises(http_client.HttpClientError, match="HTTP 500"):
        http_client.post_json(
            "https://gateway.example/endpoint", {}, headers={}, timeout=1
        )
    assert len(attempts) == 1
