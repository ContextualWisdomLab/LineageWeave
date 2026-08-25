from __future__ import annotations

import asyncio

import pytest

from backend.app.relation_verification_ingestion import (
    verify_post_relations,
    verify_post_relations_from_pool,
)
from lineageweave.relation_verification import (
    STATUS_CORROBORATED,
    RelationVerificationResult,
)


class _Connection:
    def __init__(self, evidence_post_id: str | None) -> None:
        self.evidence_post_id = evidence_post_id
        self.fetchrow_args: tuple[object, ...] | None = None
        self.execute_args: tuple[object, ...] | None = None

    async def fetch(self, query: str, post_id: str):
        assert "verification_status_code = 'verify_pending'" in query
        return [
            {
                "counterparty_entity_name": "Example Partner",
                "relationship_label": "Partner",
            }
        ]

    async def fetchrow(self, query: str, *args: object):
        assert "post_content_unit" in query
        assert "visibility_code = 'public'" in query
        self.fetchrow_args = args
        return None if self.evidence_post_id is None else {"post_id": self.evidence_post_id}

    async def execute(self, query: str, *args: object):
        assert "verification_evidence_post_id = $5" in query
        self.execute_args = args
        return "UPDATE 1"

    def transaction(self):
        return _Transaction()


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _Acquire:
    def __init__(self, pool: "_Pool") -> None:
        self.pool = pool

    async def __aenter__(self):
        assert not self.pool.acquired
        self.pool.acquired = True
        return self.pool.connection

    async def __aexit__(self, exc_type, exc, traceback):
        self.pool.acquired = False


class _Pool:
    def __init__(self, connection: _Connection) -> None:
        self.connection = connection
        self.acquired = False

    def acquire(self):
        return _Acquire(self)


class _Verifier:
    def __init__(self, pool: _Pool | None = None) -> None:
        self.pool = pool

    def verify(self, organization_name: str, relationship_label: str) -> RelationVerificationResult:
        if self.pool is not None:
            assert not self.pool.acquired
        assert (organization_name, relationship_label) == ("Example Partner", "Partner")
        return RelationVerificationResult(STATUS_CORROBORATED, "https://example.test/evidence")


def test_relation_verification_persists_authorized_internal_evidence() -> None:
    conn = _Connection("internal-post")

    verified = asyncio.run(
        verify_post_relations(conn, _Verifier(), "origin-post", visible_corporate_entity_ids=("corp-a",))
    )

    assert verified[0].verification_evidence_post_id == "internal-post"
    assert conn.fetchrow_args == ("origin-post", "Example Partner", "Partner", ["corp-a"])
    assert conn.execute_args == (
        "origin-post",
        "Example Partner",
        STATUS_CORROBORATED,
        "https://example.test/evidence",
        "internal-post",
    )


def test_relation_verification_keeps_external_result_when_internal_search_misses() -> None:
    conn = _Connection(None)

    verified = asyncio.run(verify_post_relations(conn, _Verifier(), "origin-post"))

    assert verified[0].verification_evidence_post_id is None
    assert conn.execute_args is not None
    assert conn.execute_args[-1] is None


def test_pool_connection_is_released_during_external_verification() -> None:
    conn = _Connection("internal-post")
    pool = _Pool(conn)

    verified = asyncio.run(
        verify_post_relations_from_pool(
            pool,
            _Verifier(pool),
            "origin-post",
            visible_corporate_entity_ids=("corp-a",),
        )
    )

    assert verified[0].verification_status_code == STATUS_CORROBORATED
    assert not pool.acquired


def test_pool_verification_persists_completed_rows_before_provider_failure() -> None:
    class MultiConnection(_Connection):
        def __init__(self) -> None:
            super().__init__(None)
            self.persisted_names: list[str] = []

        async def fetch(self, query: str, post_id: str):
            assert "verification_status_code = 'verify_pending'" in query
            return [
                {
                    "counterparty_entity_name": "Example Partner",
                    "relationship_label": "Partner",
                },
                {
                    "counterparty_entity_name": "Unavailable Partner",
                    "relationship_label": "Partner",
                },
            ]

        async def execute(self, query: str, *args: object):
            assert "verification_evidence_post_id = $5" in query
            self.persisted_names.append(str(args[1]))
            return "UPDATE 1"

    class FailingVerifier:
        def verify(
            self, organization_name: str, relationship_label: str
        ) -> RelationVerificationResult:
            assert relationship_label == "Partner"
            if organization_name == "Unavailable Partner":
                raise OSError("synthetic provider failure")
            return RelationVerificationResult(
                STATUS_CORROBORATED, "https://example.test/evidence"
            )

    conn = MultiConnection()
    pool = _Pool(conn)

    with pytest.raises(OSError, match="synthetic provider failure"):
        asyncio.run(
            verify_post_relations_from_pool(pool, FailingVerifier(), "origin-post")
        )

    assert conn.persisted_names == ["Example Partner"]
    assert not pool.acquired


def test_pool_verification_omits_relation_completed_by_concurrent_run() -> None:
    class ConcurrentConnection(_Connection):
        async def execute(self, query: str, *args: object):
            assert "verification_status_code = 'verify_pending'" in query
            return "UPDATE 0"

    conn = ConcurrentConnection(None)
    pool = _Pool(conn)

    verified = asyncio.run(
        verify_post_relations_from_pool(pool, _Verifier(pool), "origin-post")
    )

    assert verified == []
    assert not pool.acquired
