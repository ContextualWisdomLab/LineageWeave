"""Regression tests for related-node affiliation display authority."""

from __future__ import annotations

import asyncio
from typing import Any

from backend.app.knowledge_graph import hydrate_related_nodes
from lineageweave.knowledge_graph import NODE_PERSON, node_key


_PERSON_ID = "11111111-1111-4111-8111-111111111111"


class _FakeConnection:
    """Return the minimum query results needed by ``hydrate_related_nodes``."""

    def __init__(self, affiliations: list[str]) -> None:
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
                    "affiliated_organization_name": organization_name,
                    "affiliated_corporate_entity_id": None,
                }
                for organization_name in self._affiliations
            ]
        if "from common_lookup_value" in query:
            return [{"lookup_code": "counterparty", "lookup_label": "Counterparty"}]
        raise AssertionError(f"unexpected query: {query}")


def _hydrate(affiliations: list[str]) -> dict[str, Any]:
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
    node = _hydrate(["Northridge Grid"])
    assert node["affiliation_organization_name"] == "Northridge Grid"


def test_related_person_omits_affiliation_when_multiple_are_known() -> None:
    """Multiple affiliations must not be collapsed into an invented primary one."""
    node = _hydrate(["Northridge Grid", "Northridge Holdings"])
    assert "affiliation_organization_name" not in node
