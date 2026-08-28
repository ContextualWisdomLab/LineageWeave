"""Dedicated durable-queue worker process for the Compose deployment."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import asyncpg

from backend.app.activity_stream import create_valkey_client
from backend.app.analysis_run_start import configured_tepp_client
from backend.app.analysis_run_worker import run_analysis_run_worker
from backend.app.config import load_settings
from backend.app.db import create_pool
from backend.app.global_ask_queue import run_global_ask_worker
from backend.app.main import (
    _adjudication_client,
    _claim_verification_client_factory,
    _embedding_client,
    _post_chat_client,
    _post_structure_client,
    _semantic_query_client,
    _vision_client,
)
from backend.app.post_content_worker import run_post_content_worker
from backend.app.topic_influence_worker import run_topic_influence_worker
from backend.app.worker_health import run_worker_heartbeat
from lineageweave.observability import configure_telemetry, shutdown_telemetry
from lineageweave.topic_influence_client import HttpTopicInfluenceClient

_WORKER_LEASE_NAME = "lineageweave_durable_queue_worker"


def _topic_influence_timeouts(settings: object) -> tuple[int, int]:
    """Return a declared request/lease pair with persistence time remaining."""
    request_timeout = getattr(
        settings, "topic_influence_request_timeout_seconds", None
    )
    lease_timeout = getattr(settings, "topic_influence_lease_timeout_seconds", None)
    if (
        type(request_timeout) is not int
        or type(lease_timeout) is not int
        or request_timeout <= 0
        or lease_timeout <= request_timeout
    ):
        raise ValueError(
            "topic influence lease timeout must be a declared positive integer "
            "strictly greater than the declared positive request timeout"
        )
    return request_timeout, lease_timeout


@asynccontextmanager
async def _single_worker_lease(pool: asyncpg.Pool) -> AsyncIterator[None]:
    """Fail a second worker process before two stream cursors can race."""
    async with pool.acquire() as conn:
        acquired = bool(
            await conn.fetchval(
                "select pg_try_advisory_lock(hashtextextended($1, 0))",
                _WORKER_LEASE_NAME,
            )
        )
        if not acquired:
            raise RuntimeError("another durable queue worker already owns the lease")
        try:
            yield
        finally:
            await conn.fetchval(
                "select pg_advisory_unlock(hashtextextended($1, 0))",
                _WORKER_LEASE_NAME,
            )


async def run_worker_process() -> None:
    """Own every durable queue consumer outside the HTTP API process."""
    configure_telemetry("lineageweave-worker")
    settings = load_settings()
    pool = await create_pool(settings.database_url)
    valkey = create_valkey_client(settings.valkey_url)
    try:
        async with _single_worker_lease(pool):
            topic_influence_url = getattr(
                settings, "topic_influence_transport_url", ""
            )
            influence_timeouts = (
                _topic_influence_timeouts(settings) if topic_influence_url else None
            )
            workers = [
                asyncio.create_task(run_worker_heartbeat()),
                asyncio.create_task(
                    run_analysis_run_worker(
                        valkey,
                        pool,
                        database_url=settings.database_url,
                        tepp_client=configured_tepp_client(
                            settings.tepp_transport_url,
                            settings.tepp_api_key,
                        ),
                        adjudication_client=_adjudication_client(),
                    )
                ),
                asyncio.create_task(
                    run_post_content_worker(
                        valkey,
                        pool,
                        vision_factory=_vision_client,
                        embedding_factory=_embedding_client,
                        structure_factory=_post_structure_client,
                    )
                ),
                asyncio.create_task(
                    run_global_ask_worker(
                        valkey,
                        pool,
                        chat_factory=lambda: _post_chat_client(
                            timeout=load_settings().orchestrator_answer_timeout_seconds
                        ),
                        embedding_factory=_embedding_client,
                        semantic_query_factory=_semantic_query_client,
                        claim_verification_factory=_claim_verification_client_factory,
                    )
                ),
            ]
            if topic_influence_url and influence_timeouts is not None:
                request_timeout, lease_timeout = influence_timeouts
                workers.append(
                    asyncio.create_task(
                        run_topic_influence_worker(
                            pool,
                            lambda: HttpTopicInfluenceClient(
                                topic_influence_url,
                                getattr(settings, "topic_influence_api_key", ""),
                                timeout=float(request_timeout),
                                lease_timeout_seconds=lease_timeout,
                            ),
                        )
                    )
                )
            try:
                await asyncio.gather(*workers)
            finally:
                for worker in workers:
                    worker.cancel()
                await asyncio.gather(*workers, return_exceptions=True)
    finally:
        try:
            await pool.close()
        finally:
            try:
                await valkey.aclose()
            finally:
                shutdown_telemetry()


def main() -> None:
    """Run the durable worker service until Compose stops the process."""
    asyncio.run(run_worker_process())


if __name__ == "__main__":
    main()
