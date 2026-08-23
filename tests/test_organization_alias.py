"""Corroborated SKOS companion labels stay unique and fail closed on a tie."""

from __future__ import annotations

from lineageweave.organization_alias import (
    OrganizationNameAlias,
    attach_organization_aliases,
    companion_organization_alias,
    organization_alias_caption,
)

_DC = OrganizationNameAlias(
    alt_label="DC", pref_label="Demo Corp", corporate_entity_id="demo-id"
)
_AGP = OrganizationNameAlias(
    alt_label="AGP", pref_label="Aurora Grid Power", corporate_entity_id="aurora-id"
)


def test_pref_label_returns_the_alt_label() -> None:
    assert companion_organization_alias("Demo Corp", "demo-id", (_DC,)) == "DC"


def test_alt_label_returns_the_pref_label() -> None:
    assert companion_organization_alias("AGP", "aurora-id", (_AGP,)) == "Aurora Grid Power"


def test_uncorroborated_or_unknown_name_stays_unlabeled() -> None:
    assert companion_organization_alias("Northridge Grid", "demo-id", (_DC, _AGP)) is None
    assert companion_organization_alias("Demo Corp", "demo-id", ()) is None
    assert companion_organization_alias("  ", "demo-id", (_DC,)) is None
    assert companion_organization_alias("Demo Corp", None, (_DC,)) is None
    assert companion_organization_alias("Demo Corp", "other-id", (_DC,)) is None


def test_legal_suffix_difference_does_not_bind_an_alias() -> None:
    assert companion_organization_alias("Demo Inc", "demo-id", (_DC,)) is None


def test_identical_labels_are_ignored() -> None:
    same = OrganizationNameAlias("Demo Corp", "Demo Corp", "demo-id")
    assert companion_organization_alias("Demo Corp", "demo-id", (same,)) is None


def test_two_distinct_companions_stay_unbound() -> None:
    other = OrganizationNameAlias("DMC", "Demo Corp", "demo-id")
    assert companion_organization_alias("Demo Corp", "demo-id", (_DC, other)) is None


def test_duplicate_pair_keeps_one_companion() -> None:
    assert companion_organization_alias("Demo Corp", "demo-id", (_DC, _DC)) == "DC"


def test_caption_puts_the_alias_in_parentheses() -> None:
    assert organization_alias_caption("Demo Corp", "DC") == "Demo Corp (DC)"
    assert organization_alias_caption("Demo Corp", None) == "Demo Corp"
    assert organization_alias_caption("Demo Corp", "  ") == "Demo Corp"


def test_forest_attach_is_recursive_and_omits_missing_keys() -> None:
    forest = [
        {
            "entity_id": "group-id",
            "entity_name": "Demo Group",
            "children": [
                {"entity_id": "demo-id", "entity_name": "Demo Corp", "children": []},
                {"entity_id": "north-id", "entity_name": "Northridge Grid", "children": []},
            ],
        }
    ]
    attach_organization_aliases(forest, (_DC,), entity_id_key="entity_id")
    assert "organization_alias" not in forest[0]
    assert forest[0]["children"][0]["organization_alias"] == "DC"
    assert "organization_alias" not in forest[0]["children"][1]


def test_forest_attach_ignores_non_records_and_non_string_names() -> None:
    records = [
        "not-a-record",
        {"entity_name": None},
        {"entity_name": "Demo Corp", "corporate_entity_id": "demo-id"},
    ]
    attach_organization_aliases(records, (_DC,))  # type: ignore[arg-type]
    assert records[2]["organization_alias"] == "DC"  # type: ignore[index]


def test_same_name_on_another_catalog_id_stays_unlabeled() -> None:
    records = [
        {"entity_name": "Demo Corp", "corporate_entity_id": "demo-id"},
        {"entity_name": "Demo Corp", "corporate_entity_id": "other-id"},
        {"entity_name": "Demo Corp", "corporate_entity_id": None},
    ]
    attach_organization_aliases(records, (_DC,))
    assert records[0]["organization_alias"] == "DC"
    assert "organization_alias" not in records[1]
    assert "organization_alias" not in records[2]
