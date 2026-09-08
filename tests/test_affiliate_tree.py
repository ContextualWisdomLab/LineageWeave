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

_ENTITIES = (
    CorporateEntityRow("group-id", None, "Demo Group", "group"),
    CorporateEntityRow("korea-id", "group-id", "Demo Electronics Korea", "company"),
    CorporateEntityRow("plant-id", "korea-id", "Demo Electronics Gwangju Plant", "plant"),
    CorporateEntityRow("other-id", "group-id", "Demo Other Division", "company"),
)

AFFILIATE_TREE_SOURCE_PATH = Path(__file__).parents[1] / "lineageweave" / "affiliate_tree.py"
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


def test_affiliate_forest_reuses_one_corroborated_alias_load(monkeypatch) -> None:
    """One request shares its alias snapshot with Keyman and forest hydration."""
    aliases = (OrganizationNameAlias("DC", "Demo Corp", "demo-id"),)

    class _Connection:
        async def fetch(self, query: str, *_args: object):
            assert "from corporate_entity" in query
            return []

    conn = _Connection()
    fetch_aliases = AsyncMock(return_value=aliases)
    fetch_keymen = AsyncMock(return_value=[])
    monkeypatch.setattr(ingestion, "fetch_corroborated_organization_aliases", fetch_aliases)
    monkeypatch.setattr(ingestion, "fetch_post_keymen", fetch_keymen)

    assert asyncio.run(ingestion.fetch_affiliate_forest(conn, "post-1")) == []
    fetch_aliases.assert_awaited_once_with(conn)
    fetch_keymen.assert_awaited_once_with(conn, "post-1", organization_aliases=aliases)


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
