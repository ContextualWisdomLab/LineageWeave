"""SSRF-safe retrieval of a single public HTTP(S) resource.

LineageWeave may fetch a cited public page only after the URL and every
resolved address have been classified as globally reachable. Redirects are
refused so a public first hop cannot bounce into a private target. This module
does not search, judge, or persist; callers own those steps.
"""

from __future__ import annotations

import html.parser
import http.client
import ipaddress
import socket
import ssl
from dataclasses import dataclass
from urllib.parse import urlparse

import certifi

from .http_client import HttpClientError

_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
_ALLOWED_SCHEMES = frozenset({"http", "https"})
_SEARCH_HOST_MARKERS = (
    "google.",
    "bing.",
    "yahoo.",
    "duckduckgo.",
    "baidu.",
    "yandex.",
    "searx",
)
_BLOCKED_HOST_SUFFIXES = (
    ".local",
    ".localhost",
    ".internal",
    ".intranet",
    ".corp",
    ".lan",
    ".home",
    ".localdomain",
)
_BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "metadata",
    }
)
_DEFAULT_PORTS = {"http": 80, "https": 443}
_TEXT_MEDIA_TYPES = frozenset({"text/html", "text/plain", "application/xhtml+xml"})
DEFAULT_MAXIMUM_RESPONSE_BYTES = 200_000
DEFAULT_MAXIMUM_TEXT_CHARS = 8_000


class PublicTargetRejected(ValueError):
    """The URL is not a fetchable public target."""


class PublicResourceUnavailable(HttpClientError):
    """The public target could not be retrieved without following a redirect."""


@dataclass(frozen=True)
class PublicTarget:
    """One classified public HTTP(S) target after host and scheme checks."""

    scheme: str
    hostname: str
    port: int
    request_path: str
    original_url: str

    @property
    def host_header(self) -> str:
        """Host header that preserves the original public name."""

        default_port = _DEFAULT_PORTS[self.scheme]
        if self.port == default_port:
            return self.hostname
        return f"{self.hostname}:{self.port}"


@dataclass(frozen=True)
class PublicResource:
    """Bounded visible text retrieved from one public target."""

    url: str
    title: str
    excerpt_text: str
    media_type: str


