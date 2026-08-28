from __future__ import annotations

import json

import pytest

from lineageweave import http_client
from lineageweave.llm_context import use_llm_metadata


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


@pytest.mark.parametrize("raw", [b"not-json", b"\xff"])
def test_json_helpers_reject_non_json_and_wrong_shapes(
    monkeypatch: pytest.MonkeyPatch, raw: bytes
) -> None:
    monkeypatch.setattr(http_client, "_request", lambda *_args, **_kwargs: (200, raw))
    with pytest.raises(http_client.HttpClientError, match="non-JSON") as error:
        http_client.get_json("https://gateway.example/health", timeout=1)
    assert isinstance(error.value.__cause__, (UnicodeDecodeError, http_client.json.JSONDecodeError))

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
    "body",
    [
        None,
        {"error": "provider secret response"},
        {"choices": []},
        {"choices": ["not-an-object"]},
        {"choices": [{"message": "not-an-object"}]},
        {"choices": [{"message": {"content": ""}}]},
    ],
)
def test_chat_completion_content_rejects_malformed_provider_envelopes(body: object) -> None:
    """Malformed provider bodies produce stable errors without response reprs."""
    with pytest.raises((TypeError, ValueError)) as captured:
        http_client.chat_completion_content(body)

    assert "provider secret" not in str(captured.value)


def test_chat_completion_content_returns_admitted_text() -> None:
    """A well-formed provider envelope exposes only its text content."""
    assert (
        http_client.chat_completion_content(
            {"choices": [{"message": {"content": "synthetic result"}}]}
        )
        == "synthetic result"
    )


def test_response_media_type_treats_a_missing_header_as_unavailable() -> None:
    """An omitted response type is distinct from an admitted media type."""

    class HeaderlessResponse:
        """Return no value for the requested response header."""

        @staticmethod
        def getheader(name: str) -> None:
            assert name == "Content-Type"

    assert (
        http_client._response_media_type(HeaderlessResponse())  # type: ignore[arg-type]
        == ""
    )


def test_https_request_rejects_a_connection_without_a_socket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A connector that yields no TLS socket fails closed before a request."""
    closed = False

    class SocketlessConnection:
        """Model an unsuccessful synthetic connection without provider data."""

        sock = None

        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def connect(self) -> None:
            pass

        def close(self) -> None:
            nonlocal closed
            closed = True

    monkeypatch.setattr(http_client.http.client, "HTTPConnection", SocketlessConnection)

    with pytest.raises(http_client.HttpClientError, match="no socket after connect"):
        http_client._request(
            "GET",
            "https://gateway.example/health",
            body=None,
            headers={},
            timeout=1,
        )

    assert closed is True


def test_post_json_rejects_non_object_metadata_before_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post provenance cannot be merged into a malformed metadata value."""
    requested = False

    def unexpected_request(*_args: object, **_kwargs: object) -> tuple[int, bytes]:
        nonlocal requested
        requested = True
        return 200, b"{}"

    monkeypatch.setattr(http_client, "_request", unexpected_request)
    with (
        use_llm_metadata({"lineageweave_post_id": "synthetic-post"}),
        pytest.raises(ValueError, match="metadata must be an object"),
    ):
        http_client.post_json(
            "https://gateway.example/v1/chat/completions",
            {"metadata": "not-an-object"},
            headers={},
            timeout=1,
        )

    assert requested is False


