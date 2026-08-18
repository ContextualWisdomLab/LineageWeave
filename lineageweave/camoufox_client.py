"""Consume an already-running Camoufox fetch port. Do not plant a server.

Same missing-channel discipline as Orgmetra and Searxng: unset
``CAMOUFOX_BASE_URL`` keeps the client unavailable and never fabricates
page text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote, urlparse

from .http_client import get_json


@dataclass(frozen=True)
class FetchedPage:
    """HTML already fetched by the operator's Camoufox. No invented body."""

    url: str
    title: str
    body: str


class CamoufoxClient(Protocol):
    """Fetches one URL through an existing Camoufox port."""

    available: bool

    def fetch_page(self, url: str) -> FetchedPage:
        raise NotImplementedError


class NullCamoufoxClient:
    """No Camoufox port configured -- the fetch channel is skipped."""

    available = False

    def fetch_page(self, url: str) -> FetchedPage:
        raise RuntimeError("NullCamoufoxClient has no fetch channel; check .available first")


class HttpCamoufoxClient:
    """GET ``{base}/fetch?url=`` on an operator-configured Camoufox port."""

    available = True

    def __init__(self, base_url: str, *, timeout: float = 30.0) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError(f"unsupported Camoufox base URL scheme: {parsed.scheme or 'missing'}")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def fetch_page(self, url: str) -> FetchedPage:
        body = get_json(
            f"{self._base_url}/fetch?url={quote(url, safe='')}",
            timeout=self._timeout,
        )
        title = str(body.get("title") or "").strip()
        text = str(body.get("body") or "").strip()
        return FetchedPage(url=url, title=title, body=text)


def build_camoufox_client(base_url: str) -> CamoufoxClient:
    """Null when unset. Never plants a Camoufox process."""
    cleaned = base_url.strip()
    if not cleaned:
        return NullCamoufoxClient()
    return HttpCamoufoxClient(cleaned)
