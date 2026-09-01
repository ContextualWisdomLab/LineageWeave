"""Dedicated durable-queue worker process for the Compose deployment."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

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
from backend.app.voice_taxonomy_transition_worker import (
    run_voice_taxonomy_transition_worker,
)
from backend.app.worker_health import run_worker_heartbeat
from lineageweave.observability import configure_telemetry, shutdown_telemetry
from lineageweave.topic_influence_client import HttpTopicInfluenceClient

_ALL_CONSUMERS = (
    "analysis_run",
    "post_content",
    "global_ask",
    "voice_taxonomy",
    "topic_influence",
)
_logger = logging.getLogger(__name__)


def _selected_consumers(settings: object) -> frozenset[str]:
    """Return the declared consumer set, defaulting to the historical full worker."""
    raw = getattr(settings, "worker_consumers", "")
    if not isinstance(raw, str):
        raise TypeError("LINEAGEWEAVE_WORKER_CONSUMERS must be comma-separated text")
    selected = frozenset(item.strip() for item in raw.split(",") if item.strip())
    if not selected:
        return frozenset(_ALL_CONSUMERS)
    unknown = selected.difference(_ALL_CONSUMERS)
    if unknown:
        raise ValueError(
            "LINEAGEWEAVE_WORKER_CONSUMERS contains unknown consumers: "
            + ", ".join(sorted(unknown))
        )
    return selected


def _active_consumers(
    selected: frozenset[str], *, topic_influence_enabled: bool
) -> frozenset[str]:
    """Remove an unavailable optional consumer and reject a no-op worker."""
    active = selected.difference(() if topic_influence_enabled else {"topic_influence"})
    if not active:
        raise ValueError("selected worker has no active durable consumers")
    return active


def _topic_influence_timeouts(settings: object) -> tuple[int, int, int]:
    """Return a declared request/lease pair with persistence time remaining."""
    request_timeout = getattr(
        settings, "topic_influence_request_timeout_seconds", None
    )
    lease_timeout = getattr(settings, "topic_influence_lease_timeout_seconds", None)
    poll_seconds = getattr(settings, "topic_influence_poll_seconds", None)
    if (
        type(request_timeout) is not int
        or type(lease_timeout) is not int
        or request_timeout <= 0
        or lease_timeout <= request_timeout
        or type(poll_seconds) is not int
        or poll_seconds <= 0
    ):
        raise ValueError(
            "topic influence lease timeout must be a declared positive integer "
            "strictly greater than the declared positive request timeout, with a "
            "declared positive poll interval"
        )
    return request_timeout, lease_timeout, poll_seconds


def _optional_topic_influence_timeouts(
    settings: object, *, transport_url: object
) -> tuple[int, int, int] | None:
    """Disable only optional influence work when its endpoint contract is invalid."""
    if not transport_url:
        return None
    if not isinstance(transport_url, str):
        _logger.error(
            "Topic influence is disabled; declare an absolute HTTP or HTTPS "
            "transport URL before enabling this consumer"
        )
        return None
    parsed = urlsplit(transport_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or not parsed.hostname
    ):
        _logger.error(
            "Topic influence is disabled; declare an absolute HTTP or HTTPS "
            "transport URL before enabling this consumer"
        )
        return None
    try:
        return _topic_influence_timeouts(settings)
    except ValueError:
        _logger.error(
            "Topic influence is disabled; declare a positive lease timeout strictly "
            "greater than its request timeout before enabling this consumer"
        )
        return None


@asynccontextmanager
async def _consumer_worker_lease(
    pool: asyncpg.Pool, consumers: frozenset[str]
) -> AsyncIterator[None]:
    """Hold one session-level advisory lease for every selected consumer."""
    async with pool.acquire() as conn:
        acquired: list[str] = []
        try:
            for consumer in sorted(consumers):
                lease_name = f"lineageweave_durable_queue_worker:{consumer}"
                owns_lease = bool(
                    await conn.fetchval(
                        "select pg_try_advisory_lock(hashtextextended($1, 0))",
                        lease_name,
                    )
                )
                if not owns_lease:
                    raise RuntimeError(
                        f"another durable queue worker already owns {consumer}"
                    )
                acquired.append(lease_name)
            yield
        finally:
            for lease_name in reversed(acquired):
                await conn.fetchval(
                    "select pg_advisory_unlock(hashtextextended($1, 0))",
                    lease_name,
                )


async def run_worker_process() -> None:
    """Own every durable queue consumer outside the HTTP API process."""
    configure_telemetry("lineageweave-worker")
    settings = load_settings()
    pool = await create_pool(settings.database_url)
    valkey = create_valkey_client(settings.valkey_url)
    try:
        selected = _selected_consumers(settings)
        topic_influence_url = getattr(settings, "topic_influence_transport_url", "")
        influence_timeouts = _optional_topic_influence_timeouts(
            settings, transport_url=topic_influence_url
        )
        active_consumers = _active_consumers(
            selected,
            topic_influence_enabled=bool(
                topic_influence_url and influence_timeouts is not None
            ),
        )
        async with _consumer_worker_lease(pool, frozenset(active_consumers)):
            workers = [asyncio.create_task(run_worker_heartbeat())]
            if "analysis_run" in active_consumers:
                workers.append(
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
                    )
                )
            if "post_content" in active_consumers:
                workers.append(
                    asyncio.create_task(
                        run_post_content_worker(
                            valkey,
                            pool,
                            vision_factory=_vision_client,
                            embedding_factory=_embedding_client,
                            structure_factory=_post_structure_client,
                        )
                    )
                )
            if "global_ask" in active_consumers:
                workers.append(
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
                    )
                )
            if "voice_taxonomy" in active_consumers:
                workers.append(
                    asyncio.create_task(
                        run_voice_taxonomy_transition_worker(settings.database_url)
                    )
                )
            if "topic_influence" in active_consumers:
                assert influence_timeouts is not None
                request_timeout, lease_timeout, poll_seconds = influence_timeouts
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
                            poll_seconds=float(poll_seconds),
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
