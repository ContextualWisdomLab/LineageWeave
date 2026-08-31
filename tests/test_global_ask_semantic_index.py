from __future__ import annotations

import asyncio
import hashlib
import struct
import threading
from datetime import date
from types import SimpleNamespace

import pytest

from backend.app.global_ask_semantic_index import (
    GlobalAskExactSemanticIndex,
    build_global_ask_exact_semantic_index,
)
from lineageweave.rankweave_client import RankWeaveNotAvailable


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _Connection:
    def __init__(self) -> None:
        vector_bytes = struct.pack(">2d", 1.0, 0.0)
        self.snapshot_rows = [
            {
                "item_id": "post-a",
                "unit_id": "unit-a",
                "vector_bytes": vector_bytes,
                "vector_sha256": hashlib.sha256(vector_bytes).hexdigest(),
            }
        ]
        self.authorized_rows = [
            {
                "item_id": "post-a",
                "unit_id": "unit-a",
                "unit_index": 3,
                "evidence_open_available": True,
                "date_eligible": True,
            }
        ]
        self.snapshot_fetches = 0
        self.version_fetches = 0
        self.projection_version = 7
        self.authorization_version = 11
        self.authorization_queries: list[str] = []
        self.packed_authorization = _pack_authorization(("post-a", "unit-a"))
        self.scope_rows = [
            {
                "entity_ids": ["entity-a"],
                "process_ids": [],
                "process_scope_limited": False,
            }
        ]

    def transaction(self, **kwargs):
        assert kwargs == {"isolation": "repeatable_read", "readonly": True}
        return _Transaction()

    async def fetchval(self, query, *args):
        if "projection_version" in query:
            return self.projection_version
        self.authorization_queries.append(query)
        assert "int8send(count(*))" in query
        return self.packed_authorization

    async def fetchrow(self, query, *args):
        assert "authorization_version" in query
        self.version_fetches += 1
        return self.projection_version, self.authorization_version

    async def fetch(self, query, *args):
        if "vector_bytes" in query:
            self.snapshot_fetches += 1
            return self.snapshot_rows
        if "with readers as" in query:
            assert "left join account_affiliation" in query
            return self.scope_rows
        self.authorization_queries.append(query)
        if "authorized on true" in query:
            sentinel = {
                "request_id": None,
                "ordinal": None,
                "item_id": None,
                "unit_id": None,
                "unit_index": None,
                "evidence_open_available": False,
                "date_eligible": False,
                "projection_version": self.projection_version,
                "authorization_version": self.authorization_version,
            }
            requested = (
                zip(args[5], args[6], args[7], args[8], strict=True)
                if "from unnest(" in query
                else (
                    tuple(args[offset : offset + 4])
                    for offset in range(5, len(args), 6)
                )
            )
            authorized = [
                {
                    **self.authorized_rows[0],
                    "request_id": request_id,
                    "ordinal": ordinal,
                    "item_id": item_id,
                    "unit_id": unit_id,
                    "projection_version": self.projection_version,
                    "authorization_version": self.authorization_version,
                }
                for request_id, ordinal, item_id, unit_id in requested
                if (item_id, unit_id)
                == (
                    self.authorized_rows[0]["item_id"],
                    self.authorized_rows[0]["unit_id"],
                )
            ]
            return authorized or [sentinel]
        if "projection_state.projection_version = $10" in query and (
            args[9] != self.projection_version
            or args[10] != self.authorization_version
        ):
            return []
        return self.authorized_rows


class _OwnerIndex:
    constructions = 0
    leak = False
    preflight_failure = False
    top_k_calls: list[tuple[int, int]] = []

    def __init__(self, version, model, dimension, candidate_ids, packed_vectors):
        type(self).constructions += 1
        assert model == "synthetic-model"
        assert dimension == 2
        assert candidate_ids == [("post-a", "unit-a")]
        assert packed_vectors == struct.pack(">2d", 1.0, 0.0)
        self.snapshot_evidence = SimpleNamespace(
            snapshot_version=version,
            vector_dimension=dimension,
            candidate_count=len(candidate_ids),
        )

    def rank_authorized_packed(self, model, query, packed_authorization):
        assert model == "synthetic-model"
        assert query == [1.0, 0.0]
        assert packed_authorization == _pack_authorization(("post-a", "unit-a"))
        result = SimpleNamespace(
            item_id="hidden-post" if self.leak else "post-a",
            winning_unit_id="hidden-unit" if self.leak else "unit-a",
            score=1.0,
        )
        return SimpleNamespace(snapshot=self.snapshot_evidence, results=[result])

    def preflight_authorized_packed(self, model, packed_authorization):
        if self.preflight_failure:
            raise ValueError("synthetic preflight failure")
        return self.rank_authorized_packed(model, [1.0, 0.0], packed_authorization)

    def preflight_authorized_top_k_packed(
        self, model, packed_authorization, top_k
    ):
        return self.rank_authorized_top_k_batch_packed(
            model, [[1.0, 0.0]], packed_authorization, top_k
        )[0]

    def rank_authorized_batch_packed(self, model, queries, packed_authorization):
        return [
            self.rank_authorized_packed(model, query, packed_authorization)
            for query in queries
        ]

    def rank_authorized_top_k_batch_packed(
        self, model, queries, packed_authorization, top_k
    ):
        type(self).top_k_calls.append((len(queries), top_k))
        reports = self.rank_authorized_batch_packed(
            model, queries, packed_authorization
        )
        for report in reports:
            report.results = report.results[:top_k]
        return reports


