"""Bounded alias behavior for the buyer-facing Affiliate Tree."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import backend.app.affiliate_tree_ingestion as ingestion
from lineageweave.organization_alias import OrganizationNameAlias


def test_loaded_hierarchy_keeps_relevant_aliases_without_global_alias_scan(monkeypatch) -> None:
    """Touched resolved entities retain aliases selected only by their names."""
    group_id = UUID("00000000-0000-0000-0000-000000000001")
    company_id = UUID("00000000-0000-0000-0000-000000000002")
    keymen = [
        {
            "person_id": "ada",
            "person_name": "Ada West",
            "person_side_code": "our_side",
            "affiliations": [
                {
                    "organization_name": "Demo Corp",
                    "corporate_entity_id": str(company_id),
                }
            ],
        }
    ]
    relevant_aliases = (
        OrganizationNameAlias("DG", "Demo Group", str(group_id)),
        OrganizationNameAlias("DC", "Demo Corp", str(company_id)),
    )

    class _Connection:
        async def fetch(self, query: str, *_args: object):
            assert "with recursive affiliate_entity" in query.lower()
            return [
                {
                    "corporate_entity_id": group_id,
                    "parent_entity_id": None,
                    "entity_name": "Demo Group",
                    "entity_level_code": "group",
                },
                {
                    "corporate_entity_id": company_id,
                    "parent_entity_id": group_id,
                    "entity_name": "Demo Corp",
                    "entity_level_code": "company",
                },
            ]

    conn = _Connection()
    fetch_keymen = AsyncMock(return_value=keymen)
    fetch_aliases = AsyncMock(return_value=relevant_aliases)
    attach_labels = AsyncMock()
    attach_aliases = Mock()
    monkeypatch.setattr(ingestion, "fetch_post_keymen", fetch_keymen)
    monkeypatch.setattr(ingestion, "fetch_corroborated_organization_aliases", fetch_aliases)
    monkeypatch.setattr(ingestion, "_attach_lookup_labels", attach_labels)
    monkeypatch.setattr(ingestion, "attach_organization_aliases", attach_aliases)

    forest = asyncio.run(ingestion.fetch_affiliate_forest(conn, "post-1"))

    fetch_keymen.assert_awaited_once_with(conn, "post-1", organization_aliases=())
    fetch_aliases.assert_awaited_once_with(
        conn,
        organization_names=("Demo Corp", "Demo Group"),
    )
    attach_aliases.assert_called_once_with(
        forest,
        relevant_aliases,
        entity_id_key="entity_id",
    )
