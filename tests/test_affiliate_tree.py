"""Affiliate-tree forest: only the hierarchy a post's Keymen actually touch."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, call
from uuid import UUID

import backend.app.affiliate_tree_ingestion as ingestion
from lineageweave.affiliate_tree import (
    AffiliationLeaf,
    CorporateEntityRow,
    build_affiliate_forest,
)
from lineageweave.organization_alias import OrganizationNameAlias

_ENTITIES = (
    CorporateEntityRow("group-id", None, "Demo Group", "group"),
    CorporateEntityRow("korea-id", "group-id", "Demo Electronics Korea", "company"),
    CorporateEntityRow("plant-id", "korea-id", "Demo Electronics Gwangju Plant", "plant"),
    CorporateEntityRow("other-id", "group-id", "Demo Other Division", "company"),
)


def test_resolved_affiliation_pulls_in_ancestors_not_siblings() -> None:
    forest = build_affiliate_forest(
        _ENTITIES,
        (
            AffiliationLeaf(
                "ada", "Ada West", "our_side", "Demo Electronics Korea", "korea-id"
            ),
        ),
    )
    assert len(forest) == 1
    group = forest[0]
    assert group.entity_name == "Demo Group"
    assert group.resolved is True
    assert group.people == ()
    assert [child.entity_name for child in group.children] == ["Demo Electronics Korea"]
    korea = group.children[0]
    assert korea.people[0].person_name == "Ada West"
    assert korea.children == ()


def test_leaf_plant_includes_the_full_path_and_omits_the_unrelated_division() -> None:
    forest = build_affiliate_forest(
        _ENTITIES,
        (
            AffiliationLeaf(
                "ada",
                "Ada West",
                "our_side",
                "Demo Electronics Gwangju Plant",
                "plant-id",
            ),
        ),
    )
    group = forest[0]
    assert [child.entity_name for child in group.children] == ["Demo Electronics Korea"]
    korea = group.children[0]
    assert [child.entity_name for child in korea.children] == ["Demo Electronics Gwangju Plant"]
    assert korea.children[0].people[0].person_name == "Ada West"


def test_unresolved_organization_is_its_own_root() -> None:
    forest = build_affiliate_forest(
        _ENTITIES,
        (
            AffiliationLeaf("priya", "Priya Nair", "counterparty", "Northridge Grid", None),
            AffiliationLeaf("priya", "Priya Nair", "counterparty", "Northridge Holdings", None),
        ),
    )
    assert [node.entity_name for node in forest] == ["Northridge Grid", "Northridge Holdings"]
    assert all(node.resolved is False and node.entity_id is None for node in forest)
    assert forest[0].people[0].person_name == "Priya Nair"


def test_resolved_and_unresolved_affiliations_coexist() -> None:
    forest = build_affiliate_forest(
        _ENTITIES,
        (
            AffiliationLeaf("ada", "Ada West", "our_side", "Demo Electronics Korea", "korea-id"),
            AffiliationLeaf("priya", "Priya Nair", "counterparty", "Northridge Grid", None),
        ),
    )
    assert [node.entity_name for node in forest] == ["Demo Group", "Northridge Grid"]
    assert forest[0].resolved is True
    assert forest[1].resolved is False


def test_unknown_entity_id_is_treated_as_unresolved() -> None:
    forest = build_affiliate_forest(
        _ENTITIES,
        (AffiliationLeaf("ada", "Ada West", "our_side", "Vanished Corp", "missing-id"),),
    )
    assert len(forest) == 1
    assert forest[0].entity_name == "Vanished Corp"
    assert forest[0].resolved is False


def test_empty_affiliations_yield_an_empty_forest() -> None:
    assert build_affiliate_forest(_ENTITIES, ()) == ()


def test_to_dict_is_the_api_shape() -> None:
    forest = build_affiliate_forest(
        _ENTITIES,
        (AffiliationLeaf("ada", "Ada West", "our_side", "Demo Electronics Korea", "korea-id"),),
    )
    payload = forest[0].to_dict()
    assert payload["entity_name"] == "Demo Group"
    assert payload["resolved"] is True
    assert payload["children"][0]["people"][0]["person_name"] == "Ada West"


def test_affiliate_forest_skips_alias_catalog_when_no_keymen(monkeypatch) -> None:
    """A post with no affiliations must not load the organization alias catalog."""

    class _Connection:
        async def fetch(self, _query: str, *_args: object):
            raise AssertionError("no corporate hierarchy query is needed without resolved affiliations")

    conn = _Connection()
    fetch_aliases = AsyncMock(return_value=())
    fetch_keymen = AsyncMock(return_value=[])
    monkeypatch.setattr(ingestion, "fetch_corroborated_organization_aliases", fetch_aliases)
    monkeypatch.setattr(ingestion, "fetch_post_keymen", fetch_keymen)

    assert asyncio.run(ingestion.fetch_affiliate_forest(conn, "post-1")) == []
    fetch_aliases.assert_not_awaited()
    fetch_keymen.assert_awaited_once_with(conn, "post-1", organization_aliases=())


def test_affiliate_forest_bounds_alias_lookup_to_unresolved_names(monkeypatch) -> None:
    """Resolution and display aliases stay bounded to this post's names."""
    demo_id = UUID("00000000-0000-0000-0000-000000000002")
    aliases = (OrganizationNameAlias("Demo Co", "Demo Corp", str(demo_id)),)
    raw_keymen = [
        {
            "person_id": "ada",
            "person_name": "Ada West",
            "person_side_code": "our_side",
            "affiliations": [
                {
                    "organization_name": "Demo Co",
                    "corporate_entity_id": None,
                }
            ],
        }
    ]
    resolved_keymen = [
        {
            "person_id": "ada",
            "person_name": "Ada West",
            "person_side_code": "our_side",
            "affiliations": [
                {
                    "organization_name": "Demo Corp",
                    "corporate_entity_id": str(demo_id),
                }
            ],
        }
    ]

    class _Connection:
        async def fetch(self, query: str, *_args: object):
            assert "with recursive affiliate_entity" in query.lower()
            return [
                {
                    "corporate_entity_id": demo_id,
                    "parent_entity_id": None,
                    "entity_name": "Demo Corp",
                    "entity_level_code": "company",
                }
            ]

    conn = _Connection()
    fetch_aliases = AsyncMock(return_value=aliases)
    fetch_keymen = AsyncMock(side_effect=[raw_keymen, resolved_keymen])
    attach_labels = AsyncMock()
    monkeypatch.setattr(ingestion, "fetch_corroborated_organization_aliases", fetch_aliases)
    monkeypatch.setattr(ingestion, "fetch_post_keymen", fetch_keymen)
    monkeypatch.setattr(ingestion, "_attach_lookup_labels", attach_labels)

    forest = asyncio.run(ingestion.fetch_affiliate_forest(conn, "post-1"))

    assert fetch_aliases.await_args_list == [
        call(conn, organization_names=("Demo Co",)),
        call(conn, organization_names=("Demo Co", "Demo Corp")),
    ]
    assert fetch_keymen.await_args_list == [
        call(conn, "post-1", organization_aliases=()),
        call(conn, "post-1", organization_aliases=aliases),
    ]
    assert forest[0]["entity_name"] == "Demo Corp"


