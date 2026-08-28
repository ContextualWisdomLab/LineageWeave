"""Contract tests for TEPP-bound fast-mlsirm topic influence."""

from __future__ import annotations

import copy
import asyncio
import base64
import hashlib
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytest

from lineageweave.topic_influence_client import (
    HttpTopicInfluenceClient,
    RESULT_SCHEMA_VERSION,
    TopicInfluenceClient,
    TopicInfluenceInvalidResponse,
    build_topic_influence_request,
)
from lineageweave.http_client import HttpAdmissionDeferred
from lineageweave import topic_influence_client
from backend.app import topic_influence_worker
from backend.app.config import load_settings

_LEASE_TOKEN = "11111111-1111-4111-8111-111111111111"


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


def _artifact(request):
    return {
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


def _response(request, artifact=None):
    payload = artifact if artifact is not None else _artifact(request)
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    return {
        "artifact_sha256": hashlib.sha256(raw).hexdigest(),
        "artifact_base64": base64.b64encode(raw).decode("ascii"),
    }


def test_client_accepts_only_complete_digest_bound_result() -> None:
    """Every post-membership-topic cell remains exact and auditable."""
    request = _request()
    result = TopicInfluenceClient(lambda _payload: _response(request), lease_timeout_seconds=17).estimate(request)

    assert result.payload["artifact_sha256"] == _response(request)["artifact_sha256"]
    assert len(result.payload["influences"]) == 8


def test_request_digest_covers_lineage_owned_raw_wire_bytes() -> None:
    """The producer receives exact request bytes and echoes their opaque digest."""
    request = _request()
    wire = request.to_json()

    assert set(wire) == {"request_sha256", "request_base64"}
    raw = base64.b64decode(wire["request_base64"], validate=True)
    assert hashlib.sha256(raw).hexdigest() == wire["request_sha256"]
    assert json.loads(raw) == request.payload
    membership_raw = base64.b64decode(
        request.payload["membership_artifact_base64"], validate=True
    )
    assert hashlib.sha256(membership_raw).hexdigest() == (
        request.membership_fingerprint_sha256
    )


def test_artifact_digest_covers_producer_supplied_raw_bytes() -> None:
    """Admission hashes exact producer bytes rather than reserializing floats."""
    request = _request()
    first = _response(request)
    differently_formatted = json.dumps(_artifact(request), indent=2).encode()
    second = {
        "artifact_sha256": hashlib.sha256(differently_formatted).hexdigest(),
        "artifact_base64": base64.b64encode(differently_formatted).decode("ascii"),
    }

    assert TopicInfluenceClient(lambda _payload: first, lease_timeout_seconds=17).estimate(request)
    assert TopicInfluenceClient(lambda _payload: second, lease_timeout_seconds=17).estimate(request)


def test_artifact_digest_is_checked_before_json_parse() -> None:
    """Tampered producer bytes fail their digest before any JSON interpretation."""
    request = _request()
    response = {
        "artifact_sha256": "e" * 64,
        "artifact_base64": base64.b64encode(b"not-json").decode("ascii"),
    }

    with pytest.raises(TopicInfluenceInvalidResponse, match="digest is invalid"):
        TopicInfluenceClient(
            lambda _payload: response, lease_timeout_seconds=17
        ).estimate(request)


@pytest.mark.parametrize("mutation", ["request", "digest", "partial", "nonfinite"])
def test_client_rejects_mixed_or_incomplete_results(mutation: str) -> None:
    """No mismatched, partial, or non-finite producer row reaches persistence."""
    request = _request()
    artifact = copy.deepcopy(_artifact(request))
    response = _response(request, artifact)
    if mutation == "request":
        artifact["request_sha256"] = "e" * 64
        response = _response(request, artifact)
    elif mutation == "digest":
        response["artifact_sha256"] = "e" * 64
    elif mutation == "partial":
        artifact["influences"].pop()
        response = _response(request, artifact)
    else:
        artifact["influences"][0]["influence_value"] = "not-finite"
        response = _response(request, artifact)

    with pytest.raises(TopicInfluenceInvalidResponse):
        TopicInfluenceClient(lambda _payload: response, lease_timeout_seconds=17).estimate(request)


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


def test_request_accepts_time_varying_membership_slices() -> None:
    """Distinct evidence rows may retain the same context across valid times."""
    request = _request()
    observations = copy.deepcopy(request.payload["observations"])
    later = copy.deepcopy(observations[0]["memberships"][0])
    later["membership_id"] = "membership-later"
    later["valid_from"] = "2027-01-01T00:00:00+00:00"
    later["valid_to"] = "2028-01-01T00:00:00+00:00"
    observations[0]["memberships"].append(later)

    accepted = build_topic_influence_request(
        tepp_run=dict(request.payload["tepp_run"]),
        topics=list(request.payload["topic_indices"]),
        observations=observations,
    )

    assert len(accepted.payload["observations"][0]["memberships"]) == 5


def test_request_requires_four_dimensions_across_run_not_each_post() -> None:
    """A post carries only evidenced levels while the run covers every level."""
    request = _request()
    first = copy.deepcopy(request.payload["observations"][0])
    second = copy.deepcopy(first)
    first["memberships"] = first["memberships"][:2]
    second["post_id"] = "synthetic-post-2"
    second["memberships"] = second["memberships"][2:]
    for membership in second["memberships"]:
        membership["membership_id"] += "-second"

    accepted = build_topic_influence_request(
        tepp_run=dict(request.payload["tepp_run"]),
        topics=list(request.payload["topic_indices"]),
        observations=[first, second],
    )

    assert [len(row["memberships"]) for row in accepted.payload["observations"]] == [2, 2]


def test_http_client_attributes_transport_to_numerical_owner(monkeypatch) -> None:
    """Topic influence spans identify fast-mlsirm rather than the orchestrator."""
    request = _request()
    captured: dict[str, object] = {}

    def post(_url, _payload, **kwargs):
        captured.update(kwargs)
        return _response(request)

    monkeypatch.setattr(topic_influence_client, "post_json", post)
    HttpTopicInfluenceClient(
        "https://synthetic.invalid", "", timeout=11.0, lease_timeout_seconds=17
    ).estimate(request)

    assert captured["service_peer_name"] == "fast-mlsirm"


def test_settings_preserve_declared_request_and_lease_contract(monkeypatch) -> None:
    """Runtime timeouts come only from explicit positive deployment values."""
    monkeypatch.setenv("TOPIC_INFLUENCE_REQUEST_TIMEOUT_SECONDS", "11")
    monkeypatch.setenv("TOPIC_INFLUENCE_LEASE_TIMEOUT_SECONDS", "17")
    monkeypatch.setenv("TOPIC_INFLUENCE_POLL_SECONDS", "13")

    settings = load_settings()

    assert settings.topic_influence_request_timeout_seconds == 11
    assert settings.topic_influence_lease_timeout_seconds == 17
    assert settings.topic_influence_poll_seconds == 13


@pytest.mark.parametrize("lease_timeout", [0, -1, 1.5, True])
def test_client_rejects_undeclared_or_invalid_lease(lease_timeout: object) -> None:
    """A worker cannot invent or weaken the provider request lease."""
    with pytest.raises(ValueError, match="positive integer"):
        TopicInfluenceClient(lambda _payload: {}, lease_timeout_seconds=lease_timeout)


@pytest.mark.parametrize("request_timeout", [0, -1, float("inf"), True])
def test_http_client_rejects_invalid_request_timeout(request_timeout: object) -> None:
    """The outbound request contract requires a positive finite timeout."""
    with pytest.raises(ValueError, match="positive finite"):
        HttpTopicInfluenceClient(
            "https://synthetic.invalid",
            "",
            timeout=request_timeout,
            lease_timeout_seconds=17,
        )


def test_worker_persists_one_valid_result_without_local_math(monkeypatch) -> None:
    """The worker delegates once and passes the validated result to persistence."""
    request = _request()
    persisted: list[tuple[str, str]] = []

    async def claim(_pool, _lease_seconds):
        return "model-1", request, _LEASE_TOKEN

    async def persist(_pool, run_id, accepted_request, result, lease_token):
        persisted.append((run_id, result.payload["request_sha256"]))
        assert accepted_request is request
        assert lease_token == _LEASE_TOKEN

    monkeypatch.setattr(topic_influence_worker, "claim_topic_influence_job", claim)
    monkeypatch.setattr(topic_influence_worker, "persist_topic_influence_result", persist)

    worked = asyncio.run(
        topic_influence_worker.process_topic_influence_job(
            object(), TopicInfluenceClient(lambda _payload: _response(request), lease_timeout_seconds=17)
        )
    )

    assert worked is True
    assert persisted == [("model-1", request.request_sha256)]


def test_worker_records_invalid_result_without_persisting(monkeypatch) -> None:
    """Malformed owner output becomes a bounded failed job, never a score."""
    request = _request()
    failures: list[tuple[str, str]] = []

    async def claim(_pool, _lease_seconds):
        return "model-1", request, _LEASE_TOKEN

    async def fail(_pool, run_id, lease_token, code):
        assert lease_token == _LEASE_TOKEN
        failures.append((run_id, code))

    async def forbidden(*_args):
        raise AssertionError("invalid result reached persistence")

    monkeypatch.setattr(topic_influence_worker, "claim_topic_influence_job", claim)
    monkeypatch.setattr(topic_influence_worker, "_fail_job", fail)
    monkeypatch.setattr(topic_influence_worker, "persist_topic_influence_result", forbidden)

    worked = asyncio.run(
        topic_influence_worker.process_topic_influence_job(
            object(), TopicInfluenceClient(lambda _payload: {}, lease_timeout_seconds=17)
        )
    )

    assert worked is True
    assert failures == [("model-1", "producer_result_invalid")]


def test_worker_distinguishes_unavailable_transport(monkeypatch) -> None:
    """Transport outage remains distinct from rejected scientific evidence."""
    request = _request()
    failures: list[tuple[str, str]] = []

    async def claim(_pool, _lease_seconds):
        return "model-1", request, _LEASE_TOKEN

    async def fail(_pool, run_id, lease_token, code):
        assert lease_token == _LEASE_TOKEN
        failures.append((run_id, code))

    def unavailable(_payload):
        raise OSError("synthetic transport unavailable")

    monkeypatch.setattr(topic_influence_worker, "claim_topic_influence_job", claim)
    monkeypatch.setattr(topic_influence_worker, "_fail_job", fail)

    asyncio.run(
        topic_influence_worker.process_topic_influence_job(
            object(), TopicInfluenceClient(unavailable, lease_timeout_seconds=17)
        )
    )

    assert failures == [("model-1", "producer_unavailable")]


def test_worker_uses_exact_remote_retry_delay(monkeypatch) -> None:
    """A remote admission delay requeues exactly, without invented backoff."""
    request = _request()
    deferred: list[tuple[str, int]] = []

    async def claim(_pool, _lease_seconds):
        return "model-1", request, _LEASE_TOKEN

    async def defer(_pool, run_id, lease_token, seconds):
        assert lease_token == _LEASE_TOKEN
        deferred.append((run_id, seconds))

    def unavailable(_payload):
        raise HttpAdmissionDeferred(17)

    monkeypatch.setattr(topic_influence_worker, "claim_topic_influence_job", claim)
    monkeypatch.setattr(topic_influence_worker, "_defer_job", defer)

    asyncio.run(
        topic_influence_worker.process_topic_influence_job(
            object(), TopicInfluenceClient(unavailable, lease_timeout_seconds=17)
        )
    )

    assert deferred == [("model-1", 17)]


def test_worker_releases_changed_input_for_a_fresh_request(monkeypatch) -> None:
    """A changed digest is re-leased instead of becoming operator-only failure."""
    request = _request()
    released: list[str] = []

    async def claim(_pool, _lease_seconds):
        return "model-1", request, _LEASE_TOKEN

    async def changed(*_args):
        raise topic_influence_worker.TopicInfluenceInputChanged("changed")

    async def release(_pool, run_id, lease_token):
        assert lease_token == _LEASE_TOKEN
        released.append(run_id)

    monkeypatch.setattr(topic_influence_worker, "claim_topic_influence_job", claim)
    monkeypatch.setattr(topic_influence_worker, "persist_topic_influence_result", changed)
    monkeypatch.setattr(topic_influence_worker, "_release_changed_job", release)

    asyncio.run(
        topic_influence_worker.process_topic_influence_job(
            object(),
            TopicInfluenceClient(
                lambda _payload: _response(request), lease_timeout_seconds=17
            ),
        )
    )

    assert released == ["model-1"]


def test_worker_retries_transient_claim_database_failure(monkeypatch) -> None:
    """One transient claim failure cannot terminate the durable consumer task."""
    calls: list[str] = []

    async def process(_pool, _client):
        calls.append("process")
        if calls.count("process") == 1:
            raise topic_influence_worker.asyncpg.PostgresError("synthetic unavailable")
        raise asyncio.CancelledError

    async def sleep(seconds):
        assert seconds == 13
        calls.append("sleep")

    monkeypatch.setattr(topic_influence_worker, "process_topic_influence_job", process)
    monkeypatch.setattr(topic_influence_worker.asyncio, "sleep", sleep)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            topic_influence_worker.run_topic_influence_worker(
                object(), lambda: object(), poll_seconds=13
            )
        )

    assert calls == ["process", "sleep", "process"]


