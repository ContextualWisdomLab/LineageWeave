from __future__ import annotations

import asyncio

from backend.app.relation_verification_ingestion import verify_post_relations
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


class _Verifier:
    def verify(self, organization_name: str, relationship_label: str) -> RelationVerificationResult:
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
