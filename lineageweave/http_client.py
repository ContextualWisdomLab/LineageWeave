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


def _request(
    method: str,
    url: str,
    *,
    body: bytes | None,
    headers: dict[str, str],
    timeout: float,
    maximum_response_bytes: int | None = None,
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
        if maximum_response_bytes is not None:
            if maximum_response_bytes < 1:
                raise ValueError("maximum_response_bytes must be positive")
            raw = response.read(maximum_response_bytes + 1)
            if len(raw) > maximum_response_bytes:
                raise HttpClientError(
                    f"response exceeds {maximum_response_bytes} bytes"
                )
        else:
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
    include_llm_metadata: bool = True,
    maximum_response_bytes: int | None = None,
) -> dict:
    """POST ``payload`` as JSON to ``url`` and return the decoded object.

    ``include_llm_metadata`` preserves contextual-orchestrator enrichment by
    default. Closed non-LLM wire contracts must set it to ``False`` so an active
    LLM context cannot add an unpublished ``metadata`` member.
    ``maximum_response_bytes`` bounds reads for strict remote contracts.

    Raises:
        ValueError: ``url`` is not an ``http`` / ``https`` URL with a host.
        HttpClientError: the server responded with HTTP >= 400 or non-JSON.
    """
    request_payload = payload
    request_metadata = current_llm_metadata() if include_llm_metadata else None
    if request_metadata:
        request_payload = dict(payload)
        existing_metadata = request_payload.get("metadata")
        if existing_metadata is None:
            request_payload["metadata"] = request_metadata
        elif isinstance(existing_metadata, dict):
            request_payload["metadata"] = {**existing_metadata, **request_metadata}
        else:
            raise ValueError("metadata must be an object")
    request_options = {
        "body": json.dumps(request_payload).encode("utf-8"),
        "headers": {"content-type": "application/json", **headers},
        "timeout": timeout,
    }
    if maximum_response_bytes is not None:
        request_options["maximum_response_bytes"] = maximum_response_bytes
    status, raw = _request("POST", url, **request_options)
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
        headers={"content-type": "application/x-www-form-urlencoded", **(headers or {})},
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
) -> dict:
    """GET ``url`` and return the decoded JSON object.

    Raises:
        ValueError: ``url`` is not an ``http`` / ``https`` URL with a host.
        HttpClientError: the server responded with HTTP >= 400 or non-JSON.
    """
    status, raw = _request("GET", url, body=None, headers=headers or {}, timeout=timeout)
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
    status, raw = _request("GET", url, body=None, headers=headers or {}, timeout=timeout)
    hostname = urlparse(url).hostname or url
    if status >= 400:
        raise HttpClientError(f"HTTP {status} from {hostname}")
    return _decode_json_list(raw, hostname)
