from __future__ import annotations

import pytest

import lineageweave.http_client as http_client


class _ResponseStub:
    def __init__(self, body: bytes, content_length: str | None) -> None:
        self._body = body
        self._content_length = content_length

    def getheader(self, name: str) -> str | None:
        assert name == "Content-Length"
        return self._content_length

    def read(self, amount: int | None = None) -> bytes:
        if amount is None:
            return self._body
        return self._body[:amount]


def test_json_helpers_reject_non_json_and_wrong_shapes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        http_client,
        "_request",
        lambda *_args, **_kwargs: (200, b"not-json"),
    )
    with pytest.raises(http_client.HttpClientError, match="non-JSON"):
        http_client.get_json("https://gateway.example/health", timeout=1)

    monkeypatch.setattr(
        http_client,
        "_request",
        lambda *_args, **_kwargs: (200, b"[]"),
    )
    with pytest.raises(http_client.HttpClientError, match="JSON object"):
        http_client.post_json(
            "https://gateway.example/v1",
            {},
            headers={},
            timeout=1,
        )

    monkeypatch.setattr(
        http_client,
        "_request",
        lambda *_args, **_kwargs: (200, b"{}"),
    )
    with pytest.raises(http_client.HttpClientError, match="JSON array"):
        http_client.get_json_list(
            "https://gateway.example/items",
            timeout=1,
        )


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
    monkeypatch: pytest.MonkeyPatch,
    helper,
) -> None:
    monkeypatch.setattr(
        http_client,
        "_request",
        lambda *_args, **_kwargs: (503, b"{}"),
    )
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


def test_json_helpers_accept_optional_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[object, ...]] = []

    def request(*args, **kwargs):
        calls.append((args, kwargs))
        return 200, b"{}"

    monkeypatch.setattr(http_client, "_request", request)
    assert http_client.get_json("https://gateway.example", timeout=1) == {}
    assert http_client.post_form(
        "https://gateway.example",
        {},
        timeout=1,
    ) == {}
    assert len(calls) == 2


def test_response_reader_supports_bounded_and_unbounded_chunked_bodies() -> None:
    response = _ResponseStub(b"{}", None)
    assert http_client._read_response_body(
        response,  # type: ignore[arg-type]
        maximum_response_bytes=None,
    ) == b"{}"
    assert http_client._read_response_body(
        response,  # type: ignore[arg-type]
        maximum_response_bytes=8,
    ) == b"{}"


@pytest.mark.parametrize("header", ["not-a-number", "-1"])
def test_response_reader_rejects_invalid_content_length(header: str) -> None:
    response = _ResponseStub(b"{}", header)
    with pytest.raises(http_client.HttpClientError, match="Content-Length"):
        http_client._read_response_body(
            response,  # type: ignore[arg-type]
            maximum_response_bytes=8,
        )


@pytest.mark.parametrize("value", [True, 1.5, -1])
def test_response_limit_rejects_ambiguous_or_invalid_values(value: object) -> None:
    with pytest.raises(ValueError, match="maximum_response_bytes"):
        http_client._validated_response_limit(value)  # type: ignore[arg-type]
