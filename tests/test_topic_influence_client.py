"""Contract tests for TEPP-bound fast-mlsirm topic influence."""

from __future__ import annotations

import copy
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytest

from lineageweave.topic_influence_client import (
    RESULT_SCHEMA_VERSION,
    TopicInfluenceClient,
    TopicInfluenceInvalidResponse,
    build_topic_influence_request,
    canonical_sha256,
)
from backend.app import topic_influence_worker


def _request():
    return build_topic_influence_request(
        tepp_run={
            "tepp_run_id": "tepp-synthetic-1",
            "tepp_artifact_sha256": "a" * 64,
            "source_snapshot_sha256": "b" * 64,
            "knowledge_cutoff": "2026-01-01T00:00:00+00:00",
            "posterior_draw_set_id": "draws-1",
            "posterior_draw_count": 2,
            "coordinate_kind_code": "plausible_value",
            "topic_model_run_id": "model-1",
        },
        topics=[0, 1],
        observations=[
            {
                "post_id": "synthetic-post-1",
                "event_time": "2025-12-01T00:00:00+00:00",
                "coordinates": [
                    {"topic_index": topic, "posterior_draw_ordinal": draw, "value": value}
                    for topic, draw, value in (
                        (0, 0, -0.2),
                        (0, 1, -0.1),
                        (1, 0, 0.2),
                        (1, 1, 0.1),
                    )
                ],
                "memberships": [
                    {
                        "membership_id": f"membership-{index}",
                        "dimension_code": dimension,
                        "context_id": f"synthetic-{dimension}",
                        "weight": 1.0,
                        "valid_from": "2025-01-01T00:00:00+00:00",
                        "valid_to": "2027-01-01T00:00:00+00:00",
                        "evidence_sha256": "c" * 64,
                        "provenance_assertion_id": "assertion-1",
                    }
                    for index, dimension in enumerate(
                        ("business_unit", "process_unit", "team", "person"), 1
                    )
                ],
            }
        ],
    )


def _response(request):
    response = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "request_sha256": request.request_sha256,
        "tepp_run_id": "tepp-synthetic-1",
        "source_snapshot_sha256": "b" * 64,
        "knowledge_cutoff": "2026-01-01T00:00:00+00:00",
        "membership_fingerprint_sha256": request.membership_fingerprint_sha256,
        "producer_version": "0.1.0",
        "code_revision": "d" * 40,
        "compute_backend_code": "rust_cpu",
        "precision_code": "f64",
        "posterior_draw_coverage": 2,
        "convergence_status_code": "converged",
        "identification_status_code": "identified",
        "parity_status_code": "passed",
        "influences": [
            {
                "post_id": "synthetic-post-1",
                "membership_id": f"membership-{membership}",
                "topic_index": topic,
                "influence_value": 0.25,
                "uncertainty_method_code": "posterior_draw_interval",
                "uncertainty_lower_value": 0.2,
                "uncertainty_upper_value": 0.3,
                "diagnostic_status_code": "accepted",
            }
            for membership in (1, 2, 3, 4)
            for topic in (0, 1)
        ],
    }
    response["artifact_sha256"] = canonical_sha256(response)
    return response


def test_client_accepts_only_complete_digest_bound_result() -> None:
    """Every post-membership-topic cell remains exact and auditable."""
    request = _request()
    result = TopicInfluenceClient(lambda _payload: _response(request)).estimate(request)

    assert result.payload["artifact_sha256"] == _response(request)["artifact_sha256"]
    assert len(result.payload["influences"]) == 8


@pytest.mark.parametrize("mutation", ["request", "digest", "partial", "nonfinite"])
def test_client_rejects_mixed_or_incomplete_results(mutation: str) -> None:
    """No mismatched, partial, or non-finite producer row reaches persistence."""
    request = _request()
    response = copy.deepcopy(_response(request))
    if mutation == "request":
        response["request_sha256"] = "e" * 64
    elif mutation == "digest":
        response["artifact_sha256"] = "e" * 64
    elif mutation == "partial":
        response["influences"].pop()
        response["artifact_sha256"] = canonical_sha256(
            {key: value for key, value in response.items() if key != "artifact_sha256"}
        )
    else:
        response["influences"][0]["influence_value"] = float("nan")
        response["artifact_sha256"] = canonical_sha256(
            {key: value for key, value in response.items() if key != "artifact_sha256"}
        )

    with pytest.raises(TopicInfluenceInvalidResponse):
        TopicInfluenceClient(lambda _payload: response).estimate(request)


def test_request_rejects_incomplete_tepp_posterior_draws() -> None:
    """A hard label or partial posterior cannot become fast-mlsirm input."""
    request = _request()
    observations = copy.deepcopy(request.payload["observations"])
    observations[0]["coordinates"].pop()

    with pytest.raises(ValueError, match="coordinates are incomplete"):
        build_topic_influence_request(
            tepp_run=dict(request.payload["tepp_run"]),
            topics=list(request.payload["topic_indices"]),
            observations=observations,
        )


def test_worker_persists_one_valid_result_without_local_math(monkeypatch) -> None:
    """The worker delegates once and passes the validated result to persistence."""
    request = _request()
    persisted: list[tuple[str, str]] = []

    async def claim(_pool):
        return "model-1", request

    async def persist(_pool, run_id, accepted_request, result):
        persisted.append((run_id, result.payload["request_sha256"]))
        assert accepted_request is request

    monkeypatch.setattr(topic_influence_worker, "claim_topic_influence_job", claim)
    monkeypatch.setattr(topic_influence_worker, "persist_topic_influence_result", persist)

    worked = asyncio.run(
        topic_influence_worker.process_topic_influence_job(
            object(), TopicInfluenceClient(lambda _payload: _response(request))
        )
    )

    assert worked is True
    assert persisted == [("model-1", request.request_sha256)]