class _VisibleTextParser(html.parser.HTMLParser):
    """Collect visible HTML text while dropping script, style, and tags."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._title_chunks: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Ignore non-visible elements and record a document title opener."""

        normalized = tag.lower()
        if normalized in {"script", "style", "noscript", "template"}:
            self._skip_depth += 1
            return
        if normalized == "title" and self._skip_depth == 0:
            self._in_title = True
        if normalized in {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4"}:
            self._chunks.append(" ")

    def handle_endtag(self, tag: str) -> None:
        """Close skipped regions and the document title."""

        normalized = tag.lower()
        if normalized in {"script", "style", "noscript", "template"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if normalized == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        """Keep visible text nodes only."""

        if self._skip_depth:
            return
        if self._in_title:
            self._title_chunks.append(data)
            return
        self._chunks.append(data)

    def visible_text(self) -> str:
        """Return collapsed visible body text."""

        return " ".join("".join(self._chunks).split())

    def document_title(self) -> str:
        """Return collapsed document title text."""

        return " ".join("".join(self._title_chunks).split())


def is_public_ip(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Return True when ``address`` is globally reachable unicast."""

    mapped = address.ipv4_mapped if address.version == 6 else None
    candidate = mapped if mapped is not None else address
    return bool(candidate.is_global) and not candidate.is_multicast


def classify_public_target(url: str) -> PublicTarget | None:
    """Return a public HTTP(S) target, or ``None`` when the URL is unsafe."""

    if not isinstance(url, str) or not url.strip():
        return None
    parsed = urlparse(url.strip())
    if parsed.scheme not in _ALLOWED_SCHEMES:
        return None
    if parsed.username is not None or parsed.password is not None:
        return None
    hostname = parsed.hostname
    if not hostname:
        return None
    host = hostname.casefold().rstrip(".")
    if host in _BLOCKED_HOSTS or any(host.endswith(suffix) for suffix in _BLOCKED_HOST_SUFFIXES):
        return None
    if any(marker in host for marker in _SEARCH_HOST_MARKERS):
        return None
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None and not is_public_ip(literal):
        return None
    default_port = _DEFAULT_PORTS[parsed.scheme]
    port = parsed.port if parsed.port is not None else default_port
    if port <= 0 or port > 65535:
        return None
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    return PublicTarget(
        scheme=parsed.scheme,
        hostname=host,
        port=port,
        request_path=path,
        original_url=url.strip()[:2000],
    )


def resolve_public_addresses(hostname: str) -> tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, ...]:
    """Resolve ``hostname`` and keep only globally reachable addresses."""

    try:
        records = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise PublicTargetRejected("public target hostname could not be resolved") from exc
    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for record in records:
        sockaddr = record[4]
        if not sockaddr:
            continue
        try:
            address = ipaddress.ip_address(sockaddr[0])
        except ValueError:
            continue
        if not is_public_ip(address):
            raise PublicTargetRejected("public target resolved to a non-global address")
        if address not in addresses:
            addresses.append(address)
    if not addresses:
        raise PublicTargetRejected("public target hostname could not be resolved")
    return tuple(addresses)


def extract_visible_text(raw: bytes, media_type: str) -> tuple[str, str]:
    """Return ``(title, excerpt)`` from a bounded public body."""

    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        decoded = raw.decode("utf-8", errors="replace")
    if media_type in {"text/html", "application/xhtml+xml"}:
        parser = _VisibleTextParser()
        parser.feed(decoded)
        parser.close()
        title = parser.document_title()[:300]
        excerpt = parser.visible_text()[:DEFAULT_MAXIMUM_TEXT_CHARS]
        return title, excerpt
    excerpt = " ".join(decoded.split())[:DEFAULT_MAXIMUM_TEXT_CHARS]
    return "", excerpt


def _response_media_type(response: http.client.HTTPResponse) -> str:
    header = response.getheader("Content-Type")
    if header is None:
        return ""
    return header.split(";", 1)[0].strip().lower()


def retrieve_public_target(
    target: PublicTarget,
    connect_address: ipaddress.IPv4Address | ipaddress.IPv6Address,
    *,
    timeout: float = 10.0,
    maximum_response_bytes: int = DEFAULT_MAXIMUM_RESPONSE_BYTES,
) -> PublicResource:
    """GET one already-classified target without following redirects."""

    if maximum_response_bytes <= 0:
        raise ValueError("maximum_response_bytes must be a positive integer")
    connect_host = str(connect_address)
    if connect_address.version == 6:
        connect_host = f"[{connect_host}]"
    connection = http.client.HTTPConnection(connect_host, target.port, timeout=timeout)
    try:
        try:
            connection.connect()
            if connection.sock is None:
                raise PublicResourceUnavailable("public target transport unavailable")
            if target.scheme == "https":
                connection.sock = _SSL_CONTEXT.wrap_socket(
                    connection.sock,
                    server_hostname=target.hostname,
                )
            connection.request(
                "GET",
                target.request_path,
                headers={
                    "host": target.host_header,
                    "accept": "text/html, text/plain;q=0.9",
                    "user-agent": "LineageWeave-source-research/2.19",
                },
            )
            response = connection.getresponse()
        except (OSError, ValueError, http.client.HTTPException) as exc:
            raise PublicResourceUnavailable("public target transport unavailable") from exc
        if 300 <= response.status < 400:
            raise PublicTargetRejected("public target redirects are not followed")
        if response.status >= 400:
            raise PublicResourceUnavailable("public target returned an error status")
        media_type = _response_media_type(response)
        if media_type and media_type not in _TEXT_MEDIA_TYPES:
            raise PublicTargetRejected("public target media type is not retrievable text")
        length_header = response.getheader("Content-Length")
        if length_header is not None:
            try:
                declared_length = int(length_header)
            except ValueError as exc:
                raise PublicResourceUnavailable("public target declared an invalid length") from exc
            if declared_length < 0 or declared_length > maximum_response_bytes:
                raise PublicTargetRejected("public target exceeds the retrieval byte limit")
        raw = response.read(maximum_response_bytes + 1)
        if len(raw) > maximum_response_bytes:
            raise PublicTargetRejected("public target exceeds the retrieval byte limit")
    finally:
        connection.close()
    title, excerpt = extract_visible_text(raw, media_type or "text/plain")
    if not excerpt:
        raise PublicTargetRejected("public target contained no visible text")
    return PublicResource(
        url=target.original_url,
        title=title or target.hostname,
        excerpt_text=excerpt,
        media_type=media_type or "text/plain",
    )


def fetch_public_resource(
    url: str,
    *,
    timeout: float = 10.0,
    maximum_response_bytes: int = DEFAULT_MAXIMUM_RESPONSE_BYTES,
) -> PublicResource:
    """Classify, resolve, and retrieve one public URL with redirects disabled."""

    target = classify_public_target(url)
    if target is None:
        raise PublicTargetRejected("url is not a public HTTP(S) target")
    addresses = resolve_public_addresses(target.hostname)
    return retrieve_public_target(
        target,
        addresses[0],
        timeout=timeout,
        maximum_response_bytes=maximum_response_bytes,
    )


__all__ = [
    "DEFAULT_MAXIMUM_RESPONSE_BYTES",
    "DEFAULT_MAXIMUM_TEXT_CHARS",
    "PublicResource",
    "PublicResourceUnavailable",
    "PublicTarget",
    "PublicTargetRejected",
    "classify_public_target",
    "extract_visible_text",
    "fetch_public_resource",
    "is_public_ip",
    "resolve_public_addresses",
    "retrieve_public_target",
]
