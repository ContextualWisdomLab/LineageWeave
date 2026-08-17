"""Adapter for naruon's published mailbox inbox contract.

`naruon <https://github.com/ContextualWisdomLab/naruon>`_ is a web
client/control plane over customer-owned mail, not a mailbox host.
LineageWeave consumes only the published inbox envelope
(``GET /api/emails``) and never invents a thread, a subject, or a
message body.

The default transport raises :class:`NaruonNotAvailable` so a missing
naruon port is fail-closed, the same discipline as
:class:`lineageweave.tepp_client.TeppNotAvailable`. Wiring a live
HTTPS base URL is additive (``HttpNaruonTransport``), not a redesign.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from lineageweave.http_client import HttpClientError, get_json


class NaruonNotAvailable(RuntimeError):
    """Raised when the naruon mailbox port is down or unconfigured."""

    reason = "naruon_not_available"


def _no_transport() -> dict[str, Any]:
    raise NaruonNotAvailable(
        "naruon_not_available: naruon mailbox HTTP is not configured. "
        "Pass NARUON_BASE_URL or a transport= callable. Never invent a thread."
    )


@dataclass(frozen=True)
class MailboxThread:
    """Projected naruon inbox row. No message body."""

    thread_id: str
    subject: str
    reply_count: int | None = None

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "thread_id": self.thread_id,
            "subject": self.subject,
        }
        if self.reply_count is not None:
            payload["reply_count"] = self.reply_count
        return payload


@dataclass(frozen=True)
class MailboxInbox:
    """Accepted inbox projection. Empty when naruon returned no usable rows."""

    threads: tuple[MailboxThread, ...]

    def to_json(self) -> list[dict[str, Any]]:
        return [thread.to_json() for thread in self.threads]


def parse_inbox(payload: object) -> MailboxInbox:
    """Project naruon's published ``{emails: [...]}`` envelope.

    Unknown envelopes fail closed. Malformed rows are skipped rather than
    repaired. Message bodies are never copied.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("emails"), list):
        raise NaruonNotAvailable(
            "naruon_not_available: inbox envelope is not the published {emails: []} shape"
        )
    threads: list[MailboxThread] = []
    for row in payload["emails"]:
        if not isinstance(row, dict):
            continue
        subject = row.get("subject")
        thread_id = row.get("thread_id")
        if not isinstance(subject, str) or not subject.strip():
            continue
        if not isinstance(thread_id, str) or not thread_id.strip():
            continue
        reply_count = row.get("reply_count")
        if reply_count is not None and not isinstance(reply_count, int):
            reply_count = None
        threads.append(
            MailboxThread(
                thread_id=thread_id.strip(),
                subject=subject.strip(),
                reply_count=reply_count,
            )
        )
    return MailboxInbox(threads=tuple(threads))


class HttpNaruonTransport:
    """GET ``{base_url}/api/emails`` through the http(s)-only client."""

    def __init__(self, base_url: str, bearer: str = "", timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.bearer = bearer
        self.timeout = timeout

    def __call__(self) -> dict[str, Any]:
        headers: dict[str, str] = {}
        if self.bearer:
            headers["Authorization"] = f"Bearer {self.bearer}"
        try:
            payload = get_json(
                f"{self.base_url}/api/emails",
                headers=headers or None,
                timeout=self.timeout,
            )
        except (HttpClientError, OSError, TimeoutError, ValueError) as exc:
            raise NaruonNotAvailable(
                f"naruon_not_available: mailbox HTTP failed ({exc})"
            ) from exc
        if not isinstance(payload, dict):
            raise NaruonNotAvailable(
                "naruon_not_available: inbox HTTP did not return a JSON object"
            )
        return payload


def build_naruon_client(base_url: str = "", bearer: str = "") -> "NaruonClient":
    """Empty base URL keeps the default fail-closed transport."""
    if not base_url.strip():
        return NaruonClient()
    return NaruonClient(transport=HttpNaruonTransport(base_url=base_url, bearer=bearer))


class NaruonClient:
    """Lists naruon inbox threads through a pluggable transport."""

    def __init__(self, transport: Callable[[], dict[str, Any]] = _no_transport) -> None:
        self._transport = transport

    def list_inbox(self) -> MailboxInbox:
        return parse_inbox(self._transport())

    def as_api_payload(self) -> dict[str, Any]:
        """Buyer-visible mailbox status. Never invents a thread."""
        try:
            inbox = self.list_inbox()
        except NaruonNotAvailable:
            return {
                "port": "naruon",
                "status": "unavailable",
                "status_reason": NaruonNotAvailable.reason,
                "threads": [],
            }
        return {
            "port": "naruon",
            "status": "accepted",
            "status_reason": None,
            "threads": inbox.to_json(),
        }
