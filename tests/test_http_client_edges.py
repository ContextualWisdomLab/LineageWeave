from __future__ import annotations

import pytest

import lineageweave.http_client as http_client
from lineageweave.http_client import HttpClientError, get_json, get_json_list, post_form, post_json


def test_json_helpers_reject_non_json_and_wrong_shapes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(http_client, "_request", lambda *_args, **_kwargs: (200, b"not-json"))
    with pytest.raises(HttpClientError, match="non-JSON"):
        get_json("https://gateway.example/health", timeout=1)

    monkeypatch.setattr(http_client, "_request", lambda *_args, **_kwargs: (200, b"[]"))
    with pytest.raises(HttpClientError, match="JSON object"):
        post_json("https://gateway.example/v1", {}, headers={}, timeout=1)

    monkeypatch.setattr(http_client, "_request", lambda *_args, **_kwargs: (200, b"{}"))
    with pytest.raises(HttpClientError, match="JSON array"):
        get_json_list("https://gateway.example/items", timeout=1)


@pytest.mark.parametrize("helper", [post_json, post_form, get_json, get_json_list])
def test_json_helpers_raise_on_http_errors(monkeypatch: pytest.MonkeyPatch, helper) -> None:
    monkeypatch.setattr(http_client, "_request", lambda *_args, **_kwargs: (503, b"{}"))
    kwargs = {"timeout": 1}
    if helper is post_json:
        kwargs.update(payload={}, headers={})
    elif helper is post_form:
        kwargs.update(fields={}, headers={})
    with pytest.raises(HttpClientError, match="HTTP 503"):
        if helper in (post_json, post_form):
            helper("https://gateway.example/endpoint", **kwargs)
        else:
            helper("https://gateway.example/endpoint", **kwargs)


def test_json_helpers_accept_optional_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, ...]] = []

    def request(*args, **kwargs):
        calls.append((args, kwargs))
        return 200, b"{}" if kwargs["headers"].get("content-type") != "application/json" else b"{}"

    monkeypatch.setattr(http_client, "_request", request)
    assert get_json("https://gateway.example", timeout=1) == {}
    assert post_form("https://gateway.example", {}, timeout=1) == {}
    assert len(calls) == 2
