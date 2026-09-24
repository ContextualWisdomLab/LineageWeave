"""Shared durable Global Ask application service for REST and MCP."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import asyncpg
import redis.asyncio as redis
from fastapi import HTTPException, status

from backend.app.auth import CurrentAccount
from backend.app.global_ask_queue import (
    GlobalAskOutstandingLimitExceeded,
    enqueue_global_ask_job,
)
from backend.app.mcp_rate_limit import (
    McpRateLimiterUnavailable,
    McpRateLimitExceeded,
    ValkeyMcpRateLimiter,
)
from backend.app.source_post_revision import parse_as_of_clock


async def submit_global_ask(
    *,
    pool: asyncpg.Pool,
    valkey: redis.Redis,
    account: CurrentAccount,
    question: str,
    verify_external: bool,
    knowledge_cutoff: str | None,
    service_available: bool,
    question_max_bytes: int | None,
    max_outstanding_jobs: int | None,
    quota_request_limit: int | None,
    quota_window_seconds: int | None,
    quota_already_consumed: bool = False,
) -> dict[str, Any]:
    """Validate and enqueue one durable owner-scoped Global Ask job."""
    if not account.has_permission("post_read"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "post_read permission required")
    normalized_question = question.strip()
    if not normalized_question:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "question is required"
        )
    cutoff = None
    if knowledge_cutoff is not None:
        try:
            cutoff = parse_as_of_clock(knowledge_cutoff)
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "knowledge_cutoff must be an ISO-8601 timestamp",
            ) from exc
    if (
        question_max_bytes is None
        or max_outstanding_jobs is None
        or quota_request_limit is None
        or quota_window_seconds is None
    ):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Ask is temporarily unavailable. Ask an administrator to finish "
            "capacity setup, then retry.",
        )
    if len(normalized_question.encode("utf-8")) > question_max_bytes:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "The question is too long. Shorten it and try again.",
        )
    if not service_available:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Ask Agent is unavailable. Ask an administrator to configure the "
            "analysis service, then retry.",
        )
    if cutoff is not None:
        async with pool.acquire() as conn:
            if cutoff > await conn.fetchval("select now()"):
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_CONTENT,
                    "knowledge_cutoff must be at or before the database clock",
                )
    if not quota_already_consumed:
        limiter = ValkeyMcpRateLimiter(
            valkey,
            request_limit=quota_request_limit,
            window_seconds=quota_window_seconds,
        )
        try:
            await limiter.consume(account.user_account_id)
        except McpRateLimitExceeded as exc:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many questions are already being submitted. Retry later.",
                headers={"Retry-After": str(exc.retry_after_seconds)},
            ) from exc
        except McpRateLimiterUnavailable as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Ask is temporarily unavailable. Retry later.",
            ) from exc
    async with pool.acquire() as conn:
        try:
            job_id = await enqueue_global_ask_job(
                conn,
                valkey,
                requesting_account_id=account.user_account_id,
                question_text=normalized_question,
                verify_external_requested=verify_external,
                knowledge_cutoff=cutoff,
                corporate_entity_ids=account.corporate_entity_ids,
                process_unit_ids=account.process_unit_ids,
                max_outstanding_jobs=max_outstanding_jobs,
            )
        except GlobalAskOutstandingLimitExceeded as exc:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many questions are still active. Wait for an existing question to finish before submitting another.",
            ) from exc
    return {"ask_job_id": job_id, "job_status_code": "queued"}


async def read_global_ask_job(
    *, pool: asyncpg.Pool, account: CurrentAccount, ask_job_id: UUID
) -> dict[str, Any]:
    """Read one owner's durable Global Ask status and persisted result."""
    if not account.has_permission("post_read"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "post_read permission required")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "select requesting_account_id, job_status_code, answer_payload,"
            " failure_detail from global_ask_job where global_ask_job_id = $1",
            ask_job_id,
        )
    if row is None or str(row["requesting_account_id"]) != account.user_account_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ask job not found")
    body: dict[str, Any] = {
        "ask_job_id": str(ask_job_id),
        "job_status_code": row["job_status_code"],
    }
    if row["job_status_code"] == "succeeded" and row["answer_payload"] is not None:
        payload = row["answer_payload"]
        body["answer"] = json.loads(payload) if isinstance(payload, str) else payload
    if row["job_status_code"] == "failed":
        body["failure_detail"] = row["failure_detail"]
    return body
