"""Transactional connector outbox before a Valkey stream publish (ADR 0014).

A TEPP or orchestrator submit is first a 3NF ``connector_outbox_event``
row (``outbox_pending``). A later flush ``XADD``s onto
``outbox:{connector_code}`` and marks ``outbox_published``. A Valkey
failure leaves the row pending with ``failure_code`` -- it is not
dropped and it is not treated as delivered. No invented theta lives
in the payload.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Protocol

CONNECTOR_TEPP = "connector_tepp"
CONNECTOR_ORCHESTRATOR = "connector_orchestrator"
STATUS_PENDING = "outbox_pending"
STATUS_PUBLISHED = "outbox_published"
STATUS_FAILED = "outbox_failed"

CONNECTOR_CODES = frozenset({CONNECTOR_TEPP, CONNECTOR_ORCHESTRATOR})
STATUS_CODES = frozenset({STATUS_PENDING, STATUS_PUBLISHED, STATUS_FAILED})


class OutboxStore(Protocol):
    """Persistence for pending connector deliveries."""

    def insert_pending(
        self, connector_code: str, idempotency_key: str, payload_sha256: str, payload: dict[str, Any]
    ) -> OutboxEvent: ...

    def list_pending(self, *, limit: int) -> list[OutboxEvent]: ...

    def mark_published(self, outbox_event_id: str, stream_entry_id: str) -> None: ...

    def mark_failed(self, outbox_event_id: str, failure_code: str) -> None: ...


@dataclass(frozen=True)
class OutboxEvent:
    """One pending or published connector delivery."""

    outbox_event_id: str
    connector_code: str
    delivery_status_code: str
    idempotency_key: str
    payload_sha256: str
    payload: dict[str, Any]
    stream_entry_id: str | None = None
    failure_code: str | None = None


def payload_digest(payload: dict[str, Any]) -> str:
    """SHA-256 of the canonical JSON payload."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def outbox_stream_key(connector_code: str) -> str:
    """Valkey stream for one connector kind."""
    if connector_code not in CONNECTOR_CODES:
        raise ValueError(f"unknown connector_code {connector_code!r}")
    return f"outbox:{connector_code}"


def enqueue_connector_outbox(
    store: OutboxStore,
    *,
    connector_code: str,
    idempotency_key: str,
    payload: dict[str, Any],
) -> OutboxEvent:
    """Persist a pending delivery. Same key + digest is the store's job."""
    if connector_code not in CONNECTOR_CODES:
        raise ValueError(f"unknown connector_code {connector_code!r}")
    key = idempotency_key.strip()
    if not key:
        raise ValueError("idempotency_key is required")
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    return store.insert_pending(connector_code, key, payload_digest(payload), payload)


def publish_pending_outbox(
    store: OutboxStore,
    publisher: Callable[[str, dict[str, str]], str],
    *,
    limit: int = 50,
) -> dict[str, int]:
    """Publish pending rows. A publisher error leaves that row pending."""
    if limit < 1:
        raise ValueError("limit must be >= 1")
    pending = store.list_pending(limit=limit)
    published = 0
    still_pending = 0
    for event in pending:
        fields = {
            "outbox_event_id": event.outbox_event_id,
            "connector_code": event.connector_code,
            "idempotency_key": event.idempotency_key,
            "payload_sha256": event.payload_sha256,
            "payload_json": json.dumps(event.payload, sort_keys=True, separators=(",", ":")),
        }
        try:
            entry_id = publisher(outbox_stream_key(event.connector_code), fields)
        except Exception as exc:  # noqa: BLE001 -- Valkey/transport stays pending
            store.mark_failed(event.outbox_event_id, type(exc).__name__)
            still_pending += 1
            continue
        store.mark_published(event.outbox_event_id, str(entry_id))
        published += 1
    return {"requested": len(pending), "published": published, "pending": still_pending}
