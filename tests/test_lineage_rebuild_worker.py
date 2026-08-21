"""Worker contracts: LLM work stays off the event loop and is not invented."""

from __future__ import annotations

import asyncio
import time

from lineageweave.fixtures import sample_records
from lineageweave.lineage_persistence import lineage_edge_specs

from backend.app.lineage_rebuild_queue import LLM_AVAILABLE, LLM_SKIPPED, adjudication_client_for_job


class _SlowAdjudicationClient:
    available = True

    def __init__(self) -> None:
        self.calls = 0

    def judge(self, candidate_label: str, record_label: str) -> float:
        self.calls += 1
        time.sleep(0.02)
        return 0.9 if candidate_label else 0.1


def test_skipped_status_never_selects_the_live_client() -> None:
    live = _SlowAdjudicationClient()
    selected = adjudication_client_for_job(live, LLM_SKIPPED)
    assert selected.available is False
    edges = lineage_edge_specs(sample_records(), llm=selected)
    assert live.calls == 0
    assert all("llm" not in edge.channel_scores for edge in edges)


def test_available_status_uses_the_orchestrator_client() -> None:
    live = _SlowAdjudicationClient()
    selected = adjudication_client_for_job(live, LLM_AVAILABLE)
    edges = lineage_edge_specs(sample_records(), llm=selected)
    assert live.calls > 0
    assert all("llm" in edge.channel_scores for edge in edges)


def test_event_loop_progresses_while_model_backed_reconstruct_runs() -> None:
    async def _run() -> None:
        live = _SlowAdjudicationClient()
        progressed = False

        async def marker() -> None:
            nonlocal progressed
            await asyncio.sleep(0)
            progressed = True

        marker_task = asyncio.create_task(marker())
        await asyncio.to_thread(
            lineage_edge_specs, sample_records(), llm=live
        )
        await marker_task
        assert progressed is True
        assert live.calls > 0

    asyncio.run(_run())
