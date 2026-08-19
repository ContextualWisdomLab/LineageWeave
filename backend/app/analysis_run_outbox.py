"""Durable start-work outbox. PostgreSQL is truth; Valkey is the wake-up.

ADR 0023. Start writes Running plus one immutable outbox row, then a
worker claims that row and runs ThreadWeave or ``tepp_client``. A crash
after enqueue leaves the work item; it does not invent a theta.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as redis

OUTBOX_STREAM_KEY = "analysis-run-outbox"
_CLAIMED = "analysis_outbox_claimed"
_DELIVERED = "analysis_outbox_delivered"


def outbox_request_digest(
    *,
    analysis_run_id: str,
    work_kind_code: str,
    snapshot_sha256: str,
    knowledge_cutoff: datetime,
) -> str:
    """SHA-256 of the frozen start request. Never hashes a post body."""
    cutoff = knowledge_cutoff
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=timezone.utc)
    material = json.dumps(
        {
            "analysis_run_id": str(analysis_run_id),
            "knowledge_cutoff": cutoff.astimezone(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "snapshot_sha256": snapshot_sha256,
            "work_kind_code": work_kind_code,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(material.encode()).hexdigest()


def outbox_stream_fields(
    *,
    analysis_run_id: str,
    work_kind_code: str,
    request_sha256: str,
) -> dict[str, str]:
    """Valkey XADD fields for one start-work wake-up. No body, no theta."""
    return {
        "analysis_run_id": str(analysis_run_id),
        "request_sha256": request_sha256,
        "work_kind_code": work_kind_code,
    }


async def publish_outbox_event(
    client: redis.Redis | None,
    *,
    analysis_run_id: str,
    work_kind_code: str,
    request_sha256: str,
) -> str | None:
    """``XADD`` the wake-up. A missing Valkey leaves PostgreSQL durable."""
    if client is None:
        return None
    try:
        entry_id = await client.xadd(
            OUTBOX_STREAM_KEY,
            outbox_stream_fields(
                analysis_run_id=analysis_run_id,
                work_kind_code=work_kind_code,
                request_sha256=request_sha256,
            ),
            maxlen=1000,
            approximate=True,
        )
    except redis.RedisError:
        return None
    return str(entry_id)


def latest_outbox_delivery_is_delivered(status_code: str | None) -> bool:
    """True when the newest delivery event already finished the work."""
    return status_code == _DELIVERED


def latest_outbox_delivery_is_claimed(status_code: str | None) -> bool:
    """True when a worker already claimed the row and may retry."""
    return status_code == _CLAIMED
