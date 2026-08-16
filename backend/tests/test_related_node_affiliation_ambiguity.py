"""Regression tests for related-node affiliation display authority."""

from __future__ import annotations

import asyncio
from typing import Any

from backend.app.knowledge_graph import hydrate_related_nodes
from lineageweave.knowledge_graph import NODE_PERSON, node_key


_PERSON_ID = "11111111-1111-4111-8111-111111111111"
_CATALOG_ID = "22222222-2222-4222-8222-222222222222"


class _FakeConnection:
    """Return the minimum query results needed by ``hydrate_related_nodes``."""

    def __init__(self, affiliations: list[dict[str, Any]]) -> None:
        self._affiliations = affiliations

    async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
        if "from cataloged_person" in query:
            return [
                {
                    "person_id": _PERSON_ID,
                    "person_name": "Priya Nair",
                    "person_side_code": "counterparty",
                }
            ]
        if "from person_affiliation" in query:
            return [
                {
                    "person_id": _PERSON_ID,
                    "affiliated_organization_name": row.get("affiliated_organization_name"),
                    "affiliated_corporate_entity_id": row.get("affiliated_corporate_entity_id"),
                    "catalog_entity_name": row.get("catalog_entity_name"),
                }
                for row in self._affiliations
            ]
        if "from common_lookup_value" in query:
            return [{"lookup_code": "counterparty", "lookup_label": "Counterparty"}]
        raise AssertionError(f"unexpected query: {query}")


def _hydrate(affiliations: list[dict[str, Any]]) -> dict[str, Any]:
    payload = asyncio.run(
        hydrate_related_nodes(
            _FakeConnection(affiliations),  # type: ignore[arg-type]
            [(node_key(NODE_PERSON, _PERSON_ID), 0.8)],
        )
    )
    assert len(payload) == 1
    return payload[0]


def test_related_person_exposes_one_unambiguous_affiliation() -> None:
    """A single known affiliation is safe to use as compact display context."""
    node = _hydrate([{"affiliated_organization_name": "Northridge Grid"}])
    assert node["affiliation_organization_name"] == "Northridge Grid"


def test_related_person_omits_affiliation_when_multiple_are_known() -> None:
    """Multiple affiliations must not be collapsed into an invented primary one."""
    node = _hydrate(
        [
            {"affiliated_organization_name": "Northridge Grid"},
            {"affiliated_organization_name": "Northridge Holdings"},
        ]
    )
    assert "affiliation_organization_name" not in node


def test_related_person_omits_blank_affiliation() -> None:
    """Whitespace-only extraction strings are missing evidence, not a name."""
    node = _hydrate([{"affiliated_organization_name": "   "}])
    assert "affiliation_organization_name" not in node


def test_related_person_uses_catalog_name_for_one_resolved_org() -> None:
    """A resolved catalog org supplies entity_name, not the raw extraction."""
    node = _hydrate(
        [
            {
                "affiliated_organization_name": "Demo Corp Inc.",
                "affiliated_corporate_entity_id": _CATALOG_ID,
                "catalog_entity_name": "Demo Corp",
            }
        ]
    )
    assert node["affiliation_organization_name"] == "Demo Corp"


def test_related_person_collapses_aliases_of_one_catalog_org() -> None:
    """Two raw strings for the same corporate_entity_id are one identity."""
    node = _hydrate(
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
    assert node["affiliation_organization_name"] == "Demo Corp"


def test_related_person_collapses_unresolved_name_matching_catalog() -> None:
    """An unresolved alias of the catalog label is not a second org."""
    node = _hydrate(
        [
            {
                "affiliated_organization_name": "Demo Corp",
                "affiliated_corporate_entity_id": _CATALOG_ID,
                "catalog_entity_name": "Demo Corp",
            },
            {"affiliated_organization_name": "demo corp"},
        ]
    )
    assert node["affiliation_organization_name"] == "Demo Corp"


def test_related_person_omits_resolved_plus_distinct_unresolved() -> None:
    """A catalog org plus a different unresolved name stays ambiguous."""
    node = _hydrate(
        [
            {
                "affiliated_organization_name": "Demo Corp",
                "affiliated_corporate_entity_id": _CATALOG_ID,
                "catalog_entity_name": "Demo Corp",
            },
            {"affiliated_organization_name": "Northridge Holdings"},
        ]
    )
    assert "affiliation_organization_name" not in node
