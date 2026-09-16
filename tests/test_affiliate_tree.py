"""Affiliate-tree forest: only the hierarchy a post's Keymen actually touch."""

from __future__ import annotations

import asyncio
import ast
from pathlib import Path
from unittest.mock import AsyncMock

import backend.app.affiliate_tree_ingestion as ingestion
from lineageweave.affiliate_tree import (
    AffiliationLeaf,
    CorporateEntityRow,
    build_affiliate_forest,
)
from lineageweave.organization_alias import OrganizationNameAlias

_CORPORATE_ENTITIES = (
    CorporateEntityRow("group-id", None, "Demo Group", "group"),
    CorporateEntityRow("korea-id", "group-id", "Demo Electronics Korea", "company"),
    CorporateEntityRow(
        "plant-id", "korea-id", "Demo Electronics Gwangju Plant", "plant"
    ),
    CorporateEntityRow("other-id", "group-id", "Demo Other Division", "company"),
)

AFFILIATE_TREE_SOURCE_PATH = (
    Path(__file__).parents[1] / "lineageweave" / "affiliate_tree.py"
)
FORBIDDEN_AFFILIATE_TREE_IDENTIFIERS = {
    "affiliations",
    "child",
    "current",
    "entities",
    "leaf",
    "leaves",
    "name",
    "needed",
    "person",
    "row",
    "unique",
}