class _ConcurrentOwnerIndex(_OwnerIndex):
    barrier: threading.Barrier | None = None
    batch_sizes: list[int] = []

    def rank_authorized_packed(self, model, query, packed_authorization):
        if self.barrier is not None:
            self.barrier.wait(timeout=2)
        return super().rank_authorized_packed(model, query, packed_authorization)

    def rank_authorized_batch_packed(
        self, model, queries, packed_authorization
    ):
        type(self).batch_sizes.append(len(queries))
        return [
            _OwnerIndex.rank_authorized_packed(
                self, model, query, packed_authorization
            )
            for query in queries
        ]


def _pack_authorization(*identities: tuple[str, str]) -> bytes:
    packed = struct.pack(">Q", len(identities))
    for item_id, unit_id in identities:
        for identity in (item_id, unit_id):
            encoded = identity.encode()
            packed += struct.pack(">Q", len(encoded)) + encoded
    return packed


def _rank(index, conn):
    async def prepared_rank():
        await index.prepare(conn, model_identity="synthetic-model", vector_dimension=2)
        return await index.rank_authorized(
            conn,
            model_identity="synthetic-model",
            query_vector=[1.0, 0.0],
            authorized_corporate_entity_ids=["entity-a"],
            authorized_process_unit_ids=["unit-a"],
            start_date=None,
            end_date=None,
            limit=4,
        )

    return asyncio.run(prepared_rank())


def test_exact_index_loads_once_then_ranks_only_authorized_ids(monkeypatch) -> None:
    _OwnerIndex.constructions = 0
    _OwnerIndex.leak = False
    monkeypatch.setattr(
        "backend.app.global_ask_semantic_index._import_rankweave",
        lambda: SimpleNamespace(SemanticUnitExactIndex=_OwnerIndex),
    )
    conn = _Connection()
    index = GlobalAskExactSemanticIndex()

    first = _rank(index, conn)
    second = _rank(index, conn)

    assert first == second
    assert first[0].post_id == "post-a"
    assert first[0].unit_index == 3
    assert conn.snapshot_fetches == 1
    assert _OwnerIndex.constructions == 1
    assert all(
        "post_content_embedding_value" not in sql for sql in conn.authorization_queries
    )
    assert all("visibility_code" in sql for sql in conn.authorization_queries)


def test_exact_index_rejects_owner_authorization_leak(monkeypatch) -> None:
    _OwnerIndex.leak = True
    monkeypatch.setattr(
        "backend.app.global_ask_semantic_index._import_rankweave",
        lambda: SimpleNamespace(SemanticUnitExactIndex=_OwnerIndex),
    )

    with pytest.raises(RankWeaveNotAvailable, match="unauthorized identity"):
        _rank(GlobalAskExactSemanticIndex(), _Connection())
    _OwnerIndex.leak = False


def test_exact_index_rejects_projection_digest_mismatch(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.app.global_ask_semantic_index._import_rankweave",
        lambda: SimpleNamespace(SemanticUnitExactIndex=_OwnerIndex),
    )
    conn = _Connection()
    conn.snapshot_rows[0]["vector_sha256"] = "0" * 64

    with pytest.raises(RankWeaveNotAvailable, match="digest mismatch"):
        _rank(GlobalAskExactSemanticIndex(), conn)


