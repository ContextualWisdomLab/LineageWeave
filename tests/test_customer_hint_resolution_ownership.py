"""Regression contract for customer-hint identity versus authorization ownership."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import backend.app.customer_hint_ingestion as ingestion
from lineageweave.relation_verification import STATUS_CORROBORATED


class _ResolutionClient:
    available = True


class _VerificationClient:
    pass


class _ScopedConnection:
    """Reject evidence reads that are not explicitly bound to caller scope."""

    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, query: str, *args: object):
        normalized = " ".join(query.lower().split())
        self.executed.append((normalized, args))
        if "from source_post" in normalized and "select" in normalized:
            assert "corporate_entity_id" in normalized
            assert "process_unit_id" in normalized
            assert args[:3] == (["corp-a"], ["pu-a"], "0019999999")
            return [
                {
                    "post_id": "post-a",
                    "post_title": "Authorized visit",
                    "post_body": "<p>Authorized evidence</p>",
                }
            ]
        if "insert into source_post_customer_resolution" in normalized:
            return [{"post_id": "post-a"}]
        assert "update source_post" not in normalized
        return []

    async def fetchrow(self, query: str, *args: object):
        normalized = " ".join(query.lower().split())
        self.executed.append((normalized, args))
        if "from corporate_entity" in normalized:
            return {"corporate_entity_id": "customer-entity"}
        return None


def _resolution():
    return SimpleNamespace(
        raw_organization_name="0019999999",
        resolved_organization_name="Northridge Grid",
        verification_status_code=STATUS_CORROBORATED,
        verification_evidence_url="https://evidence.example/result",
    )


def test_resolution_is_scope_bound_and_does_not_rebind_source_ownership(monkeypatch) -> None:
    monkeypatch.setattr(
        ingestion,
        "resolve_and_verify_organization_name",
        lambda *_args: _resolution(),
    )
    connection = _ScopedConnection()

    result = asyncio.run(
        ingestion.resolve_customer_hint(
            connection,
            _ResolutionClient(),
            _VerificationClient(),
            "0019999999",
            ["corp-a"],
            ["pu-a"],
        )
    )

    assert result["corporate_entity_id"] == "customer-entity"
    assert result["linked_post_count"] == 1
    assert all("update source_post" not in query for query, _ in connection.executed)
    assert any(
        "insert into source_post_customer_resolution" in query
        for query, _ in connection.executed
    )
