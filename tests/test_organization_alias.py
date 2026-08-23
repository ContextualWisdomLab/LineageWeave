"""Corroborated SKOS companion labels stay unique and fail closed on a tie."""

from __future__ import annotations

from lineageweave.organization_alias import (
    OrganizationNameAlias,
    attach_organization_aliases,
    companion_organization_alias,
    organization_alias_caption,
)

_DC = OrganizationNameAlias(alt_label="DC", pref_label="Demo Corp")
_AGP = OrganizationNameAlias(alt_label="AGP", pref_label="Aurora Grid Power")


def test_pref_label_returns_the_alt_label() -> None:
    assert companion_organization_alias("Demo Corp", (_DC,)) == "DC"


def test_alt_label_returns_the_pref_label() -> None:
    assert companion_organization_alias("AGP", (_AGP,)) == "Aurora Grid Power"


def test_uncorroborated_or_unknown_name_stays_unlabeled() -> None:
    assert companion_organization_alias("Northridge Grid", (_DC, _AGP)) is None
    assert companion_organization_alias("Demo Corp", ()) is None


def test_identical_labels_are_ignored() -> None:
    same = OrganizationNameAlias(alt_label="Demo Corp", pref_label="Demo Corp")
    assert companion_organization_alias("Demo Corp", (same,)) is None


def test_two_distinct_companions_stay_unbound() -> None:
    other = OrganizationNameAlias(alt_label="DMC", pref_label="Demo Corp")
    assert companion_organization_alias("Demo Corp", (_DC, other)) is None


def test_caption_puts_the_alias_in_parentheses() -> None:
    assert organization_alias_caption("Demo Corp", "DC") == "Demo Corp (DC)"
    assert organization_alias_caption("Demo Corp", None) == "Demo Corp"
    assert organization_alias_caption("Demo Corp", "  ") == "Demo Corp"


def test_forest_attach_is_recursive_and_omits_missing_keys() -> None:
    forest = [
        {
            "entity_name": "Demo Group",
            "children": [
                {"entity_name": "Demo Corp", "children": []},
                {"entity_name": "Northridge Grid", "children": []},
            ],
        }
    ]
    attach_organization_aliases(forest, (_DC,))
    assert "organization_alias" not in forest[0]
    assert forest[0]["children"][0]["organization_alias"] == "DC"
    assert "organization_alias" not in forest[0]["children"][1]