def test_affiliate_tree_builder_uses_hierarchy_specific_identifiers() -> None:
    """Keep private builder names aligned with the affiliate-tree domain."""
    source_tree = ast.parse(AFFILIATE_TREE_SOURCE_PATH.read_text(encoding="utf-8"))
    owned_identifiers = {
        syntax_node.id
        for syntax_node in ast.walk(source_tree)
        if isinstance(syntax_node, ast.Name)
    }
    owned_identifiers.update(
        syntax_node.arg
        for syntax_node in ast.walk(source_tree)
        if isinstance(syntax_node, ast.arg)
    )
    owned_function_names = {
        syntax_node.name
        for syntax_node in ast.walk(source_tree)
        if isinstance(syntax_node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert not (FORBIDDEN_AFFILIATE_TREE_IDENTIFIERS & owned_identifiers)
    assert "_build" not in owned_function_names
    assert {
        "affiliate_person",
        "affiliation_leaf",
        "corporate_entities",
        "corporate_entity_row",
        "needed_entity_ids",
        "resolved_affiliation_leaves",
    } <= owned_identifiers
    assert "_build_affiliate_node" in owned_function_names


def test_resolved_affiliation_pulls_in_ancestors_not_siblings() -> None:
    affiliate_forest = build_affiliate_forest(
        _CORPORATE_ENTITIES,
        (
            AffiliationLeaf(
                "ada", "Ada West", "our_side", "Demo Electronics Korea", "korea-id"
            ),
        ),
    )
    assert len(affiliate_forest) == 1
    group_node = affiliate_forest[0]
    assert group_node.entity_name == "Demo Group"
    assert group_node.resolved is True
    assert group_node.people == ()
    assert [child_node.entity_name for child_node in group_node.children] == [
        "Demo Electronics Korea"
    ]
    korea_node = group_node.children[0]
    assert korea_node.people[0].person_name == "Ada West"
    assert korea_node.children == ()


def test_leaf_plant_includes_the_full_path_and_omits_the_unrelated_division() -> None:
    affiliate_forest = build_affiliate_forest(
        _CORPORATE_ENTITIES,
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
    group_node = affiliate_forest[0]
    assert [child_node.entity_name for child_node in group_node.children] == [
        "Demo Electronics Korea"
    ]
    korea_node = group_node.children[0]
    assert [child_node.entity_name for child_node in korea_node.children] == [
        "Demo Electronics Gwangju Plant"
    ]
    assert korea_node.children[0].people[0].person_name == "Ada West"


def test_unresolved_organization_is_its_own_root() -> None:
    affiliate_forest = build_affiliate_forest(
        _CORPORATE_ENTITIES,
        (
            AffiliationLeaf(
                "priya", "Priya Nair", "counterparty", "Northridge Grid", None
            ),
            AffiliationLeaf(
                "priya", "Priya Nair", "counterparty", "Northridge Holdings", None
            ),
        ),
    )
    assert [affiliate_node.entity_name for affiliate_node in affiliate_forest] == [
        "Northridge Grid",
        "Northridge Holdings",
    ]
    assert all(
        affiliate_node.resolved is False and affiliate_node.entity_id is None
        for affiliate_node in affiliate_forest
    )
    assert affiliate_forest[0].people[0].person_name == "Priya Nair"


def test_resolved_and_unresolved_affiliations_coexist() -> None:
    affiliate_forest = build_affiliate_forest(
        _CORPORATE_ENTITIES,
        (
            AffiliationLeaf(
                "ada", "Ada West", "our_side", "Demo Electronics Korea", "korea-id"
            ),
            AffiliationLeaf(
                "priya", "Priya Nair", "counterparty", "Northridge Grid", None
            ),
        ),
    )
    assert [affiliate_node.entity_name for affiliate_node in affiliate_forest] == [
        "Demo Group",
        "Northridge Grid",
    ]
    assert affiliate_forest[0].resolved is True
    assert affiliate_forest[1].resolved is False


def test_unknown_entity_id_is_treated_as_unresolved() -> None:
    affiliate_forest = build_affiliate_forest(
        _CORPORATE_ENTITIES,
        (
            AffiliationLeaf(
                "ada", "Ada West", "our_side", "Vanished Corp", "missing-id"
            ),
        ),
    )
    assert len(affiliate_forest) == 1
    assert affiliate_forest[0].entity_name == "Vanished Corp"
    assert affiliate_forest[0].resolved is False


def test_empty_affiliations_yield_an_empty_forest() -> None:
    assert build_affiliate_forest(_CORPORATE_ENTITIES, ()) == ()


def test_to_dict_is_the_api_shape() -> None:
    affiliate_forest = build_affiliate_forest(
        _CORPORATE_ENTITIES,
        (
            AffiliationLeaf(
                "ada", "Ada West", "our_side", "Demo Electronics Korea", "korea-id"
            ),
        ),
    )
    api_payload = affiliate_forest[0].to_dict()
    assert api_payload["entity_name"] == "Demo Group"
    assert api_payload["resolved"] is True
    assert api_payload["children"][0]["people"][0]["person_name"] == "Ada West"


def test_affiliate_forest_reuses_one_corroborated_alias_load(monkeypatch) -> None:
    """One request shares its alias snapshot with Keyman and forest hydration."""
    organization_aliases = (OrganizationNameAlias("DC", "Demo Corp", "demo-id"),)

    class _DatabaseConnection:
        async def fetch(self, database_query: str, *_args: object):
            assert "from corporate_entity" in database_query
            return []

    database_connection = _DatabaseConnection()
    fetch_organization_aliases = AsyncMock(return_value=organization_aliases)
    fetch_post_keymen = AsyncMock(return_value=[])
    monkeypatch.setattr(
        ingestion,
        "fetch_corroborated_organization_aliases",
        fetch_organization_aliases,
    )
    monkeypatch.setattr(ingestion, "fetch_post_keymen", fetch_post_keymen)

    assert (
        asyncio.run(ingestion.fetch_affiliate_forest(database_connection, "post-1"))
        == []
    )
    fetch_organization_aliases.assert_awaited_once_with(database_connection)
    fetch_post_keymen.assert_awaited_once_with(
        database_connection,
        "post-1",
        organization_aliases=organization_aliases,
    )


def test_voc_evidence_skips_unused_organization_aliases(monkeypatch) -> None:
    """VOC excerpts need affiliation names, not alias decoration or its query."""

    database_connection = AsyncMock()
    database_connection.fetchrow.side_effect = [
        {"lookup_label": "VOC"},
        {"post_body": "Demo Corp update."},
    ]
    database_connection.fetch.return_value = []
    fetch_post_keymen = AsyncMock(return_value=[])
    monkeypatch.setattr(ingestion, "fetch_post_keymen", fetch_post_keymen)

    voc_evidence_payload = asyncio.run(
        ingestion.fetch_voc_evidence(database_connection, "post-1", "voc")
    )

    assert voc_evidence_payload["voc_type_label"] == "VOC"
    fetch_post_keymen.assert_awaited_once_with(
        database_connection,
        "post-1",
        organization_aliases=(),
    )
