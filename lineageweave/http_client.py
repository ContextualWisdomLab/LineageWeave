"""Operator-configured HTTP GET/POST with an http(s)-only scheme allowlist.

The embedding, adjudication, and vision clients all talk to an
operator-configured OpenAI-compatible endpoint. ``urllib.request.urlopen``
accepts ``file://`` URLs, so a dynamic base URL would trip both the real
file-read concern and Semgrep's ``dynamic-urllib-use-detected`` rule.
This helper parses the URL, refuses any scheme other than ``http`` /
``https``, posts via ``http.client.HTTPConnection``, and for ``https``
wraps the socket with a certifi-backed ``SSLContext`` so certificate
verification is explicit. The request never goes through ``urlopen``.
"""

from __future__ import annotations

import http.client
import json
import ssl
from collections.abc import Callable
from urllib.parse import urlencode, urlparse

import certifi

from .llm_context import current_llm_metadata
from .observability import current_session_id, inject_trace_context, traced

# Some interpreter distributions don't reliably inherit the OS trust store.
# Pointing at certifi keeps full chain validation without weakening TLS.
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
_ALLOWED_SCHEMES = frozenset({"http", "https"})
_SESSION_HEADER_PEERS = frozenset({"contextual-orchestrator", "tepp"})


class HttpClientError(RuntimeError):
    """The remote endpoint failed, returned a non-success status, or invalid JSON."""


def json_request_body(
    payload: dict,
    *,
    include_orchestrator_session: bool = False,
) -> bytes:
    """Serialize a JSON body with bounded post provenance when requested.

    ``session_id`` is an orchestrator transport field, so callers that only
    size or persist a provider-neutral payload retain their existing bytes.
    """
    request_payload = payload
    request_metadata = current_llm_metadata()
    if request_metadata:
        request_payload = dict(payload)
        existing_metadata = request_payload.get("metadata")
        if existing_metadata is None:
            request_payload["metadata"] = request_metadata
        elif isinstance(existing_metadata, dict):
            request_payload["metadata"] = {**existing_metadata, **request_metadata}
        else:
            raise ValueError("metadata must be an object")
        if include_orchestrator_session:
            session_id = request_metadata.get("lineageweave_post_session_id")
            if session_id:
                request_payload["session_id"] = session_id
    return json.dumps(request_payload).encode("utf-8")


def _validated_response_limit(value: int | None) -> int | None:
    """Return a positive byte limit or reject ambiguous numeric values."""

    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("maximum_response_bytes must be a positive integer")
    return value


