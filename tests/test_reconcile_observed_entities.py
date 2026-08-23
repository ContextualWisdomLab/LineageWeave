"""Tests for scripts/reconcile_observed_entities.py's batch aggregation.

`_reconcile_batch` is the pure per-pair replay loop, isolated from pool/
connection setup precisely so it can be exercised here without a real
database -- same reasoning as tests/test_backfill_customer_hints.py.
"""

from __future__ import annotations

import asyncio

import asyncpg

import scripts.reconcile_observed_entities as reconcile


def _pair(corporate_entity_id: str, source_post_id: str) -> dict[str, str]:
    return {"corporate_entity_id": corporate_entity_id, "source_post_id": source_post_id}


def test_reconcile_batch_replays_write_and_prune_for_each_pair(monkeypatch) -> None:
    recorded: list[tuple[str, str]] = []
    pruned: list[list[str]] = []

    async def fake_record_observed_entity(conn, corporate_entity_id, source_post_id):
        recorded.append((corporate_entity_id, source_post_id))

    async def fake_prune(conn, source_post_ids):
        pruned.append(source_post_ids)

    monkeypatch.setattr(reconcile, "record_observed_entity", fake_record_observed_entity)
    monkeypatch.setattr(reconcile, "prune_observed_entity_for_posts", fake_prune)

    pairs = [_pair("e-1", "p-1"), _pair("e-2", "p-2")]
    result = asyncio.run(reconcile._reconcile_batch(object(), pairs))

    assert recorded == [("e-1", "p-1"), ("e-2", "p-2")]
    assert pruned == [["p-1"], ["p-2"]]
    assert result == {
        "requested_pairs": 2,
        "reconciled_pairs": 2,
        "failed_pairs": 0,
        "failure_types": {},
    }


def test_reconcile_batch_counts_failures_without_aborting_the_batch(monkeypatch) -> None:
    async def fake_record_observed_entity(conn, corporate_entity_id, source_post_id):
        if source_post_id == "p-bad":
            raise asyncpg.PostgresError("connection reset")

    async def fake_prune(conn, source_post_ids):
        return None

    monkeypatch.setattr(reconcile, "record_observed_entity", fake_record_observed_entity)
    monkeypatch.setattr(reconcile, "prune_observed_entity_for_posts", fake_prune)

    pairs = [_pair("e-1", "p-bad"), _pair("e-2", "p-2")]
    result = asyncio.run(reconcile._reconcile_batch(object(), pairs))

    assert result["requested_pairs"] == 2
    assert result["reconciled_pairs"] == 1
    assert result["failed_pairs"] == 1
    assert result["failure_types"] == {"PostgresError": 1}


def test_reconcile_batch_empty_pairs_is_a_clean_no_op() -> None:
    result = asyncio.run(reconcile._reconcile_batch(object(), []))
    assert result == {
        "requested_pairs": 0,
        "reconciled_pairs": 0,
        "failed_pairs": 0,
        "failure_types": {},
    }
