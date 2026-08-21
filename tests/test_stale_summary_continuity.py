"""Regression tests for buyer-visible stale summary continuity."""

import asyncio

from backend.app.post_summary_ingestion import fetch_persisted_summary
from lineageweave.post_summary import POST_SUMMARY_CONTRACT_VERSION


class _StaleSummaryConnection:
    """Minimal asyncpg-shaped fake containing one legacy summary header."""

    async def fetchrow(self, query: str, post_id: str) -> dict[str, object]:
        return {
            "korean_summary": "Previously persisted evidence.",
            "summary_contract_version": POST_SUMMARY_CONTRACT_VERSION - 1,
        }

    async def fetch(self, query: str, post_id: str) -> list[dict[str, object]]:
        return []


def test_stale_summary_is_hidden_by_default() -> None:
    """Current-contract reads must not silently present legacy semantics."""
    result = asyncio.run(fetch_persisted_summary(_StaleSummaryConnection(), "post-id"))
    assert result is None


def test_stale_summary_can_be_returned_with_explicit_status() -> None:
    """The continuity path exposes the old contract so the UI can label it."""
    result = asyncio.run(
        fetch_persisted_summary(_StaleSummaryConnection(), "post-id", allow_stale=True)
    )
    assert result is not None
    assert result["summary_status"] == "stale"
    assert result["summary_contract_version"] == POST_SUMMARY_CONTRACT_VERSION - 1
    assert result["korean_summary"] == "Previously persisted evidence."
