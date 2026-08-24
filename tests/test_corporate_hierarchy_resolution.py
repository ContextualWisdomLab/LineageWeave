"""Tests for deterministic corporate-hierarchy candidate resolution."""

from __future__ import annotations

from lineageweave.corporate_hierarchy_resolution import (
    RESOLUTION_MISS,
    RESOLUTION_TIE,
    RESOLUTION_UNIQUE,
    CorporateEntityCandidate,
    OrganizationNameAlias,
    expand_candidates_with_skos_aliases,
    normalize_organization_name,
    resolve_corporate_entity,
    score_corporate_entity,
)

_CANDIDATES = [
    CorporateEntityCandidate("group-id", "Acme Group"),
    CorporateEntityCandidate("korea-id", "Acme Electronics Korea"),
    CorporateEntityCandidate("gwangju-id", "Acme Electronics Gwangju Plant"),
]


def test_exact_name_resolves() -> None:
    assert resolve_corporate_entity(
        "Acme Electronics Korea",
        _CANDIDATES,
    ) == "korea-id"


def test_trailing_legal_suffix_still_resolves() -> None:
    assert resolve_corporate_entity(
        "Acme Electronics Korea Ltd.",
        _CANDIDATES,
    ) == "korea-id"


def test_abbreviation_still_resolves() -> None:
    assert resolve_corporate_entity("Acme Elec Korea", _CANDIDATES) == "korea-id"


def test_resolves_to_the_correct_sibling_not_a_different_one() -> None:
    """A plant-like mention resolves to the plant rather than its parent."""
    assert resolve_corporate_entity(
        "Acme Gwangju Plant",
        _CANDIDATES,
    ) == "gwangju-id"


def test_unrelated_organization_is_a_miss() -> None:
    """A below-threshold candidate set is distinct from an equal-score tie."""
    outcome = score_corporate_entity(
        "Totally Different Company",
        _CANDIDATES,
    )
    assert outcome.kind == RESOLUTION_MISS
    assert outcome.catalog_id is None
    assert resolve_corporate_entity(
        "Totally Different Company",
        _CANDIDATES,
    ) is None


def test_empty_mention_does_not_resolve() -> None:
    assert resolve_corporate_entity("", _CANDIDATES) is None
    assert resolve_corporate_entity("   ", _CANDIDATES) is None


def test_no_candidates_does_not_resolve() -> None:
    assert resolve_corporate_entity("Acme Electronics Korea", []) is None


def test_tied_same_display_name_stays_unbound() -> None:
    """Distinct same-named catalog rows are a tie, not a first-wins match."""
    homonyms = [
        CorporateEntityCandidate("homonym-a", "Tied Energy"),
        CorporateEntityCandidate("homonym-b", "Tied Energy"),
    ]
    outcome = score_corporate_entity("Tied Energy", homonyms)
    assert outcome.kind == RESOLUTION_TIE
    assert outcome.catalog_id is None
    assert set(outcome.top_catalog_ids) == {"homonym-a", "homonym-b"}
    assert resolve_corporate_entity("Tied Energy", homonyms) is None


def test_duplicate_snapshot_rows_for_one_catalog_id_are_unique() -> None:
    """Duplicate query rows do not manufacture an identity tie."""
    duplicated = [
        CorporateEntityCandidate("korea-id", "Acme Electronics Korea"),
        CorporateEntityCandidate("korea-id", "Acme Electronics Korea"),
    ]
    outcome = score_corporate_entity("Acme Electronics Korea", duplicated)
    assert outcome.kind == RESOLUTION_UNIQUE
    assert outcome.catalog_id == "korea-id"


def test_unique_exact_name_still_wins_beside_unrelated_homonyms() -> None:
    mixed = [
        *_CANDIDATES,
        CorporateEntityCandidate("homonym-a", "Tied Energy"),
        CorporateEntityCandidate("homonym-b", "Tied Energy"),
    ]
    assert resolve_corporate_entity(
        "Acme Electronics Korea",
        mixed,
    ) == "korea-id"
    assert resolve_corporate_entity("Tied Energy", mixed) is None


def test_normalize_strips_suffix_punctuation_and_case() -> None:
    assert normalize_organization_name(
        "Acme Electronics Korea, Ltd."
    ) == "acme electronics korea"
    assert normalize_organization_name("  ACME   Group  ") == "acme group"


_AGP_ALIAS = OrganizationNameAlias(alt_label="AGP", pref_label="Aurora Grid Power")


def test_skos_alias_binds_short_form_to_pref_label_catalog_row() -> None:
    """A corroborated AGP altLabel must resolve to the Aurora Grid Power row."""
    catalog = [CorporateEntityCandidate("aurora-id", "Aurora Grid Power")]
    expanded = expand_candidates_with_skos_aliases(catalog, [_AGP_ALIAS])
    outcome = score_corporate_entity("AGP", expanded)
    assert outcome.kind == RESOLUTION_UNIQUE
    assert outcome.catalog_id == "aurora-id"
    assert resolve_corporate_entity("AGP", catalog) is None


def test_skos_alias_binds_pref_label_to_short_form_catalog_row() -> None:
    """A catalog row stored under the altLabel still binds the prefLabel mention."""
    catalog = [CorporateEntityCandidate("aurora-id", "AGP")]
    expanded = expand_candidates_with_skos_aliases(catalog, [_AGP_ALIAS])
    outcome = score_corporate_entity("Aurora Grid Power", expanded, min_similarity=1.0)
    assert outcome.kind == RESOLUTION_UNIQUE
    assert outcome.catalog_id == "aurora-id"


def test_skos_alias_does_not_bind_an_unrelated_organization() -> None:
    catalog = [CorporateEntityCandidate("northridge-id", "Northridge Grid")]
    expanded = expand_candidates_with_skos_aliases(catalog, [_AGP_ALIAS])
    outcome = score_corporate_entity("AGP", expanded)
    assert outcome.kind == RESOLUTION_MISS
    assert outcome.catalog_id is None


def test_skos_alias_tie_across_two_catalog_rows_stays_unbound() -> None:
    """Two catalog ids that both own the same prefLabel remain a tie."""
    catalog = [
        CorporateEntityCandidate("aurora-a", "Aurora Grid Power"),
        CorporateEntityCandidate("aurora-b", "Aurora Grid Power"),
    ]
    expanded = expand_candidates_with_skos_aliases(catalog, [_AGP_ALIAS])
    outcome = score_corporate_entity("AGP", expanded)
    assert outcome.kind == RESOLUTION_TIE
    assert outcome.catalog_id is None
    assert set(outcome.top_catalog_ids) == {"aurora-a", "aurora-b"}


def test_identical_or_empty_skos_labels_do_not_expand() -> None:
    catalog = [CorporateEntityCandidate("aurora-id", "Aurora Grid Power")]
    expanded = expand_candidates_with_skos_aliases(
        catalog,
        [
            OrganizationNameAlias(alt_label="Aurora Grid Power", pref_label="Aurora Grid Power"),
            OrganizationNameAlias(alt_label="  ", pref_label="Aurora Grid Power"),
        ],
    )
    assert expanded == catalog

