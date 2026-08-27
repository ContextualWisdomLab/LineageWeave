"""Catalog-bound occupational construct extraction regressions."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import pytest

from backend.app.occupational_construct_ingestion import (
    extract_occupational_construct_assertions,
)
from lineageweave.occupational_construct_extraction import (
    OccupationalConstructCandidate,
    OccupationalConstructSelection,
    parse_occupational_construct_selections,
)


def test_parser_accepts_only_offered_iri_and_verbatim_evidence() -> None:
    """Unknown catalog terms and invented evidence fail closed."""
    candidate = OccupationalConstructCandidate("https://example.test/c1", "Think", None)
    assert parse_occupational_construct_selections(
        '[{"construct_iri":"https://example.test/c1","evidence_text":"reviewed data"}]',
        "The analyst reviewed data.",
        (candidate,),
    ) == (OccupationalConstructSelection(candidate.construct_iri, "reviewed data"),)
    with pytest.raises(ValueError, match="offered unique IRI"):
        parse_occupational_construct_selections(
            '[{"construct_iri":"https://example.test/invented","evidence_text":"reviewed data"}]',
            "The analyst reviewed data.",
            (candidate,),
        )


def test_hierarchy_descends_only_through_selected_official_nodes() -> None:
    """Traversal offers bounded siblings and persists selected parent and child evidence."""
    base = "https://data.onetcenter.org/element/"
    catalog = [
        {
            "construct_iri": base + "1.A.1",
            "construct_family_code": "cognitive_ability",
            "preferred_label": "Abilities",
            "construct_description": "Root",
        },
        {
            "construct_iri": base + "1.A.1.a",
            "construct_family_code": "cognitive_ability",
            "preferred_label": "Reasoning",
            "construct_description": "Child",
        },
        {
            "construct_iri": base + "1.D",
            "construct_family_code": "work_style",
            "preferred_label": "Work Styles",
            "construct_description": "Other root",
        },
    ]
    units = [{"post_content_unit_id": "unit-1", "unit_text": "reviewed data"}]

    class Connection:
        calls = 0

        async def fetch(self, _query, *_args):
            self.calls += 1
            return catalog if self.calls == 1 else units

    class Pool:
        active = False

        @asynccontextmanager
        async def acquire(self):
            self.active = True
            try:
                yield Connection()
            finally:
                self.active = False

    offered: list[tuple[str, ...]] = []
    pool = Pool()

    class Client:
        available = True

        def select(self, _text, candidates):
            assert not pool.active
            offered.append(tuple(item.construct_iri for item in candidates))
            selected = candidates[0]
            return (OccupationalConstructSelection(selected.construct_iri, "reviewed data"),)

    assertions = asyncio.run(
        extract_occupational_construct_assertions(pool, "post-1", Client())
    )

    assert offered == [(base + "1.A.1", base + "1.D"), (base + "1.A.1.a",)]
    assert [item.construct.construct_iri for item in assertions] == [
        base + "1.A.1",
        base + "1.A.1.a",
    ]
    assert all(item.truth_status_code == "truth_inferred" for item in assertions)
