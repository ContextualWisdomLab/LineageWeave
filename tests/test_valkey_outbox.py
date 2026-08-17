"""Fail-closed Valkey transactional outbox.

A missing or disabled Valkey port never invents a stream id, a
delivery, or a theta. Hidden posts drop from the buyer projection.
"""

from __future__ import annotations

import pytest

from lineageweave.valkey_outbox import (
    ValkeyNotAvailable,
    ValkeyOutboxClient,
    build_valkey_outbox_client,
    project_outbox_list,
)

PUBLIC = {
    "post_id": "post-1",
    "post_title": "Public post",
    "visibility_code": "public",
    "event_summary": "Ticket created: Send Northridge Grid the revised quote",
    "delivery_status_code": "outbox_delivered",
    "valkey_entry_id": "1-0",
}
HIDDEN = {
    "post_id": "hidden-parent",
    "post_title": "Private parent",
    "visibility_code": "private",
    "event_summary": "Ticket created: hidden ticket",
    "delivery_status_code": "outbox_delivered",
    "valkey_entry_id": "1-1",
}
PENDING = {
    "post_id": "post-1",
    "post_title": "Public post",
    "visibility_code": "public",
    "event_summary": "Ticket created: pending only",
    "delivery_status_code": "outbox_pending",
    "valkey_entry_id": None,
}


def test_default_payload_never_invents_a_delivery() -> None:
    payload = ValkeyOutboxClient().as_api_payload(
        [PUBLIC],
        can_see_post=lambda _row: True,
    )
    assert payload == {
        "port": "valkey",
        "status": "unavailable",
        "status_reason": "valkey_not_available",
        "deliveries": [],
    }


def test_disabled_factory_fails_closed() -> None:
    client = build_valkey_outbox_client(disabled=True, ping=lambda: None)
    payload = client.as_api_payload([PUBLIC], can_see_post=lambda _row: True)
    assert payload["status"] == "unavailable"
    assert payload["deliveries"] == []


def test_reachable_port_lists_visible_delivered_rows() -> None:
    payload = ValkeyOutboxClient(ping=lambda: None).as_api_payload(
        [PUBLIC, HIDDEN, PENDING],
        can_see_post=lambda row: row["post_id"] != "hidden-parent",
    )
    assert payload["status"] == "accepted"
    assert payload["status_reason"] is None
    assert payload["deliveries"] == [
        {
            "post_id": "post-1",
            "post_title": "Public post",
            "event_summary": "Ticket created: Send Northridge Grid the revised quote",
            "delivery_status_code": "outbox_delivered",
            "valkey_entry_id": "1-0",
        }
    ]


def test_project_drops_pending_and_missing_stream_id() -> None:
    listing = project_outbox_list(
        [PENDING, {**PUBLIC, "valkey_entry_id": ""}],
        can_see_post=lambda _row: True,
    )
    assert listing.to_json() == []


def test_ping_exception_fails_closed() -> None:
    def boom() -> None:
        raise RuntimeError("connection refused")

    with pytest.raises(ValkeyNotAvailable, match="valkey_not_available"):
        ValkeyOutboxClient(ping=boom).as_api_payload(
            [PUBLIC],
            can_see_post=lambda _row: True,
        )
