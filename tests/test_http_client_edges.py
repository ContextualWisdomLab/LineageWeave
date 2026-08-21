from __future__ import annotations

import pytest

import lineageweave.http_client as http_client


@pytest.mark.parametrize("raw", [b"not-json", b"\xff"])
def test_json_helpers_reject_non_json_and_wrong_shapes(
    monkeypatch: pytest.MonkeyPatch, raw: bytes
) -> None:
    monkeypatch.setattr(http_client, "_request", lambda *_args, **_kwargs: (200, raw))
    with pytest.raises(http_client.HttpClientError, match="non-JSON") as error:
        http_client.get_json("https://gateway.example/health", timeout=1)
    assert error.value.__cause__ is None
    assert error.value.__context__ is None

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
