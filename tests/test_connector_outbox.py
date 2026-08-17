"""Connector outbox stays pending when Valkey publish fails (ADR 0014)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "lineageweave" / "connector_outbox.py"


def _load():
    spec = importlib.util.spec_from_file_location("lw_connector_outbox", _PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


outbox = _load()


class _MemoryStore:
    def __init__(self) -> None:
        self.rows: dict[str, object] = {}
        self._next = 1

    def insert_pending(self, connector_code, idempotency_key, payload_sha256, payload):
        existing = next(
            (
                row
                for row in self.rows.values()
                if row.connector_code == connector_code and row.idempotency_key == idempotency_key
            ),
            None,
        )
        if existing is not None:
            if existing.payload_sha256 != payload_sha256:
                raise ValueError("idempotency_conflict")
            return existing
        event = outbox.OutboxEvent(
            outbox_event_id=f"evt-{self._next}",
            connector_code=connector_code,
            delivery_status_code=outbox.STATUS_PENDING,
            idempotency_key=idempotency_key,
            payload_sha256=payload_sha256,
            payload=payload,
        )
        self._next += 1
        self.rows[event.outbox_event_id] = event
        return event

    def list_pending(self, *, limit):
        pending = [
            row for row in self.rows.values() if row.delivery_status_code == outbox.STATUS_PENDING
        ]
        return pending[:limit]

    def mark_published(self, outbox_event_id, stream_entry_id):
        row = self.rows[outbox_event_id]
        self.rows[outbox_event_id] = outbox.OutboxEvent(
            **{**row.__dict__, "delivery_status_code": outbox.STATUS_PUBLISHED, "stream_entry_id": stream_entry_id}
        )

    def mark_failed(self, outbox_event_id, failure_code):
        row = self.rows[outbox_event_id]
        self.rows[outbox_event_id] = outbox.OutboxEvent(
            **{**row.__dict__, "failure_code": failure_code}
        )


def test_enqueue_is_idempotent_on_the_same_digest() -> None:
    store = _MemoryStore()
    payload = {"contract_version": 1, "idempotency_key": "demo-run-1"}
    first = outbox.enqueue_connector_outbox(
        store,
        connector_code=outbox.CONNECTOR_TEPP,
        idempotency_key="demo-run-1",
        payload=payload,
    )
    again = outbox.enqueue_connector_outbox(
        store,
        connector_code=outbox.CONNECTOR_TEPP,
        idempotency_key="demo-run-1",
        payload=payload,
    )
    assert first.outbox_event_id == again.outbox_event_id
    try:
        outbox.enqueue_connector_outbox(
            store,
            connector_code=outbox.CONNECTOR_TEPP,
            idempotency_key="demo-run-1",
            payload={**payload, "snapshot_id": "other"},
        )
    except ValueError as exc:
        assert "idempotency_conflict" in str(exc)
    else:
        raise AssertionError("expected digest conflict")


def test_publish_leaves_a_failed_row_pending() -> None:
    store = _MemoryStore()
    outbox.enqueue_connector_outbox(
        store,
        connector_code=outbox.CONNECTOR_TEPP,
        idempotency_key="ok",
        payload={"idempotency_key": "ok"},
    )
    outbox.enqueue_connector_outbox(
        store,
        connector_code=outbox.CONNECTOR_TEPP,
        idempotency_key="down",
        payload={"idempotency_key": "down"},
    )

    def publisher(stream_key, fields):
        assert stream_key == "outbox:connector_tepp"
        if fields["idempotency_key"] == "down":
            raise OSError("valkey unavailable")
        return "1-0"

    result = outbox.publish_pending_outbox(store, publisher)
    assert result == {"requested": 2, "published": 1, "pending": 1}
    by_key = {row.idempotency_key: row for row in store.rows.values()}
    assert by_key["ok"].delivery_status_code == outbox.STATUS_PUBLISHED
    assert by_key["down"].delivery_status_code == outbox.STATUS_PENDING
    assert by_key["down"].failure_code == "OSError"
    assert "theta" not in by_key["ok"].payload
