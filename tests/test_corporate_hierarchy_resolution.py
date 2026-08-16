"""Tests for lineageweave.corporate_hierarchy_resolution, against a
synthetic hierarchy fixture structurally identical to the one already used
in tests/test_schema.py's real-database test (Acme Group -> Acme
Electronics Korea -> Acme Electronics Gwangju Plant), so the correct
resolution is known by construction: an abbreviation or trailing legal
suffix of one of these three names must resolve to it, and an unrelated
organization name must not resolve to anything.
"""

from __future__ import annotations

from lineageweave.corporate_hierarchy_resolution import (
    CorporateEntityCandidate,
    normalize_organization_name,
    resolve_corporate_entity,
)

_CANDIDATES = [
    CorporateEntityCandidate("group-id", "Acme Group"),
    CorporateEntityCandidate("korea-id", "Acme Electronics Korea"),
    CorporateEntityCandidate("gwangju-id", "Acme Electronics Gwangju Plant"),
]


def test_exact_name_resolves() -> None:
    assert resolve_corporate_entity("Acme Electronics Korea", _CANDIDATES) == "korea-id"


def test_trailing_legal_suffix_still_resolves() -> None:
    assert resolve_corporate_entity("Acme Electronics Korea Ltd.", _CANDIDATES) == "korea-id"


def test_abbreviation_still_resolves() -> None:
    assert resolve_corporate_entity("Acme Elec Korea", _CANDIDATES) == "korea-id"


def test_resolves_to_the_correct_sibling_not_a_different_one() -> None:
    """The whole point of similarity scoring over "any partial match":
    a mention close to the Gwangju plant must resolve to the plant, not
    accidentally to the parent "Acme Electronics Korea" it shares most of
    its name with.
    """
    assert resolve_corporate_entity("Acme Gwangju Plant", _CANDIDATES) == "gwangju-id"


def test_unrelated_organization_does_not_resolve() -> None:
    """A genuine non-match must return None, not the closest-available
    guess -- a wrong hierarchy link corrupts every downstream Knowledge
    Graph traversal through it.
    """
    assert resolve_corporate_entity("Totally Different Company", _CANDIDATES) is None


def test_empty_mention_does_not_resolve() -> None:
    assert resolve_corporate_entity("", _CANDIDATES) is None
    assert resolve_corporate_entity("   ", _CANDIDATES) is None


def test_no_candidates_does_not_resolve() -> None:
    assert resolve_corporate_entity("Acme Electronics Korea", []) is None


def test_tied_same_display_name_does_not_resolve() -> None:
    """Two catalog orgs can share a display name. First-wins is a homonym."""
    homonyms = [
        CorporateEntityCandidate("mentioned-id", "Homonym Energy"),
        CorporateEntityCandidate("other-id", "Homonym Energy"),
    ]
    assert resolve_corporate_entity("Homonym Energy", homonyms) is None


def test_tied_same_display_name_ignores_duplicate_candidate_rows() -> None:
    """The same catalog id listed twice is still one unique winner."""
    duplicated = [
        CorporateEntityCandidate("korea-id", "Acme Electronics Korea"),
        CorporateEntityCandidate("korea-id", "Acme Electronics Korea"),
    ]
    assert resolve_corporate_entity("Acme Electronics Korea", duplicated) == "korea-id"


def test_unique_exact_name_still_wins_among_homonym_neighbors() -> None:
    """A unique exact match stays a button; only a tied top score fails closed."""
    mixed = [
        CorporateEntityCandidate("korea-id", "Acme Electronics Korea"),
        CorporateEntityCandidate("homonym-a", "Homonym Energy"),
        CorporateEntityCandidate("homonym-b", "Homonym Energy"),
    ]
    assert resolve_corporate_entity("Acme Electronics Korea", mixed) == "korea-id"
    assert resolve_corporate_entity("Homonym Energy", mixed) is None


def test_normalize_strips_suffix_punctuation_and_case() -> None:
    assert normalize_organization_name("Acme Electronics Korea, Ltd.") == "acme electronics korea"
    assert normalize_organization_name("  ACME   Group  ") == "acme group"