def test_request_never_builds_an_unprepared_or_stale_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.app.global_ask_semantic_index._import_rankweave",
        lambda: SimpleNamespace(SemanticUnitExactIndex=_OwnerIndex),
    )
    conn = _Connection()
    index = GlobalAskExactSemanticIndex()

    parameters = {
        "model_identity": "synthetic-model",
        "query_vector": [1.0, 0.0],
        "authorized_corporate_entity_ids": ["entity-a"],
        "authorized_process_unit_ids": ["unit-a"],
        "start_date": None,
        "end_date": None,
        "limit": 4,
    }
    with pytest.raises(RankWeaveNotAvailable, match="not prepared"):
        asyncio.run(index.rank_authorized(conn, **parameters))
    assert conn.snapshot_fetches == 0

    asyncio.run(
        index.prepare(conn, model_identity="synthetic-model", vector_dimension=2)
    )
    conn.projection_version = 8
    with pytest.raises(RankWeaveNotAvailable, match="not prepared"):
        asyncio.run(index.rank_authorized(conn, **parameters))
    assert conn.snapshot_fetches == 1

    conn.projection_version = 7
    conn.authorization_version = 12
    with pytest.raises(RankWeaveNotAvailable, match="not prepared"):
        asyncio.run(index.rank_authorized(conn, **parameters))


def test_failed_refresh_never_marks_stale_authorization_prepared(monkeypatch) -> None:
    """A replaced owner snapshot cannot reuse authorization from its predecessor."""
    _OwnerIndex.preflight_failure = False
    monkeypatch.setattr(
        "backend.app.global_ask_semantic_index._import_rankweave",
        lambda: SimpleNamespace(SemanticUnitExactIndex=_OwnerIndex),
    )
    conn = _Connection()
    index = GlobalAskExactSemanticIndex()

    async def exercise() -> None:
        await index.prepare(
            conn, model_identity="synthetic-model", vector_dimension=2
        )
        conn.projection_version = 8
        _OwnerIndex.preflight_failure = True
        with pytest.raises(RankWeaveNotAvailable, match="preflight failed"):
            await index.prepare(
                conn, model_identity="synthetic-model", vector_dimension=2
            )
        assert not await index.is_prepared_for(
            conn, model_identity="synthetic-model", vector_dimension=2
        )

        _OwnerIndex.preflight_failure = False
        await index.prepare(
            conn, model_identity="synthetic-model", vector_dimension=2
        )
        assert await index.is_prepared_for(
            conn, model_identity="synthetic-model", vector_dimension=2
        )

    try:
        asyncio.run(exercise())
    finally:
        _OwnerIndex.preflight_failure = False


@pytest.mark.parametrize(
    "scope_rows",
    [
        [
            {
                "entity_ids": [],
                "process_ids": [],
                "process_scope_limited": False,
            }
        ],
        [
            {
                "entity_ids": [],
                "process_ids": [],
                "process_scope_limited": False,
            },
            {
                "entity_ids": ["entity-a"],
                "process_ids": [],
                "process_scope_limited": False,
            },
            {
                "entity_ids": ["entity-a"],
                "process_ids": ["unit-a"],
                "process_scope_limited": True,
            },
        ],
    ],
)
def test_active_scopes_include_public_only_readers(monkeypatch, scope_rows) -> None:
    """Every reader contributes its local scope even without affiliation rows."""
    _OwnerIndex.preflight_failure = False
    monkeypatch.setattr(
        "backend.app.global_ask_semantic_index._import_rankweave",
        lambda: SimpleNamespace(SemanticUnitExactIndex=_OwnerIndex),
    )
    conn = _Connection()
    conn.scope_rows = scope_rows
    index = GlobalAskExactSemanticIndex()

    async def exercise() -> None:
        await index.prepare(
            conn, model_identity="synthetic-model", vector_dimension=2
        )
        scopes = await index._active_authorization_scopes(conn)
        assert index._scope([], [], process_scope_limited=False) in scopes

    asyncio.run(exercise())


def test_warm_immutable_snapshot_allows_concurrent_exact_ranking(monkeypatch) -> None:
    _ConcurrentOwnerIndex.barrier = None
    _ConcurrentOwnerIndex.batch_sizes = []
    _ConcurrentOwnerIndex.top_k_calls = []
    monkeypatch.setattr(
        "backend.app.global_ask_semantic_index._import_rankweave",
        lambda: SimpleNamespace(SemanticUnitExactIndex=_ConcurrentOwnerIndex),
    )
    index = GlobalAskExactSemanticIndex()
    _rank(index, _Connection())
    _ConcurrentOwnerIndex.batch_sizes = []
    _ConcurrentOwnerIndex.top_k_calls = []

    async def rank_twice():
        parameters = {
            "model_identity": "synthetic-model",
            "query_vector": [1.0, 0.0],
            "authorized_corporate_entity_ids": ["entity-a"],
            "authorized_process_unit_ids": ["unit-a"],
            "start_date": None,
            "end_date": None,
            "limit": 4,
        }
        first_conn = _Connection()
        second_conn = _Connection()
        results = await asyncio.gather(
            index.rank_authorized(first_conn, **parameters),
            index.rank_authorized(second_conn, **parameters),
        )
        return results, first_conn, second_conn

    (first, second), first_conn, second_conn = asyncio.run(rank_twice())
    assert first == second
    assert _ConcurrentOwnerIndex.top_k_calls == [(2, 4)]
    assert _ConcurrentOwnerIndex.batch_sizes == [2]
    assert first_conn.version_fetches + second_conn.version_fetches == 0
    assert len(first_conn.authorization_queries) + len(second_conn.authorization_queries) == 1
    assert any(
        "authorized on true" in query
        for query in first_conn.authorization_queries + second_conn.authorization_queries
    )
    _ConcurrentOwnerIndex.barrier = None


