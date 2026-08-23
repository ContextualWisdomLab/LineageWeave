"""SKOS alt/pref round-trip binds two synthetic names to one catalog row."""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from typing import Any

from backend.app import corporate_entity_ingestion
from lineageweave.corporate_hierarchy_inference import HierarchyProposal
from lineageweave.corporate_hierarchy_resolution import (
    CorporateEntityCandidate,
    OrganizationNameAlias,
)
from lineageweave.relation_verification import STATUS_CORROBORATED


_AGP_ALIAS = OrganizationNameAlias(alt_label="AGP", pref_label="Aurora Grid Power")
_SYNTHETIC_CONTEXT = "AGP (Aurora Grid Power) joined the synthetic grid forum."


class _RejectInferenceClient:
    available = False

    def infer(self, organization_name: str, context_text: str) -> HierarchyProposal:
        raise AssertionError(f"alias binding must not create {organization_name!r}")


class _RejectVerificationClient:
    available = False

    def verify(self, subject: str, relation: str) -> SimpleNamespace:
        raise AssertionError("alias binding must not call live search")


class _CreateIfReachedInferenceClient:
    available = True

    def infer(self, organization_name: str, context_text: str) -> HierarchyProposal:
        return HierarchyProposal(level_code="company", parent_name=None)


class _CreateIfReachedVerificationClient:
    available = True

    def verify(self, subject: str, relation: str) -> SimpleNamespace:
        return SimpleNamespace(status_code=STATUS_CORROBORATED)


class _AliasLockConnection:
    """Serve corroborated aliases and a catalog row stored under the altLabel."""

    def __init__(self, catalog_id: str, entity_name: str) -> None:
        self.catalog_id = catalog_id
        self.entity_name = entity_name
        self.insert_attempted = False

    class _Transaction:
        async def __aenter__(self) -> "_AliasLockConnection._Transaction":
            return self

        async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
            return False

    def transaction(self) -> "_AliasLockConnection._Transaction":
        return self._Transaction()

    async def execute(self, query: str, *args: Any) -> str:
        assert "pg_advisory_xact_lock" in query
        return "SELECT 1"

    async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
        if "organization_name_resolution" in query:
            assert args == (STATUS_CORROBORATED,)
            return [
                {
                    "raw_organization_name": "AGP",
                    "resolved_organization_name": "Aurora Grid Power",
                }
            ]
        assert "from corporate_entity" in query
        return [
            {
                "corporate_entity_id": self.catalog_id,
                "entity_name": self.entity_name,
            }
        ]

    async def fetchrow(self, query: str, *args: Any) -> dict[str, Any]:
        self.insert_attempted = True
        raise AssertionError("alias round-trip must reuse the existing catalog row")


def test_short_form_mention_reuses_pref_label_catalog_row() -> None:
    catalog_id = str(uuid.uuid4())
    result = asyncio.run(
        corporate_entity_ingestion.get_or_create_corporate_entity(
            object(),
            "AGP",
            _SYNTHETIC_CONTEXT,
            _RejectInferenceClient(),
            _RejectVerificationClient(),
            [CorporateEntityCandidate(catalog_id, "Aurora Grid Power")],
            aliases=[_AGP_ALIAS],
        )
    )
    assert result == catalog_id


def test_pref_label_mention_reuses_alt_label_catalog_row_under_creation_lock() -> None:
    catalog_id = str(uuid.uuid4())
    connection = _AliasLockConnection(catalog_id, "AGP")
    result = asyncio.run(
        corporate_entity_ingestion.get_or_create_corporate_entity(
            connection,
            "Aurora Grid Power",
            _SYNTHETIC_CONTEXT,
            _CreateIfReachedInferenceClient(),
            _CreateIfReachedVerificationClient(),
            [],
        )
    )
    assert result == catalog_id
    assert connection.insert_attempted is False


def test_uncorroborated_alias_does_not_bind() -> None:
    result = asyncio.run(
        corporate_entity_ingestion.get_or_create_corporate_entity(
            object(),
            "AGP",
            _SYNTHETIC_CONTEXT,
            _RejectInferenceClient(),
            _RejectVerificationClient(),
            [CorporateEntityCandidate(str(uuid.uuid4()), "Aurora Grid Power")],
            aliases=(),
        )
    )
    assert result is None
