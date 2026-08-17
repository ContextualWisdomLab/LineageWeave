"""Valkey outbox for TEPP submit envelopes (ADR 0023).

The stream is the durable attempt log -- not a second score table.
Fields are outcome + next action + the published request identity.
No theta is written.
"""

from __future__ import annotations

from typing import Any

from lineageweave.fail_closed import FailClosedEnvelope

TEPP_OUTBOX_STREAM = "outbox:tepp"


def outbox_fields(envelope: FailClosedEnvelope, actor_account_id: str) -> dict[str, str]:
    """String fields Valkey can XADD. Measurement keys are never included."""
    request = envelope.request or {}
    return {
        "channel_code": envelope.channel_code,
        "outcome_code": envelope.outcome_code,
        "next_action": envelope.next_action,
        "actor_account_id": str(actor_account_id),
        "idempotency_key": str(request.get("idempotency_key", "")),
        "snapshot_id": str(request.get("snapshot_id", "")),
        "knowledge_cutoff": str(request.get("knowledge_cutoff", "")),
        "tenant_workspace_id": str(request.get("tenant_workspace_id", "")),
    }


def publish_tepp_outbox_sync(client: Any, envelope: FailClosedEnvelope, actor_account_id: str) -> str | None:
    """Sync ``XADD`` for ``make seed``. Skips a matching idempotency key."""
    fields = outbox_fields(envelope, actor_account_id)
    existing = client.xrevrange(TEPP_OUTBOX_STREAM, count=50)
    if any(row.get("idempotency_key") == fields["idempotency_key"] for _entry_id, row in existing):
        return None
    return client.xadd(TEPP_OUTBOX_STREAM, fields, maxlen=1000, approximate=True)


async def publish_tepp_outbox(client: Any, envelope: FailClosedEnvelope, actor_account_id: str) -> str:
    """``XADD`` one fail-closed (or accepted) TEPP attempt."""
    return await client.xadd(
        TEPP_OUTBOX_STREAM,
        outbox_fields(envelope, actor_account_id),
        maxlen=1000,
        approximate=True,
    )


async def list_tepp_outbox(client: Any, count: int = 20) -> list[dict[str, Any]]:
    """Newest first. Payloads are labels and request identity only."""
    entries = await client.xrevrange(TEPP_OUTBOX_STREAM, count=count)
    return [
        {
            "event_id": entry_id,
            "channel_code": fields.get("channel_code", ""),
            "outcome_code": fields.get("outcome_code", ""),
            "next_action": fields.get("next_action", ""),
            "idempotency_key": fields.get("idempotency_key", ""),
            "snapshot_id": fields.get("snapshot_id", ""),
            "knowledge_cutoff": fields.get("knowledge_cutoff", ""),
        }
        for entry_id, fields in entries
    ]
