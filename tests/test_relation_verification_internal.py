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
    def __init__(self, evidence_post_id: str | None, update_status: str = "UPDATE 1") -> None:
        self.evidence_post_id = evidence_post_id
        self.update_status = update_status
        self.fetchrow_args: tuple[object, ...] | None = None
        self.execute_args: tuple[object, ...] | None = None
        self.execute_calls: list[tuple[object, ...]] = []

    async def fetch(self, query: str, post_id: str):
        assert "verification_status_code = 'verify_pending'" in query
        return [
            {
                "counterparty_entity_name": "Example Partner",
                "relationship_type_code": "partner",
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
        assert "$5::uuid is null or exists" in query
        self.execute_args = args
        self.execute_calls.append(args)
        return self.update_status

    def transaction(self):
        return _Transaction()


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _Acquire:
    def __init__(self, pool: _Pool) -> None:
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
        "partner",
    )


def test_relation_verification_keeps_external_result_when_internal_search_misses() -> None:
    conn = _Connection(None)

    verified = asyncio.run(verify_post_relations(conn, _Verifier(), "origin-post"))

    assert verified[0].verification_evidence_post_id is None
    assert conn.execute_args is not None
    assert conn.execute_args[-2] is None
    assert conn.execute_args[-1] == "partner"


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


def test_pool_verification_counts_only_rows_settled_by_this_worker() -> None:
    """A concurrent winner is not reported as work persisted by this request."""
    conn = _Connection("internal-post", update_status="UPDATE 0")
    pool = _Pool(conn)

    verified = asyncio.run(
        verify_post_relations_from_pool(pool, _Verifier(pool), "origin-post")
    )

    assert verified == []


def test_pool_verification_persists_completed_rows_before_provider_failure() -> None:
    """A later provider failure does not roll back an earlier completed row."""

    class _TwoRelationConnection(_Connection):
        async def fetch(self, query: str, post_id: str):
            assert "verification_status_code = 'verify_pending'" in query
            return [
                {
                    "counterparty_entity_name": "Example Partner",
                    "relationship_type_code": "partner",
                    "relationship_label": "Partner",
                },
                {
                    "counterparty_entity_name": "Example Supplier",
                    "relationship_type_code": "supplier",
                    "relationship_label": "Supplier",
                },
            ]

    class _FailingSecondVerifier:
        def verify(
            self, organization_name: str, relationship_label: str
        ) -> RelationVerificationResult:
            if organization_name == "Example Supplier":
                raise RuntimeError("synthetic provider failure")
            return RelationVerificationResult(
                STATUS_CORROBORATED, "https://example.test/evidence"
            )

    conn = _TwoRelationConnection(None)

    with pytest.raises(RuntimeError, match="synthetic provider failure"):
        asyncio.run(
            verify_post_relations_from_pool(
                _Pool(conn), _FailingSecondVerifier(), "origin-post"
            )
        )

    assert len(conn.execute_calls) == 1
    assert conn.execute_calls[0][-1] == "partner"
