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
from urllib.parse import urlencode, urlparse

import certifi

from .llm_context import current_llm_metadata

# Some interpreter distributions don't reliably inherit the OS trust store.
# Pointing at certifi keeps full chain validation without weakening TLS.
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
_ALLOWED_SCHEMES = frozenset({"http", "https"})


class HttpClientError(RuntimeError):
    """The remote endpoint returned a non-success status or invalid JSON."""


def _validated_response_limit(value: int | None) -> int | None:
    """Return a positive byte limit or reject ambiguous numeric values."""

    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("maximum_response_bytes must be a positive integer")
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


def _request(
    method: str,
    url: str,
    *,
    body: bytes | None,
    headers: dict[str, str],
    timeout: float,
    maximum_response_bytes: int | None = None,
) -> tuple[int, bytes]:
    """Perform one bounded HTTP(S) request and return status plus raw bytes."""

    limit = _validated_response_limit(maximum_response_bytes)
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
        raw = _read_response_body(
            response,
            maximum_response_bytes=limit,
        )
        return response.status, raw
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
) -> dict:
    """POST ``payload`` as JSON to ``url`` and return the decoded object.

    Raises:
        ValueError: ``url`` is not an ``http`` / ``https`` URL with a host.
        HttpClientError: the server responded with HTTP >= 400 or non-JSON.
    """

    request_payload = payload
    request_metadata = current_llm_metadata()
    if request_metadata:
        request_payload = dict(payload)
        existing_metadata = request_payload.get("metadata")
        if existing_metadata is None:
            request_payload["metadata"] = request_metadata
        elif isinstance(existing_metadata, dict):
            request_payload["metadata"] = {
                **existing_metadata,
                **request_metadata,
            }
        else:
            raise ValueError("metadata must be an object")
    status, raw = _request(
        "POST",
        url,
        body=json.dumps(request_payload).encode("utf-8"),
        headers={"content-type": "application/json", **headers},
        timeout=timeout,
    )
    hostname = urlparse(url).hostname or url
    if status >= 400:
        raise HttpClientError(f"HTTP {status} from {hostname}")
    return _decode_json_object(raw, hostname)


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


def get_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float,
    maximum_response_bytes: int | None = None,
) -> dict:
    """GET ``url`` and return a decoded JSON object.

    Args:
        url: Operator-configured HTTP(S) endpoint.
        headers: Optional request headers.
        timeout: Socket timeout in seconds.
        maximum_response_bytes: Optional strict response-body byte ceiling.

    Raises:
        ValueError: The URL or byte limit is invalid.
        HttpClientError: The response is too large, HTTP >= 400, or non-JSON.
    """

    status, raw = _request(
        "GET",
        url,
        body=None,
        headers=headers or {},
        timeout=timeout,
        maximum_response_bytes=maximum_response_bytes,
    )
    hostname = urlparse(url).hostname or url
    if status >= 400:
        raise HttpClientError(f"HTTP {status} from {hostname}")
    return _decode_json_object(raw, hostname)


def get_json_list(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float,
) -> list:
    """GET ``url`` and return the decoded JSON array.

    Used by the demo seeder to read Keycloak's admin users list (a JSON
    array, not an object). Same scheme allowlist as ``get_json``.

    Raises:
        ValueError: ``url`` is not an ``http`` / ``https`` URL with a host.
        HttpClientError: the server responded with HTTP >= 400 or non-array JSON.
    """

    status, raw = _request(
        "GET",
        url,
        body=None,
        headers=headers or {},
        timeout=timeout,
    )
    hostname = urlparse(url).hostname or url
    if status >= 400:
        raise HttpClientError(f"HTTP {status} from {hostname}")
    return _decode_json_list(raw, hostname)
