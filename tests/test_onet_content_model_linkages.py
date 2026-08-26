"""Contracts for the eight O*NET 31.0 content-model linkage tables."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from rdflib.namespace import PROV, RDF

from lineageweave import onet_content_model
from lineageweave.ontology import LW, ONTOLOGY

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "ontology" / "data"
TURTLE = ROOT / "docs" / "ontology" / "onet-31-content-model-linkages.ttl"
RENDERER = ROOT / "scripts" / "render_onet_31_content_model_linkages.py"

TABLES = {
    "abilities_to_work_activities": (381, "e03c3db1dbe8c7818198c943c8640cc2ddaf351972a79756b535940c84acfc52"),
    "abilities_to_work_context": (139, "7d5fbdc3df973790f1f24f98ace1f77c6cc8dab97197444e9ebf7695b6f59348"),
    "essential_skills_to_work_activities": (110, "35d389bb2a578d64bf49ef263f24cb5c1bb59c214bcec9045e476008023205f5"),
    "essential_skills_to_work_context": (39, "883f99fe723610530666031da9a68d72790f04cc87e0ac808f4600f1e01b8e5f"),
    "transferable_skills_to_work_activities": (122, "0b1755becb3100d4c19660cea2adf8d7c47a0654087560ceffd71c515fe94be2"),
    "transferable_skills_to_work_context": (57, "4add628b7257f2a1b7b204b1ddd715b82685559d35b020e540b15ca74abb2dd6"),
    "work_styles_to_work_activities": (303, "889071d37a3bb073854c72dc31f96a8e9079a18c4e581e6f5bf2e082f58c641b"),
    "work_styles_to_work_context": (266, "9e3aa088aa55d1f927688c55bb77987f5825ba0fdc9da3edebcb81cbf198fa54"),
}


def _path(table_id: str) -> Path:
    return DATA / f"onet-31-{table_id.replace('_', '-')}.json"


def test_pinned_tables_have_exact_counts_digests_and_unique_pairs() -> None:
    for table_id, (expected_count, expected_digest) in TABLES.items():
        path = _path(table_id)
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload["row"]
        assert payload["table_id"] == table_id
        assert len(rows) == expected_count
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_digest
        assert len({tuple(row.values()) for row in rows}) == expected_count


def test_ontology_publishes_every_directed_link_and_reified_provenance() -> None:
    activity_links = set(ONTOLOGY.triples((None, LW.relevantWorkActivity, None)))
    context_links = set(ONTOLOGY.triples((None, LW.relevantWorkContext, None)))
    assert len(activity_links) == 916
    assert len(context_links) == 501

    for subject, predicate, object_ in activity_links | context_links:
        statements = {
            statement
            for statement in ONTOLOGY.subjects(RDF.subject, subject)
            if (statement, RDF.predicate, predicate) in ONTOLOGY
            and (statement, RDF.object, object_) in ONTOLOGY
        }
        assert len(statements) == 1
        statement = statements.pop()
        assert (statement, RDF.type, RDF.Statement) in ONTOLOGY
        assert (statement, RDF.type, PROV.Entity) in ONTOLOGY
        assert len(set(ONTOLOGY.objects(statement, PROV.wasDerivedFrom))) == 1


def test_read_model_exposes_direction_and_source() -> None:
    assert hasattr(onet_content_model, "content_model_linkages")
    links = onet_content_model.content_model_linkages("1.A.1.a.1")
    assert any(
        link.target_element_id == "4.A.1.a.1"
        and link.relationship == "relevant_work_activity"
        and link.provenance_iri.endswith("sourceOnet310AbilitiesToWorkActivities")
        for link in links
    )


def test_checked_in_turtle_is_exact_renderer_output() -> None:
    spec = importlib.util.spec_from_file_location("render_onet_linkages", RENDERER)
    assert spec is not None and spec.loader is not None
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    sources = tuple(_path(table_id) for table_id in TABLES)
    rendered = renderer.render(DATA / "onet-31-content-model-reference.json", sources)
    assert rendered == TURTLE.read_text(encoding="utf-8")


def test_renderer_rejects_a_duplicate_source_pair(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("render_onet_linkages_invalid", RENDERER)
    assert spec is not None and spec.loader is not None
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    table_id = "abilities_to_work_activities"
    payload = json.loads(_path(table_id).read_text(encoding="utf-8"))
    payload["row"][1] = payload["row"][0]
    invalid = tmp_path / f"{table_id}.json"
    invalid.write_text(json.dumps(payload), encoding="utf-8")
    sources = tuple(invalid if name == table_id else _path(name) for name in TABLES)

    with pytest.raises(ValueError, match="duplicate pair"):
        renderer.render(DATA / "onet-31-content-model-reference.json", sources)