def test_affiliate_forest_loads_only_resolved_affiliation_ancestor_closure(monkeypatch) -> None:
    """Hierarchy and alias reads both stay inside the touched organization closure."""
    group_id = UUID("00000000-0000-0000-0000-000000000001")
    company_id = UUID("00000000-0000-0000-0000-000000000002")
    unrelated_id = UUID("00000000-0000-0000-0000-000000000003")
    observed_calls: list[tuple[str, tuple[object, ...]]] = []

    class _Connection:
        async def fetch(self, query: str, *args: object):
            observed_calls.append((query, args))
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
                    "entity_name": "Demo Electronics Korea",
                    "entity_level_code": "company",
                },
            ]

    fetch_aliases = AsyncMock(return_value=())
    fetch_keymen = AsyncMock(
        return_value=[
            {
                "person_id": "ada",
                "person_name": "Ada West",
                "person_side_code": "our_side",
                "affiliations": [
                    {
                        "organization_name": "Demo Electronics Korea",
                        "corporate_entity_id": str(company_id),
                    },
                    {
                        "organization_name": "Unresolved Supplier",
                        "corporate_entity_id": None,
                    },
                ],
            }
        ]
    )
    attach_labels = AsyncMock()
    monkeypatch.setattr(ingestion, "fetch_corroborated_organization_aliases", fetch_aliases)
    monkeypatch.setattr(ingestion, "fetch_post_keymen", fetch_keymen)
    monkeypatch.setattr(ingestion, "_attach_lookup_labels", attach_labels)

    conn = _Connection()
    forest = asyncio.run(ingestion.fetch_affiliate_forest(conn, "post-1"))

    assert fetch_aliases.await_args_list == [
        call(conn, organization_names=("Unresolved Supplier",)),
        call(
            conn,
            organization_names=(
                "Demo Electronics Korea",
                "Demo Group",
                "Unresolved Supplier",
            ),
        ),
    ]
    assert len(observed_calls) == 1
    query, args = observed_calls[0]
    assert "with recursive affiliate_entity" in query.lower()
    assert "corporate_entity_id = any($1::uuid[])" in query.lower()
    assert args == ([company_id],)
    assert unrelated_id not in args[0]
    assert [node["entity_name"] for node in forest] == ["Demo Group", "Unresolved Supplier"]
    attach_labels.assert_awaited_once()


def test_voc_evidence_skips_unused_organization_aliases(monkeypatch) -> None:
    """VOC excerpts need affiliation names, not alias decoration or its query."""

    conn = AsyncMock()
    conn.fetchrow.side_effect = [{"lookup_label": "VOC"}, {"post_body": "Demo Corp update."}]
    conn.fetch.return_value = []
    fetch_keymen = AsyncMock(return_value=[])
    monkeypatch.setattr(ingestion, "fetch_post_keymen", fetch_keymen)

    payload = asyncio.run(ingestion.fetch_voc_evidence(conn, "post-1", "voc"))

    assert payload["voc_type_label"] == "VOC"
    fetch_keymen.assert_awaited_once_with(conn, "post-1", organization_aliases=())
