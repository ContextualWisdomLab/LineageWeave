"""Operator-configured JSON HTTP POST with an http(s)-only scheme allowlist.

The embedding, adjudication, and vision clients all talk to an
operator-configured OpenAI-compatible endpoint. ``urllib.request.urlopen``
accepts ``file://`` URLs, so a dynamic base URL would trip both the real
file-read concern and Semgrep's ``dynamic-urllib-use-detected`` rule.
This helper parses the URL, refuses any scheme other than ``http`` /
``https``, and posts via ``http.client`` so the request never goes through
``urlopen``.
"""

from __future__ import annotations

import http.client
import json
import ssl
from urllib.parse import urlparse

import certifi

# Some interpreter distributions don't reliably inherit the OS trust store.
# Pointing at certifi keeps full chain validation without weakening TLS.
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
_ALLOWED_SCHEMES = frozenset({"http", "https"})


class HttpClientError(RuntimeError):
    """The remote endpoint returned a non-success status or invalid JSON."""


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
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(f"refusing non-http(s) URL scheme: {parsed.scheme!r}")
    if not parsed.hostname:
        raise ValueError("URL is missing a hostname")

    body = json.dumps(payload).encode("utf-8")
    request_headers = {"content-type": "application/json", **headers}
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    if parsed.scheme == "https":
        connection: http.client.HTTPConnection = http.client.HTTPSConnection(
            parsed.hostname, parsed.port, timeout=timeout, context=_SSL_CONTEXT
        )
    else:
        connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=timeout)

    try:
        connection.request("POST", path, body=body, headers=request_headers)
        response = connection.getresponse()
        length_header = response.getheader("Content-Length")
        raw = response.read(int(length_header)) if length_header is not None else response.read()
        if response.status >= 400:
            raise HttpClientError(f"HTTP {response.status} from {parsed.hostname}")
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HttpClientError(f"non-JSON response from {parsed.hostname}") from exc
        if not isinstance(decoded, dict):
            raise HttpClientError(f"JSON object expected from {parsed.hostname}")
        return decoded
    finally:
        connection.close()
