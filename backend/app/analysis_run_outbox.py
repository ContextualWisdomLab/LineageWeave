"""PostgreSQL outbox for one lineage delivery per analysis run.

Valkey may later signal a worker. Durable lease and completion state stay
here so a missing queue cannot invent a Succeeded run or a TEPP theta.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import asyncpg

LINEAGE_DELIVERY_KIND = "analysis_delivery_lineage"
DELIVERY_QUEUED = "analysis_delivery_queued"
DELIVERY_LEASED = "analysis_delivery_leased"
DELIVERY_COMPLETED = "analysis_delivery_completed"
DELIVERY_FAILED = "analysis_delivery_failed"
_LEASE_TTL = timedelta(minutes=15)


class AnalysisRunDeliveryError(Exception):
    """Fail-closed delivery: HTTP status plus a next-action detail string."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def enqueue_lineage_delivery(
    conn: asyncpg.Connection,
    analysis_run_id: str,
) -> None:
    """Queue one lineage delivery. A replay of the same run is a no-op."""
    await conn.execute(
        """
        insert into analysis_run_outbox
            (analysis_run_id, delivery_kind_code, delivery_status_code)
        values ($1, $2, $3)
        on conflict (analysis_run_id) do nothing
        """,
        analysis_run_id,
        LINEAGE_DELIVERY_KIND,
        DELIVERY_QUEUED,
    )


async def claim_lineage_delivery(
    conn: asyncpg.Connection,
    analysis_run_id: str,
) -> str:
    """Lease a queued lineage row and return the lease token.

    An empty token means the outbox already completed (replay). A live
    lease from another worker is 409.
    """
    current = await conn.fetchrow(
        """
        select delivery_kind_code, delivery_status_code, lease_token, leased_until
        from analysis_run_outbox
        where analysis_run_id = $1
        for update
        """,
        analysis_run_id,
    )
    if current is None:
        raise AnalysisRunDeliveryError(
            422,
            "This run has no queued reconstruction. Request a lineage run, then start reconstruction.",
        )
    if current["delivery_kind_code"] != LINEAGE_DELIVERY_KIND:
        raise AnalysisRunDeliveryError(
            422,
            "Connect a TEPP transport from a Failed TEPP row. This path reconstructs lineage only.",
        )
    if current["delivery_status_code"] == DELIVERY_COMPLETED:
        return ""
    now = datetime.now(timezone.utc)
    if current["delivery_status_code"] == DELIVERY_LEASED:
        leased_until = current["leased_until"]
        if leased_until is not None and leased_until > now:
            raise AnalysisRunDeliveryError(
                409,
                "Reconstruction is already in progress. Refresh this run.",
            )
    if current["delivery_status_code"] == DELIVERY_FAILED:
        raise AnalysisRunDeliveryError(
            422,
            "Open this run to see why it failed, then retry reconstruction from a current snapshot.",
        )
    token = uuid4().hex
    leased = await conn.fetchval(
        """
        update analysis_run_outbox
           set delivery_status_code = $2,
               lease_token = $3,
               leased_until = $4,
               attempt_count = attempt_count + 1,
               last_attempt_at = $5
         where analysis_run_id = $1
         returning analysis_run_id
        """,
        analysis_run_id,
        DELIVERY_LEASED,
        token,
        now + _LEASE_TTL,
        now,
    )
    if leased is None:
        raise AnalysisRunDeliveryError(
            422,
            "This run has no queued reconstruction. Request a lineage run, then start reconstruction.",
        )
    return token


async def complete_lineage_delivery(
    conn: asyncpg.Connection,
    analysis_run_id: str,
    lease_token: str,
) -> None:
    """Mark a held lease completed. Does not write a theta."""
    now = datetime.now(timezone.utc)
    updated = await conn.fetchval(
        """
        update analysis_run_outbox
           set delivery_status_code = $3,
               lease_token = null,
               leased_until = null,
               completed_at = $4
         where analysis_run_id = $1
           and lease_token = $2
           and delivery_status_code = $5
         returning analysis_run_id
        """,
        analysis_run_id,
        lease_token,
        DELIVERY_COMPLETED,
        now,
        DELIVERY_LEASED,
    )
    if updated is None:
        raise AnalysisRunDeliveryError(
            409,
            "Reconstruction is already in progress. Refresh this run.",
        )


async def fail_lineage_delivery(
    conn: asyncpg.Connection,
    analysis_run_id: str,
    lease_token: str,
) -> None:
    """Release a held lease as failed without storing exception text."""
    updated = await conn.fetchval(
        """
        update analysis_run_outbox
           set delivery_status_code = $3,
               lease_token = null,
               leased_until = null
         where analysis_run_id = $1
           and lease_token = $2
           and delivery_status_code = $4
         returning analysis_run_id
        """,
        analysis_run_id,
        lease_token,
        DELIVERY_FAILED,
        DELIVERY_LEASED,
    )
    if updated is None:
        raise AnalysisRunDeliveryError(
            409,
            "Reconstruction is already in progress. Refresh this run.",
        )