def test_claim_scans_past_incomplete_evidence(monkeypatch) -> None:
    """Older incomplete requests cannot starve a later complete request."""
    request = _request()
    statements: list[str] = []

    class Connection:
        async def execute(self, sql, *_args):
            statements.append(sql)
            return "UPDATE 1"

        async def fetch(self, sql):
            assert "limit 10" not in sql.lower()
            assert "not_before <= clock_timestamp()" in sql
            return [
                {"topic_model_run_id": f"incomplete-{index}"}
                for index in range(11)
            ] + [{"topic_model_run_id": "complete"}]

        def transaction(self):
            return _async_context(self)

        async def fetchval(
            self, _sql, run_id, _digest, _lease_seconds, _lease_token
        ):
            return run_id

    class Pool:
        def acquire(self):
            return _async_context(Connection())

    async def load(_conn, run_id):
        if run_id != "complete":
            raise ValueError("synthetic incomplete evidence")
        return request

    monkeypatch.setattr(topic_influence_worker, "load_topic_influence_request", load)

    claimed = asyncio.run(topic_influence_worker.claim_topic_influence_job(Pool(), 17))

    assert claimed is not None
    assert claimed[:2] == ("complete", request)
    assert uuid.UUID(claimed[2])
    assert any("lease_expires_at <= clock_timestamp()" in sql for sql in statements)
    assert sum("awaiting_evidence" in sql for sql in statements) == 11


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
    result = TopicInfluenceClient(lambda _payload: _response(request), lease_timeout_seconds=17).estimate(request)

    class Connection:
        def __init__(self):
            self.executed: list[str] = []

        def transaction(self):
            return _async_context(self)

        async def fetchrow(self, _sql, *_args):
            return {
                "request_sha256": request.request_sha256,
                "lease_token": _LEASE_TOKEN,
            }

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
            Pool(), "model-1", request, result, _LEASE_TOKEN
        )
    )

    influence_inserts = sum(
        "insert into topic_post_context_influence" in sql
        for sql in connection.executed
    )
    assert influence_inserts == 8
    assert any("status_code = 'succeeded'" in sql for sql in connection.executed)
    assert any("lease_token = $2::uuid" in sql for sql in connection.executed)


def test_every_running_transition_is_bound_to_the_exact_lease() -> None:
    """A stale worker cannot fail, defer, or release a replacement lease."""
    statements: list[tuple[str, tuple[object, ...]]] = []

    class Connection:
        async def execute(self, sql, *args):
            statements.append((sql, args))

    class Pool:
        def acquire(self):
            return _async_context(Connection())

    async def exercise() -> None:
        await topic_influence_worker._fail_job(
            Pool(), "model-1", _LEASE_TOKEN, "producer_unavailable"
        )
        await topic_influence_worker._defer_job(
            Pool(), "model-1", _LEASE_TOKEN, 17
        )
        await topic_influence_worker._release_changed_job(
            Pool(), "model-1", _LEASE_TOKEN
        )

    asyncio.run(exercise())

    assert len(statements) == 3
    assert all("lease_token = $2::uuid" in sql for sql, _args in statements)
    assert all(args[1] == _LEASE_TOKEN for _sql, args in statements)


@asynccontextmanager
async def _async_context(value):
    """Yield one async context-manager test double."""
    yield value