def _validated_expected_media_type(value: str | None) -> str | None:
    """Return one exact lower-case type/subtype without parameters."""

    if value is None:
        return None
    if (
        not isinstance(value, str)
        or value != value.strip()
        or not value
        or value != value.lower()
        or ";" in value
        or value.count("/") != 1
        or any(character.isspace() for character in value)
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ValueError(
            "expected_response_media_type must be an exact lower-case type/subtype"
        )
    return value


def _read_response_body(
    response: http.client.HTTPResponse,
    *,
    maximum_response_bytes: int | None,
) -> bytes:
    """Read one response without allocating beyond an admitted byte limit."""

    limit = _validated_response_limit(maximum_response_bytes)
    length_header = response.getheader("Content-Length")
    if length_header is not None:
        try:
            declared_length = int(length_header)
        except ValueError as exc:
            raise HttpClientError("invalid Content-Length from remote endpoint") from exc
        if declared_length < 0:
            raise HttpClientError("invalid Content-Length from remote endpoint")
        if limit is not None and declared_length > limit:
            raise HttpClientError(
                f"response exceeds maximum_response_bytes={limit}"
            )
        raw = response.read(declared_length)
    elif limit is None:
        raw = response.read()
    else:
        raw = response.read(limit + 1)

    if limit is not None and len(raw) > limit:
        raise HttpClientError(
            f"response exceeds maximum_response_bytes={limit}"
        )
    return raw


def _response_media_type(response: http.client.HTTPResponse) -> str:
    """Return the normalized media type without optional parameters."""

    header = response.getheader("Content-Type")
    if header is None:
        return ""
    return header.split(";", 1)[0].strip().lower()


def chat_completion_content(body: object) -> str:
    """Extract text from a provider chat envelope without echoing its body."""
    if not isinstance(body, dict):
        raise TypeError("provider response was not an object")
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("provider response did not contain a choice")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise TypeError("provider response choice was not an object")
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise TypeError("provider response message was not an object")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise TypeError("provider response did not contain text content")
    return content


def _request(
    method: str,
    url: str,
    *,
    body: bytes | None,
    headers: dict[str, str],
    timeout: float,
    maximum_response_bytes: int | None = None,
    expected_response_media_type: str | None = None,
) -> tuple[int, bytes]:
    """Perform one bounded HTTP(S) request without exposing provider transport exception details."""

    limit = _validated_response_limit(maximum_response_bytes)
    expected_media_type = _validated_expected_media_type(
        expected_response_media_type
    )
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"refusing non-http(s) URL scheme: {parsed.scheme!r}"
        )
    if not parsed.hostname:
        raise ValueError("URL is missing a hostname")

    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    # HTTPConnection + an explicit wrap keeps TLS verification on the
    # certifi-backed context we already built. HTTPSConnection is not used:
    # Semgrep's httpsconnection-detected rule still warns about pre-3.4.3
    # defaults, which this project (requires-python >= 3.10) never hits.
    default_port = 443 if parsed.scheme == "https" else 80
    port = parsed.port if parsed.port is not None else default_port
    connection = http.client.HTTPConnection(
        parsed.hostname,
        port,
        timeout=timeout,
    )

    try:
        try:
            if parsed.scheme == "https":
                connection.connect()
                if connection.sock is None:
                    raise HttpClientError(
                        f"no socket after connect to {parsed.hostname}"
                    )
                connection.sock = _SSL_CONTEXT.wrap_socket(
                    connection.sock,
                    server_hostname=parsed.hostname,
                )
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            if (
                expected_media_type is not None
                and _response_media_type(response) != expected_media_type
            ):
                raise HttpClientError(
                    f"unexpected response media type from {parsed.hostname}"
                )
            raw = _read_response_body(
                response,
                maximum_response_bytes=limit,
            )
            return response.status, raw
        except (OSError, ValueError, http.client.HTTPException) as exc:
            # Chain internally for operator logging; the exposed
            # message stays generic/hostname-only, never the raw exception text.
            raise HttpClientError("provider transport unavailable") from exc
    finally:
        connection.close()


def _decode_json(raw: bytes, hostname: str) -> object:
    """Decode UTF-8 JSON without exposing response content in errors."""

    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HttpClientError(f"non-JSON response from {hostname}") from exc


def _decode_json_object(raw: bytes, hostname: str) -> dict:
    """Decode one JSON object and reject arrays or scalar payloads."""

    decoded = _decode_json(raw, hostname)
    if not isinstance(decoded, dict):
        raise HttpClientError(f"JSON object expected from {hostname}")
    return decoded


def _decode_json_list(raw: bytes, hostname: str) -> list:
    """Decode one JSON array and reject objects or scalar payloads."""

    decoded = _decode_json(raw, hostname)
    if not isinstance(decoded, list):
        raise HttpClientError(f"JSON array expected from {hostname}")
    return decoded


def post_json(
    url: str,
    payload: dict,
    *,
    headers: dict[str, str],
    timeout: float,
    service_peer_name: str = "contextual-orchestrator",
) -> dict:
    """POST ``payload`` as JSON to ``url`` and return the decoded object.

    Raises:
        ValueError: ``url`` is not an ``http`` / ``https`` URL with a host.
        HttpClientError: the server responded with HTTP >= 400 or non-JSON.

    ``service_peer_name`` is a bounded service name used for the request span.
    """
    hostname = urlparse(url).hostname or url
    request_headers = {"content-type": "application/json", **headers}
    session_id = current_session_id()
    if session_id:
        request_headers["x-lineageweave-session-id"] = session_id
    with traced(
        "lineageweave.http.post_json",
        {
            "http.request.method": "POST",
            "lineageweave.operation_code": "http_post_json",
            "service.peer.name": service_peer_name,
        },
    ) as span:
        inject_trace_context(request_headers)
        status, raw = _request(
            "POST",
            url,
            body=json_request_body(
                payload,
                include_orchestrator_session=(
                    service_peer_name == "contextual-orchestrator"
                ),
            ),
            headers=request_headers,
            timeout=timeout,
        )
        if span is not None:
            span.set_attribute("http.response.status_code", status)
        if status >= 400:
            if span is not None:
                span.set_attribute("error.type", str(status))
            raise HttpClientError(f"HTTP {status} from {hostname}")
        try:
            return _decode_json_object(raw, hostname)
        except HttpClientError:
            if span is not None:
                span.set_attribute("error.type", "HttpClientError")
            raise


