"""API contract tests for the FJA I/O-Psychology ontology endpoints (ADR 0251).

Exercises the read-only worker-function psychology and construct-catalog
routes through their handler aliases with the authorization gate stubbed
out, mirroring the sibling ``backend/tests`` style. The payloads are pure
projections of the published ontology, so no database is needed.
"""

from __future__ import annotations

import asyncio
import builtins
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.app import iopsy_ontology_api
from backend.app import main


@pytest.fixture(autouse=True)
def _stub_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub the coarse post_read authorization gate for handler tests."""
    if hasattr(main, "_require_post_read"):
        monkeypatch.setattr(main, "_require_post_read", lambda account: None)


def _account() -> SimpleNamespace:
    """Return a minimal authorized account double."""
    return SimpleNamespace(corporate_entity_ids=set(), process_unit_ids=set())


def _run(function: object, *args: object) -> object:
    """Await one async handler with the given arguments."""
    return asyncio.run(function(*args))


def test_worker_function_psychology_returns_profile() -> None:
    """High-complexity data work demands analytic cognition and core performance."""
    payload = _run(main.read_worker_function_psychology, "data", 2, _account())

    assert payload["function_domain"] == "data"
    assert payload["function_rank"] == 2
    assert payload["function_label"] == "Analyzing"
    cognitive_labels = {item["label"] for item in payload["cognitive_demands"]}
    assert "Diagnostic Reasoning" in cognitive_labels
    assert "Inductive & Deductive Reasoning" in cognitive_labels
    assert payload["mental_workload_demands"]
    assert all(item["category"] == "cognitive" for item in payload["mental_workload_demands"])


def test_people_function_includes_emotional_labor() -> None:
    """Negotiating demands deep acting and affective regulation."""
    payload = _run(main.read_worker_function_psychology, "people", 1, _account())
    assert payload["function_label"] == "Negotiating"
    emotional_labor = {item["label"] for item in payload["emotional_labor_demands"]}
    assert "Emotional Labor — Deep Acting" in emotional_labor
    assert payload["affective_demands"]


def test_things_function_requires_safety() -> None:
    """Things functions manifest safety compliance and psychomotor behavior."""
    payload = _run(main.read_worker_function_psychology, "things", 2, _account())
    behavioral_labels = {item["label"] for item in payload["behavioral_manifestations"]}
    assert "Safety Compliance" in behavioral_labels
    assert payload["psychomotor_behaviors"]


def test_undeclared_function_is_honest_404() -> None:
    """An absent domain/rank pair fails closed as an honest 404."""
    with pytest.raises(HTTPException) as exc_info:
        _run(main.read_worker_function_psychology, "data", 99, _account())
    assert exc_info.value.status_code == 404


def test_invalid_domain_is_client_error() -> None:
    """An unrecognized FJA domain is client error, never fabricated output."""
    with pytest.raises(HTTPException) as exc_info:
        _run(main.read_worker_function_psychology, "bogus", 0, _account())
    assert exc_info.value.status_code == 422


def test_construct_catalog_is_deterministic_and_complete() -> None:
    """The catalog groups constructs by psychological domain with metadata."""
    payload = iopsy_ontology_api.construct_catalog_payload()
    constructs = payload["constructs"]
    assert {"cognitive", "affective", "behavioral"} <= set(constructs)
    for category in ("cognitive", "affective", "behavioral"):
        assert constructs[category]
    cognitive = {item["label"] for item in constructs["cognitive"]}
    assert "Mental Workload" in cognitive
    affective = {item["label"] for item in constructs["affective"]}
    assert "Burnout — Emotional Exhaustion" in affective
    assert all(item["theoretical_basis"] for item in constructs["cognitive"])
    assert payload["relations"]


def test_construct_catalog_isolated_from_main_import() -> None:
    """The serializer module imports no FastAPI application concerns."""
    code = builtins.open(iopsy_ontology_api.__file__, encoding="utf-8").read()
    assert "import main" not in code
    assert "fastapi" not in code