"""Dedicated durable-queue worker process for the Compose deployment."""

from __future__ import annotations

import asyncio

from backend.app.activity_stream import create_valkey_client
from backend.app.analysis_run_start import configured_tepp_client
from backend.app.analysis_run_worker import run_analysis_run_worker
from backend.app.config import load_settings
from backend.app.db import create_pool
from backend.app.global_ask_queue import run_global_ask_worker
from backend.app.main import (
    _adjudication_client,
    _embedding_client,
    _post_chat_client,
    _post_structure_client,
    _vision_client,
)
from backend.app.post_content_worker import run_post_content_worker
from lineageweave.observability import configure_telemetry, shutdown_telemetry


async def run_worker_process() -> None:
    """Own every durable queue consumer outside the HTTP API process."""
    configure_telemetry("lineageweave-worker")
    settings = load_settings()
    pool = await create_pool(settings.database_url)
    valkey = create_valkey_client(settings.valkey_url)
    workers = (
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
            )
        ),
    )
    try:
        await asyncio.gather(*workers)
    finally:
        for worker in workers:
            worker.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
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
