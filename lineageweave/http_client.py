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


class HttpClientError(RuntimeError):
    """The remote endpoint returned a non-success status or invalid JSON."""


def _request(
    method: str,
    url: str,
    *,
    body: bytes | None,
    headers: dict[str, str],
    timeout: float,
) -> tuple[int, bytes]:
    """Implement the _request operation for this channel."""
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(f"refusing non-http(s) URL scheme: {parsed.scheme!r}")
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
    connection = http.client.HTTPConnection(parsed.hostname, port, timeout=timeout)

    try:
        if parsed.scheme == "https":
            connection.connect()
            if connection.sock is None:
                raise HttpClientError(f"no socket after connect to {parsed.hostname}")
            connection.sock = _SSL_CONTEXT.wrap_socket(
                connection.sock, server_hostname=parsed.hostname
            )
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        length_header = response.getheader("Content-Length")
        raw = response.read(int(length_header)) if length_header is not None else response.read()
        return response.status, raw
    finally:
        connection.close()


def _decode_json(raw: bytes, hostname: str) -> object:
    """Implement the _decode_json operation for this channel."""
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HttpClientError(f"non-JSON response from {hostname}") from exc


def _decode_json_object(raw: bytes, hostname: str) -> dict:
    """Implement the _decode_json_object operation for this channel."""
    decoded = _decode_json(raw, hostname)
    if not isinstance(decoded, dict):
        raise HttpClientError(f"JSON object expected from {hostname}")
    return decoded


def _decode_json_list(raw: bytes, hostname: str) -> list:
    """Implement the _decode_json_list operation for this channel."""
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
            body=json.dumps(request_payload).encode("utf-8"),
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
        headers={"content-type": "application/x-www-form-urlencoded", **(headers or {})},
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
):
    """GET ``url`` under one HTTP span and inject the active W3C context."""
    hostname = urlparse(url).hostname or url
    request_headers = dict(headers or {})
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
            "GET", url, body=None, headers=request_headers, timeout=timeout
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
    service_peer_name: str = "contextual-orchestrator",
) -> dict:
    """GET ``url`` and return the decoded JSON object.

    Raises:
        ValueError: ``url`` is not an ``http`` / ``https`` URL with a host.
        HttpClientError: the server responded with HTTP >= 400 or non-JSON.
    """
    return _traced_get_json(
        url,
        headers=headers,
        timeout=timeout,
        decoder=_decode_json_object,
        span_name="lineageweave.http.get_json",
        service_peer_name=service_peer_name,
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
