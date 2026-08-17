"""Fail-closed adapter for the Valkey transactional activity outbox.

Ticket mutations persist an ``activity_outbox_event`` row first, then
``XADD`` onto ``activity:{post_id}``. A missing or disabled Valkey
port must not invent a stream id, a delivery, or a theta (Hohpe &
Woolf, 2003; Kleppmann, 2017). Hidden posts are omitted from the
buyer projection.

This module does not replace ``backend.app.activity_stream`` and does
not implement TEPP measurement (ADR 0022 on #214).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

DELIVERY_PENDING = "outbox_pending"
DELIVERY_DELIVERED = "outbox_delivered"
DELIVERY_FAILED = "outbox_failed"
PORT_NAME = "valkey"


class ValkeyNotAvailable(RuntimeError):
    """Raised when the Valkey outbox port is down or disabled."""

    reason = "valkey_not_available"


def _no_ping() -> None:
    raise ValkeyNotAvailable(
        "valkey_not_available: Valkey outbox port is not configured. "
        "Pass VALKEY_DISABLED=0 (default) or a ping= callable. "
        "Never invent a delivery."
    )


@dataclass(frozen=True)
class OutboxDelivery:
    """One visible delivered event. Never a calibrated theta."""

    post_id: str
    post_title: str
    event_summary: str
    delivery_status_code: str
    valkey_entry_id: str

    def to_json(self) -> dict[str, Any]:
        return {
            "post_id": self.post_id,
            "post_title": self.post_title,
            "event_summary": self.event_summary,
            "delivery_status_code": self.delivery_status_code,
            "valkey_entry_id": self.valkey_entry_id,
        }


@dataclass(frozen=True)
class OutboxList:
    """Accepted outbox projection. Empty when nothing was delivered."""

    items: tuple[OutboxDelivery, ...]

    def to_json(self) -> list[dict[str, Any]]:
        return [item.to_json() for item in self.items]


def project_outbox_list(
    rows: Sequence[Mapping[str, Any]],
    can_see_post: Callable[[Mapping[str, Any]], bool],
) -> OutboxList:
    """Accept persisted rows. Pending/failed/hidden rows drop. No invented id."""
    items: list[OutboxDelivery] = []
    seen: set[str] = set()
    for row in rows:
        if not can_see_post(row):
            continue
        status = str(row.get("delivery_status_code") or "").strip()
        post_id = str(row.get("post_id") or "").strip()
        title = str(row.get("post_title") or "").strip()
        summary = str(row.get("event_summary") or "").strip()
        entry_id = str(row.get("valkey_entry_id") or "").strip()
        if status != DELIVERY_DELIVERED:
            continue
        if not post_id or not title or not summary or not entry_id:
            continue
        dedupe = f"{post_id}:{summary}"
        if dedupe in seen:
            continue
        seen.add(dedupe)
        items.append(
            OutboxDelivery(
                post_id=post_id,
                post_title=title,
                event_summary=summary,
                delivery_status_code=status,
                valkey_entry_id=entry_id,
            )
        )
    return OutboxList(items=tuple(items))


def build_valkey_outbox_client(
    disabled: bool = False,
    ping: Callable[[], None] | None = None,
) -> "ValkeyOutboxClient":
    """``disabled=True`` keeps the default fail-closed ping."""
    if disabled:
        return ValkeyOutboxClient()
    if ping is None:
        return ValkeyOutboxClient()
    return ValkeyOutboxClient(ping=ping)


class ValkeyOutboxClient:
    """Projects durable outbox rows only when Valkey itself answers."""

    def __init__(self, ping: Callable[[], None] = _no_ping) -> None:
        self._ping = ping

    def as_api_payload(
        self,
        rows: Sequence[Mapping[str, Any]],
        can_see_post: Callable[[Mapping[str, Any]], bool],
    ) -> dict[str, Any]:
        """Buyer-visible outbox status. Never invents a delivery."""
        try:
            self._ping()
        except ValkeyNotAvailable:
            return {
                "port": PORT_NAME,
                "status": "unavailable",
                "status_reason": ValkeyNotAvailable.reason,
                "deliveries": [],
            }
        except Exception as exc:
            raise ValkeyNotAvailable(
                f"valkey_not_available: outbox ping failed ({exc})"
            ) from exc
        listing = project_outbox_list(rows, can_see_post)
        return {
            "port": PORT_NAME,
            "status": "accepted",
            "status_reason": None,
            "deliveries": listing.to_json(),
        }
