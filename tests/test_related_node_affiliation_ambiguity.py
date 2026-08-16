"""Identity-rule unit tests for compact related-node affiliation."""

from __future__ import annotations

from typing import Any

from backend.app.knowledge_graph import compact_affiliation_summaries

_PERSON_ID = "11111111-1111-4111-8111-111111111111"
_CATALOG_ID = "22222222-2222-4222-8222-222222222222"
_SECOND_CATALOG_ID = "33333333-3333-4333-8333-333333333333"


def _summarize(affiliations: list[dict[str, Any]]):
    rows = [
        {
            "person_id": _PERSON_ID,
            "affiliated_organization_name": None,
            "affiliated_corporate_entity_id": None,
            "catalog_entity_name": None,
            **row,
        }
        for row in affiliations
    ]
    return compact_affiliation_summaries(rows).get(_PERSON_ID)


def _payload(summary) -> dict[str, Any]:
    """Mirror hydrate: emit a name or the plural flag, never both."""
    if summary is None:
        return {}
    item: dict[str, Any] = {}
    if summary.display_name:
        item["affiliation_organization_name"] = summary.display_name
    if summary.ambiguous:
        item["affiliation_ambiguous"] = True
    return item


def test_related_person_exposes_one_unambiguous_affiliation() -> None:
    """A single known affiliation is safe to use as compact display context."""
    summary = _summarize([{"affiliated_organization_name": "Northridge Grid"}])
    assert summary is not None
    assert summary.display_name == "Northridge Grid"
    assert summary.ambiguous is False
    assert _payload(summary) == {"affiliation_organization_name": "Northridge Grid"}


def test_related_person_marks_plural_affiliations_ambiguous() -> None:
    """A known-plural set is not a missing affiliation and never invents a primary."""
    summary = _summarize(
        [
            {"affiliated_organization_name": "Northridge Grid"},
            {"affiliated_organization_name": "Northridge Holdings"},
        ]
    )
    assert summary is not None
    assert summary.display_name is None
    assert summary.ambiguous is True
    assert _payload(summary) == {"affiliation_ambiguous": True}


def test_related_person_omits_blank_affiliation() -> None:
    """Whitespace-only extraction strings are missing evidence, not a name."""
    summary = _summarize([{"affiliated_organization_name": "   "}])
    assert summary is None
    assert _payload(summary) == {}


def test_related_person_uses_catalog_name_for_one_resolved_org() -> None:
    """A resolved catalog org supplies entity_name, not the raw extraction."""
    summary = _summarize(
        [
            {
                "affiliated_organization_name": "Demo Corp Inc.",
                "affiliated_corporate_entity_id": _CATALOG_ID,
                "catalog_entity_name": "Demo Corp",
            }
        ]
    )
    assert summary is not None
    assert summary.display_name == "Demo Corp"
    assert summary.ambiguous is False
    assert _payload(summary) == {"affiliation_organization_name": "Demo Corp"}


def test_related_person_collapses_aliases_of_one_catalog_org() -> None:
    """Two raw strings for the same corporate_entity_id are one identity."""
    summary = _summarize(
        [
            {
                "affiliated_organization_name": "Demo Corp Inc.",
                "affiliated_corporate_entity_id": _CATALOG_ID,
                "catalog_entity_name": "Demo Corp",
            },
            {
                "affiliated_organization_name": "Demo Corp",
                "affiliated_corporate_entity_id": _CATALOG_ID,
                "catalog_entity_name": "Demo Corp",
            },
        ]
    )
    assert summary is not None
    assert summary.display_name == "Demo Corp"
    assert summary.ambiguous is False


def test_related_person_collapses_unresolved_name_matching_catalog() -> None:
    """An unresolved alias of the catalog label is not a second org."""
    summary = _summarize(
        [
            {
                "affiliated_organization_name": "Demo Corp",
                "affiliated_corporate_entity_id": _CATALOG_ID,
                "catalog_entity_name": "Demo Corp",
            },
            {"affiliated_organization_name": "demo corp"},
        ]
    )
    assert summary is not None
    assert summary.display_name == "Demo Corp"
    assert summary.ambiguous is False


def test_related_person_omits_resolved_plus_distinct_unresolved() -> None:
    """A catalog org plus a different unresolved name stays ambiguous."""
    summary = _summarize(
        [
            {
                "affiliated_organization_name": "Demo Corp",
                "affiliated_corporate_entity_id": _CATALOG_ID,
                "catalog_entity_name": "Demo Corp",
            },
            {"affiliated_organization_name": "Northridge Holdings"},
        ]
    )
    assert summary is not None
    assert summary.display_name is None
    assert summary.ambiguous is True
    assert _payload(summary) == {"affiliation_ambiguous": True}


def test_related_person_marks_two_distinct_catalog_orgs_ambiguous() -> None:
    """Two resolved catalog orgs must not collapse into a guessed primary."""
    summary = _summarize(
        [
            {
                "affiliated_organization_name": "Demo Corp",
                "affiliated_corporate_entity_id": _CATALOG_ID,
                "catalog_entity_name": "Demo Corp",
            },
            {
                "affiliated_organization_name": "Northridge Holdings",
                "affiliated_corporate_entity_id": _SECOND_CATALOG_ID,
                "catalog_entity_name": "Northridge Holdings",
            },
        ]
    )
    assert summary is not None
    assert summary.display_name is None
    assert summary.ambiguous is True
    assert _payload(summary) == {"affiliation_ambiguous": True}


def test_related_person_keeps_nameless_catalog_identity_side_only() -> None:
    """An orphaned catalog id with no name is not a guessed primary or a plural set."""
    summary = _summarize(
        [
            {
                "affiliated_organization_name": "",
                "affiliated_corporate_entity_id": _CATALOG_ID,
                "catalog_entity_name": "",
            }
        ]
    )
    assert summary is not None
    assert summary.identity_count == 1
    assert summary.display_name is None
    assert summary.ambiguous is False
    assert _payload(summary) == {}


def test_related_person_collapses_unresolved_names_that_differ_only_by_case() -> None:
    """Letter-case variants of one unresolved name are one identity."""
    summary = _summarize(
        [
            {"affiliated_organization_name": "Northridge Grid"},
            {"affiliated_organization_name": "northridge grid"},
        ]
    )
    assert summary is not None
    assert summary.display_name == "Northridge Grid"
    assert summary.ambiguous is False
    assert _payload(summary) == {"affiliation_organization_name": "Northridge Grid"}