def post_form(
    url: str,
    fields: dict[str, str],
    *,
    headers: dict[str, str] | None = None,
    timeout: float,
) -> dict:
    """POST ``application/x-www-form-urlencoded`` fields and decode JSON.

    Used by the OIDC smoke test (resource-owner password grant). Same
    scheme allowlist as ``post_json`` -- never ``urllib.request.urlopen``.
    """

    status, raw = _request(
        "POST",
        url,
        body=urlencode(fields).encode("utf-8"),
        headers={
            "content-type": "application/x-www-form-urlencoded",
            **(headers or {}),
        },
        timeout=timeout,
    )
    hostname = urlparse(url).hostname or url
    if status >= 400:
        raise HttpClientError(f"HTTP {status} from {hostname}")
    return _decode_json_object(raw, hostname)


def _traced_get_json(
    url: str,
    *,
    headers: dict[str, str] | None,
    timeout: float,
    decoder: Callable[[bytes, str], dict | list],
    span_name: str,
    service_peer_name: str,
    maximum_response_bytes: int | None = None,
    expected_response_media_type: str | None = None,
):
    """GET ``url`` under one HTTP span and inject the active W3C context."""
    hostname = urlparse(url).hostname or url
    request_headers = dict(headers or {})
    if service_peer_name in _SESSION_HEADER_PEERS:
        session_id = current_session_id()
        if session_id:
            request_headers["x-lineageweave-session-id"] = session_id
    with traced(
        span_name,
        {
            "http.request.method": "GET",
            "lineageweave.operation_code": "http_get_json",
            "service.peer.name": service_peer_name,
        },
    ) as span:
        inject_trace_context(request_headers)
        status, raw = _request(
            "GET",
            url,
            body=None,
            headers=request_headers,
            timeout=timeout,
            maximum_response_bytes=maximum_response_bytes,
            expected_response_media_type=expected_response_media_type,
        )
        if span is not None:
            span.set_attribute("http.response.status_code", status)
        if status >= 400:
            if span is not None:
                span.set_attribute("error.type", str(status))
            raise HttpClientError(f"HTTP {status} from {hostname}")
        try:
            return decoder(raw, hostname)
        except HttpClientError:
            if span is not None:
                span.set_attribute("error.type", "HttpClientError")
            raise


def get_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float,
    service_peer_name: str = "http-service",
    maximum_response_bytes: int | None = None,
    expected_response_media_type: str | None = None,
) -> dict:
    """GET ``url`` and return a decoded JSON object.

    Args:
        url: Operator-configured HTTP(S) endpoint.
        headers: Optional request headers.
        timeout: Socket timeout in seconds.
        maximum_response_bytes: Optional strict response-body byte ceiling.
        expected_response_media_type: Optional exact lower-case type/subtype.

    Raises:
        ValueError: The URL, byte limit, or expected media type is invalid.
        HttpClientError: The response is too large, has the wrong media type,
            returns HTTP >= 400, or is not a JSON object.
    """
    return _traced_get_json(
        url,
        headers=headers,
        timeout=timeout,
        decoder=_decode_json_object,
        span_name="lineageweave.http.get_json",
        service_peer_name=service_peer_name,
        maximum_response_bytes=maximum_response_bytes,
        expected_response_media_type=expected_response_media_type,
    )


def get_json_list(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float,
    service_peer_name: str = "contextual-orchestrator",
) -> list:
    """GET ``url`` and return the decoded JSON array.

    Used by the demo seeder to read Keycloak's admin users list (a JSON
    array, not an object). Same scheme allowlist as ``get_json``.

    Raises:
        ValueError: ``url`` is not an ``http`` / ``https`` URL with a host.
        HttpClientError: the server responded with HTTP >= 400 or non-array JSON.
    """
    return _traced_get_json(
        url,
        headers=headers,
        timeout=timeout,
        decoder=_decode_json_list,
        span_name="lineageweave.http.get_json_list",
        service_peer_name=service_peer_name,
    )
