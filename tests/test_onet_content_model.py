"""Contract tests for the complete O*NET 31.0 content-model hierarchy."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest
from rdflib.namespace import SKOS

from lineageweave.onet_content_model import (
    child_elements,
    content_model_element,
    content_model_records,
)
from lineageweave.ontology import LW, ONTOLOGY

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "ontology" / "data" / "onet-31-content-model-reference.json"
TURTLE = ROOT / "docs" / "ontology" / "onet-31-content-model.ttl"
RENDERER = ROOT / "scripts" / "render_onet_31_content_model.py"


def test_complete_source_hierarchy_and_parent_closure() -> None:
    records = content_model_records()
    by_id = {record.element_id: record for record in records}

    assert len(records) == len(by_id) == 3006
    assert {record.name for record in records if record.parent_element_id is None} == {
        "Worker Characteristics",
        "Worker Requirements",
        "Experience Requirements",
        "Occupational Requirements",
        "Occupation-Specific Information",
        "Workforce Characteristics",
    }
    assert all(
        record.parent_element_id is None or record.parent_element_id in by_id
        for record in records
    )


def test_verbatim_examples_and_direct_children() -> None:
    assert content_model_element("1.A.1.a.1").name == "Oral Comprehension"
    assert content_model_element("1.D").description == (
        "Personality tendencies exhibited at work, which can affect how well "
        "someone performs a job."
    )
    assert {record.element_id for record in child_elements("1")} == {"1.A", "1.B", "1.D"}


def test_records_follow_numeric_outline_order() -> None:
    element_ids = [record.element_id for record in content_model_records()]
    assert element_ids.index("2.C.2") < element_ids.index("2.C.10")


def test_lookup_distinguishes_absent_from_malformed() -> None:
    assert content_model_element("1.Z") is None
    assert child_elements("1.Z") == ()
    with pytest.raises(ValueError):
        content_model_element("not-an-onet-id")


def test_pinned_source_and_generated_turtle_are_exact() -> None:
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == (
        "db59c30e4240931edce59310f2747f5476f058984b55f58f72c6f29faa30186f"
    )
    spec = importlib.util.spec_from_file_location("render_onet_31_content_model", RENDERER)
    assert spec is not None and spec.loader is not None
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    assert renderer.render(SOURCE) == TURTLE.read_text(encoding="utf-8")
    assert len(set(ONTOLOGY.subjects(SKOS.inScheme, LW.onet31ContentModelScheme))) == 3006
