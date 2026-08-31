"""Atomic bulk embedding backfill tests with synthetic records."""

from __future__ import annotations

import asyncio
import uuid

import pytest

from lineageweave.embedding_backfill import (
    _SELECT_UNITS_SQL,
    backfill_post_content_embeddings,
)


class _Transaction:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        self.conn.transaction_entries += 1

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _Connection:
    def __init__(self, rows):
        self.rows = rows
        self.executemany_calls = []
        self.execute_calls = []
        self.fetchval_calls = []
        self.transaction_entries = 0
        self.embedding_ids = {
            row["post_content_unit_id"]: uuid.uuid4() for row in rows
        }

    async def fetch(self, query, *args):
        if "from post_content_unit unit" in query:
            return self.rows
        selected_unit_ids = set(args[1])
        return [
            {
                "post_content_unit_id": unit_id,
                "post_content_embedding_id": embedding_id,
            }
            for unit_id, embedding_id in self.embedding_ids.items()
            if unit_id in selected_unit_ids
        ]

    def transaction(self):
        return _Transaction(self)

    async def executemany(self, query, args):
        self.executemany_calls.append((query, list(args)))

    async def execute(self, query, *args):
        self.execute_calls.append((query, args))

    async def fetchval(self, query, *args):
        self.fetchval_calls.append((query, args))
        return 1


class _EmbeddingClient:
    available = True

    def __init__(self, *, fail=False):
        self.fail = fail
        self.resolved_model = None
        self.calls = []

    def embed_many(self, texts, **kwargs):
        self.calls.append((list(texts), kwargs))
        if self.fail:
            raise RuntimeError("synthetic provider failure")
        self.resolved_model = "synthetic-embedding-model"
        return [[float(index), 1.0] for index, _text in enumerate(texts)]

    def batch_request_body_size(self, texts, **kwargs):
        return sum(len(text.encode("utf-8")) for text in texts) + 100 * len(texts)


def _row(index: int) -> dict[str, object]:
    return {
        "post_content_unit_id": uuid.uuid4(),
        "unit_text": f"synthetic semantic unit {index}",
        "unit_index": index,
        "post_id": uuid.uuid4(),
        "author_account_id": f"synthetic-author-{index}",
        "source_process_unit_code": f"synthetic-team-{index}",
        "source_author_code": None,
        "source_company_code": None,
        "source_customer_code": None,
        "source_project_code": None,
        "source_sales_pool_code": None,
        "corporate_entity_code": f"synthetic-company-{index}",
    }


def test_bulk_backfill_calls_provider_once_and_persists_in_one_transaction() -> None:
    rows = [_row(0), _row(1)]
    conn = _Connection(rows)
    client = _EmbeddingClient()

    result = asyncio.run(
        backfill_post_content_embeddings(conn, client, max_request_body_bytes=10_000, max_inputs=2048)
    )

    assert result == {
        "selected_units": 2,
        "persisted_units": 2,
        "dimension_values": 4,
        "model": "synthetic-embedding-model",
    }
    assert any(
        "refresh_post_content_embedding_exact_projection" in query
        for query, _args in conn.fetchval_calls
    )
    assert len(client.calls) == 1
    assert len(client.calls[0][0]) == 2
    assert [item["team"] for item in client.calls[0][1]["input_attributions"]] == [
        "synthetic-team-0",
        "synthetic-team-1",
    ]
    assert len(client.calls[0][1]["input_metadata"]) == 2
    assert conn.transaction_entries == 1
    assert len(conn.executemany_calls) == 2
    assert len(conn.executemany_calls[1][1]) == 4


def test_provider_failure_makes_no_database_change() -> None:
    conn = _Connection([_row(0), _row(1)])
    client = _EmbeddingClient(fail=True)

    with pytest.raises(RuntimeError, match="synthetic provider failure"):
        asyncio.run(
            backfill_post_content_embeddings(conn, client, max_request_body_bytes=10_000, max_inputs=2048)
        )

    assert conn.transaction_entries == 0
    assert conn.executemany_calls == []
    assert conn.execute_calls == []


def test_empty_selection_skips_provider_and_transaction() -> None:
    conn = _Connection([])
    client = _EmbeddingClient()

    result = asyncio.run(
        backfill_post_content_embeddings(conn, client, max_request_body_bytes=10_000, max_inputs=2048)
    )

    assert result == {
        "selected_units": 0,
        "persisted_units": 0,
        "dimension_values": 0,
    }
    assert client.calls == []
    assert conn.transaction_entries == 0


def test_oversized_first_unit_reaches_the_explicit_failure_guard() -> None:
    """The SQL cannot hide a blocking unit and silently stall later work."""
    row = _row(0)
    row["unit_text"] = "x" * 200

    with pytest.raises(
        ValueError,
        match="one semantic unit exceeds the advertised embedding request ceiling",
    ):
        asyncio.run(
            backfill_post_content_embeddings(
                _Connection([row]),
                _EmbeddingClient(),
                max_request_body_bytes=100,
                max_inputs=2048,
            )
        )

    assert "candidate_ordinal <= $2" in _SELECT_UNITS_SQL


def test_bulk_backfill_packs_largest_prefix_within_advertised_body_ceiling() -> None:
    rows = [_row(0), _row(1), _row(2)]
    conn = _Connection(rows)
    client = _EmbeddingClient()
    two_input_size = client.batch_request_body_size(
        [str(rows[0]["unit_text"]), str(rows[1]["unit_text"])]
    )

    result = asyncio.run(
        backfill_post_content_embeddings(
            conn, client, max_request_body_bytes=two_input_size, max_inputs=2048
        )
    )

    assert result["selected_units"] == 2
    assert len(client.calls[0][0]) == 2


def test_candidate_window_is_bounded_before_window_functions() -> None:
    """Each batch ranks at most the operator-advertised input ceiling."""
    bounded_start = _SELECT_UNITS_SQL.index("bounded_candidates as materialized")
    limit_position = _SELECT_UNITS_SQL.index("limit $2")
    window_position = _SELECT_UNITS_SQL.index("row_number() over")

    assert bounded_start < limit_position < window_position