def test_date_filtered_requests_keep_complete_ranking_before_filter(monkeypatch) -> None:
    """A date predicate cannot use top-k before PostgreSQL applies the date."""
    _ConcurrentOwnerIndex.batch_sizes = []
    _ConcurrentOwnerIndex.top_k_calls = []
    monkeypatch.setattr(
        "backend.app.global_ask_semantic_index._import_rankweave",
        lambda: SimpleNamespace(SemanticUnitExactIndex=_ConcurrentOwnerIndex),
    )
    index = GlobalAskExactSemanticIndex()
    _rank(index, _Connection())
    _ConcurrentOwnerIndex.batch_sizes = []
    _ConcurrentOwnerIndex.top_k_calls = []

    async def rank_filtered() -> None:
        conn = _Connection()
        await index.rank_authorized(
            conn,
            model_identity="synthetic-model",
            query_vector=[1.0, 0.0],
            authorized_corporate_entity_ids=["entity-a"],
            authorized_process_unit_ids=["unit-a"],
            start_date=date(2026, 1, 1),
            end_date=None,
            limit=4,
        )

    asyncio.run(rank_filtered())
    assert _ConcurrentOwnerIndex.top_k_calls == []
    assert _ConcurrentOwnerIndex.batch_sizes == []


def test_distinct_authorization_digests_never_share_an_owner_batch(monkeypatch) -> None:
    """Scheduler-turn coalescing remains confined to one exact ABAC digest."""
    _ConcurrentOwnerIndex.top_k_calls = []
    monkeypatch.setattr(
        "backend.app.global_ask_semantic_index._import_rankweave",
        lambda: SimpleNamespace(SemanticUnitExactIndex=_ConcurrentOwnerIndex),
    )
    prepare_conn = _Connection()
    prepare_conn.scope_rows = [
        {
            "entity_ids": ["entity-a"],
            "process_ids": [],
            "process_scope_limited": False,
        },
        {
            "entity_ids": ["entity-b"],
            "process_ids": [],
            "process_scope_limited": False,
        },
    ]
    index = GlobalAskExactSemanticIndex()
    asyncio.run(
        index.prepare(
            prepare_conn, model_identity="synthetic-model", vector_dimension=2
        )
    )
    _ConcurrentOwnerIndex.top_k_calls = []

    async def rank_distinct_scopes() -> None:
        await asyncio.gather(
            *(
                index.rank_authorized(
                    _Connection(),
                    model_identity="synthetic-model",
                    query_vector=[1.0, 0.0],
                    authorized_corporate_entity_ids=[entity],
                    authorized_process_unit_ids=[],
                    start_date=None,
                    end_date=None,
                    limit=4,
                )
                for entity in ("entity-a", "entity-b")
            )
        )

    asyncio.run(rank_distinct_scopes())
    assert sorted(_ConcurrentOwnerIndex.top_k_calls) == [(1, 4), (1, 4)]


def test_builder_stays_inactive_without_pinned_owner_contract(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.app.global_ask_semantic_index._import_rankweave",
        lambda: SimpleNamespace(),
    )

    assert build_global_ask_exact_semantic_index() is None


def test_builder_honors_shared_rankweave_disable_switch(monkeypatch) -> None:
    """The exact owner cannot bypass the repository RankWeave kill switch."""
    monkeypatch.setattr(
        "backend.app.config.load_settings",
        lambda: SimpleNamespace(rankweave_disabled=True),
    )
    monkeypatch.setattr(
        "backend.app.global_ask_semantic_index._import_rankweave",
        lambda: SimpleNamespace(SemanticUnitExactIndex=_OwnerIndex),
    )

    assert build_global_ask_exact_semantic_index() is None
