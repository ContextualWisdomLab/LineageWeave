"""Completeness and reproducibility checks for ADR 0251's 2018 SOC graph."""

from __future__ import annotations

import hashlib
import importlib.util
from collections import Counter
from pathlib import Path

from rdflib import Graph

from lineageweave.io_taxonomy import (
    soc_classification,
    soc_classification_records,
)

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "docs" / "ontology" / "data" / "soc-2018-structure.csv"
TTL_PATH = ROOT / "docs" / "ontology" / "soc-2018-structure.ttl"


def _renderer():
    spec = importlib.util.spec_from_file_location(
        "render_soc_2018_hierarchy",
        ROOT / "scripts" / "render_soc_2018_hierarchy.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_complete_official_level_counts_and_parent_closure() -> None:
    """All 1,447 published classifications retain a declared parent."""
    records = soc_classification_records()
    assert len(records) == 1447
    assert Counter(record.level for record in records) == {
        "major_group": 23,
        "minor_group": 98,
        "broad_occupation": 459,
        "detailed_occupation": 867,
    }
    codes = {record.code for record in records}
    assert all(
        record.broader_code is None
        if record.level == "major_group"
        else record.broader_code in codes
        for record in records
    )


def test_published_four_level_chain_is_preserved_verbatim() -> None:
    """The BLS example chain reaches its major group without inference."""
    expected = {
        "17-3011": ("Architectural and Civil Drafters", "17-3010"),
        "17-3010": ("Drafters", "17-3000"),
        "17-3000": (
            "Drafters, Engineering Technicians, and Mapping Technicians",
            "17-0000",
        ),
        "17-0000": ("Architecture and Engineering Occupations", None),
    }
    for code, (title, parent) in expected.items():
        record = soc_classification(code)
        assert record is not None
        assert (record.label, record.broader_code) == (title, parent)


def test_source_digest_and_generated_turtle_are_exact() -> None:
    """The normalized source and checked-in Turtle cannot drift independently."""
    assert hashlib.sha256(CSV_PATH.read_bytes()).hexdigest() == (
        "7de1c9d4da14d8eeb95197974d9dc1989752ebda235dd234b1693f336891f68e"
    )
    assert _renderer().render(CSV_PATH) == TTL_PATH.read_text(encoding="utf-8")
    graph = Graph().parse(TTL_PATH, format="turtle")
    assert len(set(graph.subjects())) == 1447


def test_lookup_distinguishes_absent_from_malformed_codes() -> None:
    """Valid unknown codes are absent; malformed caller input fails closed."""
    assert soc_classification("99-9999") is None
    for invalid in ("17-301", "173011", "", 173011):
        try:
            soc_classification(invalid)  # type: ignore[arg-type]
        except ValueError:
            pass
        else:
            raise AssertionError(f"malformed code was accepted: {invalid!r}")
