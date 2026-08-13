"""Affiliate-tree forest: only the hierarchy a post's Keymen actually touch."""

from __future__ import annotations

from lineageweave.affiliate_tree import (
    AffiliationLeaf,
    CorporateEntityRow,
    build_affiliate_forest,
)

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