def test_post_json_adds_context_metadata_when_payload_omits_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post provenance is carried when the request has no metadata object."""
    captured_body = b""

    def capture_request(*_args: object, **kwargs: object) -> tuple[int, bytes]:
        nonlocal captured_body
        captured_body = kwargs["body"]  # type: ignore[assignment]
        return 200, b"{}"

    monkeypatch.setattr(http_client, "_request", capture_request)
    with use_llm_metadata({"lineageweave_post_id": "synthetic-post"}):
        assert (
            http_client.post_json(
                "https://gateway.example/v1/chat/completions",
                {"messages": []},
                headers={},
                timeout=1,
            )
            == {}
        )

    assert b'"lineageweave_post_id": "synthetic-post"' in captured_body


@pytest.mark.parametrize(
    ("status", "error_code"),
    [(429, "rate_limit_exceeded"), (503, "no_viable_agent")],
)
def test_post_json_exposes_only_validated_admission_deferral(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    error_code: str,
) -> None:
    """The exact bounded retry contract becomes a typed control signal."""

    def deferred_request(*_args: object, **kwargs: object) -> tuple[int, bytes]:
        kwargs["response_control_headers"]["retry-after"] = "30"
        return (
            status,
            json.dumps({
                "error": {
                    "code": error_code,
                    "detail": {"retry_after_seconds": 30},
                }
            }).encode("utf-8"),
        )

    monkeypatch.setattr(http_client, "_request", deferred_request)
    with pytest.raises(http_client.HttpAdmissionDeferred) as captured:
        http_client.post_json(
            "https://gateway.example/v1/chat/completions",
            {},
            headers={},
            timeout=1,
        )

    assert captured.value.retry_after_seconds == 30
    assert error_code not in str(captured.value)


@pytest.mark.parametrize(
    ("status", "error_code"),
    [(429, "rate_limit_exceeded"), (503, "no_viable_agent")],
)
def test_post_json_rejects_mismatched_admission_delay(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    error_code: str,
) -> None:
    """Conflicting header/body delays remain an ordinary unavailable response."""

    def mismatched_request(*_args: object, **kwargs: object) -> tuple[int, bytes]:
        kwargs["response_control_headers"]["retry-after"] = "31"
        return (
            status,
            json.dumps({
                "error": {
                    "code": error_code,
                    "detail": {"retry_after_seconds": 30},
                }
            }).encode("utf-8"),
        )

    monkeypatch.setattr(http_client, "_request", mismatched_request)
    with pytest.raises(http_client.HttpClientError, match=f"HTTP {status}") as captured:
        http_client.post_json(
            "https://gateway.example/v1/chat/completions",
            {},
            headers={},
            timeout=1,
        )

    assert not isinstance(captured.value, http_client.HttpAdmissionDeferred)


@pytest.mark.parametrize(
    ("status", "error_code"),
    [(429, "rate_limit_exceeded"), (503, "no_viable_agent")],
)
@pytest.mark.parametrize(
    ("retry_after", "detail_seconds"),
    [(None, 30), ("30", None), ("0", 0), ("30", True), ("+30", 30)],
)
def test_post_json_rejects_missing_or_malformed_admission_delay(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    error_code: str,
    retry_after: str | None,
    detail_seconds: object,
) -> None:
    """Incomplete or non-canonical admission controls fail closed."""

    def malformed_request(*_args: object, **kwargs: object) -> tuple[int, bytes]:
        if retry_after is not None:
            kwargs["response_control_headers"]["retry-after"] = retry_after
        return (
            status,
            json.dumps({
                "error": {
                    "code": error_code,
                    "detail": {"retry_after_seconds": detail_seconds},
                }
            }).encode("utf-8"),
        )

    monkeypatch.setattr(http_client, "_request", malformed_request)
    with pytest.raises(http_client.HttpClientError, match=f"HTTP {status}") as captured:
        http_client.post_json(
            "https://gateway.example/v1/chat/completions",
            {},
            headers={},
            timeout=1,
        )

    assert not isinstance(captured.value, http_client.HttpAdmissionDeferred)


def test_request_preserves_the_url_query_in_the_http_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cursor parameters remain part of the bounded projection request."""
    requested_path = ""

    class SyntheticResponse:
        """Serve one bounded JSON object without a network dependency."""

        status = 200

        @staticmethod
        def getheader(name: str) -> str | None:
            assert name == "Content-Length"
            return "2"

        @staticmethod
        def read(amount: int | None = None) -> bytes:
            assert amount == 2
            return b"{}"

    class SyntheticConnection:
        """Capture the exact request target for a synthetic HTTP request."""

        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def request(
            self,
            _method: str,
            path: str,
            *,
            body: bytes | None,
            headers: dict[str, str],
        ) -> None:
            del body, headers
            nonlocal requested_path
            requested_path = path

        @staticmethod
        def getresponse() -> SyntheticResponse:
            return SyntheticResponse()

        @staticmethod
        def close() -> None:
            pass

    monkeypatch.setattr(http_client.http.client, "HTTPConnection", SyntheticConnection)

    assert http_client._request(
        "GET",
        "http://gateway.example/events?cursor=synthetic-token",
        body=None,
        headers={},
        timeout=1,
    ) == (200, b"{}")
    assert requested_path == "/events?cursor=synthetic-token"


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
        return 200, b"[]" if str(args[1]).endswith("/items") else b"{}"

    monkeypatch.setattr(http_client, "_request", request)
    assert http_client.get_json("https://gateway.example", timeout=1) == {}
    assert http_client.post_form(
        "https://gateway.example",
        {},
        timeout=1,
    ) == {}
    assert http_client.get_json_list(
        "https://gateway.example/items",
        timeout=1,
    ) == []
    assert len(calls) == 3


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
