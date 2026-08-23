"""Tests for scripts/backfill_customer_hints.py's batch aggregation.

`_resolve_batch` is the pure per-hint orchestration loop, isolated from
pool/connection setup precisely so it can be exercised here without a
real database or orchestrator -- same reasoning as
tests/test_customer_hint_ingestion.py's fakes.
"""

from __future__ import annotations

import argparse
import asyncio

import asyncpg

import scripts.backfill_customer_hints as backfill
from lineageweave.http_client import HttpClientError


def test_run_rejects_hint_code_and_all_combined() -> None:
    args = argparse.Namespace(hint_code="CUST-1", all=True, limit=25, hint_timeout=120.0)
    try:
        asyncio.run(backfill._run(args))
    except ValueError as exc:
        assert "cannot be combined" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_run_rejects_neither_hint_code_nor_all() -> None:
    # A bare invocation must not silently resolve one real hint via a live
    # orchestrator call -- an operator running this with no flags almost
    # certainly expected a no-op, not a real provider call.
    args = argparse.Namespace(hint_code=None, all=False, limit=25, hint_timeout=120.0)
    try:
        asyncio.run(backfill._run(args))
    except ValueError as exc:
        assert "one of --hint-code or --all is required" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_resolve_batch_counts_resolved_declined_and_failed(monkeypatch) -> None:
    outcomes = {
        "CUST-1": {"corporate_entity_id": "e-1", "entity_name": "Acme", "linked_post_count": 3,
                    "verification_evidence_url": "https://evidence.example/acme"},
        "CUST-2": None,  # declined this run -- not a failure
        "CUST-3": TimeoutError(),
        "CUST-4": HttpClientError("gateway unavailable"),
    }

    async def fake_resolve_customer_hint(conn, resolution_client, verification_client, hierarchy_client, hint_code):
        outcome = outcomes[hint_code]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(backfill, "resolve_customer_hint", fake_resolve_customer_hint)

    result = asyncio.run(
        backfill._resolve_batch(
            object(), object(), object(), object(), list(outcomes.keys()), hint_timeout=5.0
        )
    )

    assert result["requested_hint_codes"] == 4
    assert result["resolved_hint_codes"] == 1
    assert result["declined_hint_codes"] == 1
    assert result["failed_hint_codes"] == 2
    assert result["failure_types"] == {"HttpClientError": 1, "TimeoutError": 1}
    assert result["linked_post_count"] == 3
    assert result["resolved"] == [
        {
            "hint_code": "CUST-1",
            "corporate_entity_id": "e-1",
            "entity_name": "Acme",
            "linked_post_count": 3,
            "verification_evidence_url": "https://evidence.example/acme",
        }
    ]


def test_resolve_batch_empty_hint_codes_is_a_clean_no_op() -> None:
    result = asyncio.run(
        backfill._resolve_batch(object(), object(), object(), object(), [], hint_timeout=5.0)
    )
    assert result == {
        "requested_hint_codes": 0,
        "resolved_hint_codes": 0,
        "declined_hint_codes": 0,
        "linked_post_count": 0,
        "resolved": [],
        "failed_hint_codes": 0,
        "failure_types": {},
    }


def test_resolve_batch_surfaces_a_postgres_error_as_a_counted_failure(monkeypatch) -> None:
    async def fake_resolve_customer_hint(conn, resolution_client, verification_client, hierarchy_client, hint_code):
        raise asyncpg.PostgresError("connection reset")

    monkeypatch.setattr(backfill, "resolve_customer_hint", fake_resolve_customer_hint)

    result = asyncio.run(
        backfill._resolve_batch(object(), object(), object(), object(), ["CUST-9"], hint_timeout=5.0)
    )
    assert result["failed_hint_codes"] == 1
    assert result["failure_types"] == {"PostgresError": 1}