def test_worker_records_invalid_result_without_persisting(monkeypatch) -> None:
    """Malformed owner output becomes a bounded failed job, never a score."""
    request = _request()
    failures: list[tuple[str, str]] = []

    async def claim(_pool):
        return "model-1", request

    async def fail(_pool, run_id, code):
        failures.append((run_id, code))

    async def forbidden(*_args):
        raise AssertionError("invalid result reached persistence")

    monkeypatch.setattr(topic_influence_worker, "claim_topic_influence_job", claim)
    monkeypatch.setattr(topic_influence_worker, "_fail_job", fail)
    monkeypatch.setattr(topic_influence_worker, "persist_topic_influence_result", forbidden)

    worked = asyncio.run(
        topic_influence_worker.process_topic_influence_job(
            object(), TopicInfluenceClient(lambda _payload: {})
        )
    )

    assert worked is True
    assert failures == [("model-1", "producer_result_invalid")]


def test_worker_distinguishes_unavailable_transport(monkeypatch) -> None:
    """Transport outage remains distinct from rejected scientific evidence."""
    request = _request()
    failures: list[tuple[str, str]] = []

    async def claim(_pool):
        return "model-1", request

    async def fail(_pool, run_id, code):
        failures.append((run_id, code))

    def unavailable(_payload):
        raise OSError("synthetic transport unavailable")

    monkeypatch.setattr(topic_influence_worker, "claim_topic_influence_job", claim)
    monkeypatch.setattr(topic_influence_worker, "_fail_job", fail)

    asyncio.run(
        topic_influence_worker.process_topic_influence_job(
            object(), TopicInfluenceClient(unavailable)
        )
    )

    assert failures == [("model-1", "producer_unavailable")]


def test_loader_requires_receipt_bound_complete_tepp_evidence() -> None:
    """The database projection becomes a request only with every evidence row."""
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    class Connection:
        async def fetchrow(self, sql, *_args):
            assert "analysis_run_tepp_receipt" in sql
            return {
                "topic_model_run_id": "model-1",
                "tepp_run_id": "tepp-synthetic-1",
                "tepp_artifact_sha256": "a" * 64,
                "posterior_draw_set_id": "draws-1",
                "posterior_draw_count": 2,
                "coordinate_kind_code": "plausible_value",
                "snapshot_sha256": "b" * 64,
                "knowledge_cutoff": now,
            }

        async def fetch(self, sql, *_args):
            if "from topic_definition" in sql:
                return [{"topic_index": 0}, {"topic_index": 1}]
            if "select distinct membership.source_post_id" in sql:
                return [{"source_post_id": "post-1", "event_time": now}]
            if "from topic_post_coordinate" in sql:
                return [
                    {
                        "topic_index": topic,
                        "posterior_draw_ordinal": draw,
                        "coordinate_value": value,
                    }
                    for topic, draw, value in (
                        (0, 0, -0.2),
                        (0, 1, -0.1),
                        (1, 0, 0.2),
                        (1, 1, 0.1),
                    )
                ]
            return [
                {
                    "topic_context_membership_id": f"membership-{index}",
                    "dimension_code": dimension,
                    "context_id": f"synthetic-{dimension}",
                    "membership_weight": 1.0,
                    "valid_from": now,
                    "valid_to": datetime(2027, 1, 1, tzinfo=timezone.utc),
                    "evidence_sha256": "c" * 64,
                    "provenance_assertion_id": f"assertion-{index}",
                }
                for index, dimension in enumerate(
                    ("business_unit", "process_unit", "team", "person"), 1
                )
            ]

    request = asyncio.run(
        topic_influence_worker.load_topic_influence_request(Connection(), "model-1")
    )

    assert request.payload["tepp_run"]["tepp_artifact_sha256"] == "a" * 64
    assert len(request.payload["observations"][0]["memberships"]) == 4


def test_persistence_rechecks_digest_and_writes_every_validated_row(monkeypatch) -> None:
    """The short transaction stores the run, all rows, and terminal lease."""
    request = _request()
    result = TopicInfluenceClient(lambda _payload: _response(request)).estimate(request)

    class Connection:
        def __init__(self):
            self.executed: list[str] = []

        def transaction(self):
            return _async_context(self)

        async def fetchrow(self, _sql, *_args):
            return {"request_sha256": request.request_sha256}

        async def fetchval(self, sql, *_args):
            self.executed.append(sql)
            return "influence-run-1"

        async def execute(self, sql, *_args):
            self.executed.append(sql)

    connection = Connection()

    class Pool:
        def acquire(self):
            return _async_context(connection)

    async def current(_conn, _run_id):
        return request

    monkeypatch.setattr(topic_influence_worker, "load_topic_influence_request", current)

    asyncio.run(
        topic_influence_worker.persist_topic_influence_result(
            Pool(), "model-1", request, result
        )
    )

    influence_inserts = sum(
        "insert into topic_post_context_influence" in sql
        for sql in connection.executed
    )
    assert influence_inserts == 8
    assert any("status_code = 'succeeded'" in sql for sql in connection.executed)


@asynccontextmanager
async def _async_context(value):
    """Yield one async context-manager test double."""
    yield value
