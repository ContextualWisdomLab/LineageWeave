"""Regression tests that keep tied organization names out of AUTO rows."""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from typing import Any

from backend.app import corporate_entity_ingestion, keyman_ingestion
from lineageweave.corporate_hierarchy_inference import HierarchyProposal
from lineageweave.corporate_hierarchy_resolution import CorporateEntityCandidate
from lineageweave.relation_verification import STATUS_CORROBORATED


_TIED_CANDIDATES = [
    CorporateEntityCandidate("tied-a", "Tied Energy"),
    CorporateEntityCandidate("tied-b", "Tied Energy"),
]


class _LiveInferenceClient:
    """Return a creatable root-company proposal if a tie leaks through."""

    available = True

    def __init__(self) -> None:
        self.calls = 0

    def infer(self, organization_name: str, context_text: str) -> HierarchyProposal:
        self.calls += 1
        return HierarchyProposal(level_code="company", parent_name=None)


class _LiveVerificationClient:
    """Corroborate every proposal if a tie leaks through."""

    available = True

    def __init__(self) -> None:
        self.calls = 0

    def verify(self, subject: str, relation: str) -> SimpleNamespace:
        self.calls += 1
        return SimpleNamespace(status_code=STATUS_CORROBORATED)


class _TimeoutInferenceClient:
    """Simulate an unavailable orchestrator during hierarchy enrichment."""

    available = True

    def infer(self, organization_name: str, context_text: str) -> HierarchyProposal:
        raise TimeoutError("synthetic orchestrator timeout")


class _Transaction:
    """Minimal async transaction context manager."""

    async def __aenter__(self) -> "_Transaction":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        return False


class _ReloadTieConnection:
    """Expose a tie only after inference and the advisory lock."""

    def __init__(self) -> None:
        self.insert_attempted = False

    def transaction(self) -> _Transaction:
        return _Transaction()

    async def execute(self, query: str, *args: Any) -> str:
        assert "pg_advisory_xact_lock" in query
        return "SELECT 1"

    async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
        if "organization_name_resolution" in query:
            return []
        assert "from corporate_entity" in query
        return [
            {
                "corporate_entity_id": uuid.uuid4(),
                "entity_name": "Tied Energy",
            },
            {
                "corporate_entity_id": uuid.uuid4(),
                "entity_name": "Tied Energy",
            },
        ]

    async def fetchrow(self, query: str, *args: Any) -> dict[str, Any]:
        self.insert_attempted = True
        raise AssertionError("a refreshed tie must not insert an AUTO row")


def test_initial_tie_never_reaches_live_inference_or_creation() -> None:
    """A known tie returns before any live external client is consulted."""
    inference = _LiveInferenceClient()
    verification = _LiveVerificationClient()

    result = asyncio.run(
        corporate_entity_ingestion.get_or_create_corporate_entity(
            object(),
            "Tied Energy",
            "Synthetic context",
            inference,
            verification,
            list(_TIED_CANDIDATES),
        )
    )

    assert result is None
    assert inference.calls == 0
    assert verification.calls == 0


def test_hierarchy_timeout_leaves_actor_unbound_without_raising() -> None:
    """Enrichment outage must not discard a source-grounded summary."""
    result = asyncio.run(
        corporate_entity_ingestion.get_or_create_corporate_entity(
            object(),
            "Unresolved Energy",
            "Synthetic context",
            _TimeoutInferenceClient(),
            _LiveVerificationClient(),
            [],
        )
    )

    assert result is None


def test_tie_discovered_under_creation_lock_does_not_insert() -> None:
    """Concurrent homonyms discovered after inference still fail closed."""
    connection = _ReloadTieConnection()
    inference = _LiveInferenceClient()
    verification = _LiveVerificationClient()

    result = asyncio.run(
        corporate_entity_ingestion.get_or_create_corporate_entity(
            connection,
            "Tied Energy",
            "Synthetic context",
            inference,
            verification,
            [],
        )
    )

    assert result is None
    assert inference.calls == 1
    assert verification.calls == 1
    assert connection.insert_attempted is False


def test_keyman_raw_tie_blocks_abbreviation_rewrite_and_auto_creation() -> None:
    """Keyman checks the raw tied name before any resolver rewrite."""
    result = asyncio.run(
        keyman_ingestion._resolve_affiliated_organization(
            object(),
            "Tied Energy",
            "Synthetic context",
            object(),
            object(),
            object(),
            list(_TIED_CANDIDATES),
        )
    )

    assert result == ("Tied Energy", "Tied Energy", None)
