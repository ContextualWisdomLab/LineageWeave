"""Authorized customer-group forest: affiliated rows plus ancestors/descendants."""

from __future__ import annotations

from lineageweave.customer_group_tree import (
    CatalogEntityRow,
    TreeAbbreviation,
    authorized_catalog_ids,
    build_customer_group_forest,
)

_ENTITIES = (
    CatalogEntityRow("group-id", None, "Demo Group", "group"),
    CatalogEntityRow("corp-id", "group-id", "Demo Corp", "company"),
    CatalogEntityRow("plant-id", "corp-id", "Demo Plant", "plant"),
    CatalogEntityRow("other-id", None, "Other Corp", "group"),
)


def test_affiliated_company_includes_group_parent_and_plant_child() -> None:
    needed = authorized_catalog_ids(_ENTITIES, ("corp-id",))
    assert needed == {"group-id", "corp-id", "plant-id"}


def test_unaffiliated_sibling_group_is_omitted() -> None:
    forest = build_customer_group_forest(_ENTITIES, ("corp-id",))
    assert [node.entity_name for node in forest] == ["Demo Group"]
    group = forest[0]
    assert [child.entity_name for child in group.children] == ["Demo Corp"]
    assert [child.entity_name for child in group.children[0].children] == ["Demo Plant"]


def test_unknown_affiliation_adds_no_invented_parent() -> None:
    forest = build_customer_group_forest(_ENTITIES, ("missing-id",))
    assert forest == ()


def test_broken_parent_pointer_stops_without_inventing_an_ancestor() -> None:
    broken = (
        CatalogEntityRow("corp-id", "missing-parent", "Demo Corp", "company"),
    )
    assert authorized_catalog_ids(broken, ("corp-id",)) == {"corp-id"}


def test_already_included_descendant_is_not_walked_twice() -> None:
    needed = authorized_catalog_ids(_ENTITIES, ("plant-id", "group-id"))
    assert needed == {"group-id", "corp-id", "plant-id"}


def test_corroborated_abbreviation_attaches_only_to_authorized_nodes() -> None:
    forest = build_customer_group_forest(
        _ENTITIES,
        ("corp-id",),
        (
            (
                "corp-id",
                TreeAbbreviation("DC", "verify_corroborated", "https://example.test/demo-corp-dc"),
            ),
            (
                "other-id",
                TreeAbbreviation("OC", "verify_corroborated", "https://example.test/other"),
            ),
        ),
    )
    company = forest[0].children[0]
    assert [alias.raw_organization_name for alias in company.abbreviations] == ["DC"]
    assert forest[0].to_dict()["children"][0]["abbreviations"][0]["raw_organization_name"] == "DC"
    serialized = forest[0].to_dict()
    assert "Other Corp" not in str(serialized)
