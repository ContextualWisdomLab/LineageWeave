"""Typed temporal-artifact admission tests."""

from __future__ import annotations

import asyncio
import hashlib
import json

import pytest

from backend.app.project_journey_temporal import (
    TemporalArtifactAdmissionError,
    persist_project_journey_temporal_artifact,
)
from lineageweave.temporal_journey_artifact import (
    TemporalJourneyArtifactError,
    parse_temporal_journey_artifact,
)


def _payload(*, run_id: str = "remote-1") -> bytes:
    return json.dumps(
        {
            "schema_version": "tepp.tdt_chronos_interval_consistency.v1",
            "run_id": run_id,
            "snapshot_id": "snapshot-1",
            "input_digest_sha256": "a" * 64,
            "relations": [{
                "left_event_id": "00000000-0000-0000-0000-000000000001",
                "right_event_id": "00000000-0000-0000-0000-000000000002",
                "allen_relations": ["before", "meets"],
                "observed": False,
                "support_assertion_ordinals": [0, 2],
            }],
        },
        separators=(",", ":"),
    ).encode()


def _parse(payload: bytes):
    return parse_temporal_journey_artifact(
        payload,
        expected_run_id="remote-1",
        expected_snapshot_id="snapshot-1",
        expected_input_digest_sha256="a" * 64,
        expected_artifact_digest_sha256=hashlib.sha256(payload).hexdigest(),
    )


def test_parser_binds_canonical_bytes_and_all_identities() -> None:
    """The admitted DTO retains no unbound provider field."""

    result = _parse(_payload())
    assert result.relations[0].allen_relations == ("before", "meets")
    assert result.relations[0].support_assertion_ordinals == (0, 2)


@pytest.mark.parametrize("mutation", ["digest", "run", "unknown", "order"])
def test_parser_rejects_changed_or_noncanonical_artifacts(mutation: str) -> None:
    """Malformed, moved, or noncanonical payloads fail closed."""

    payload = _payload(run_id="other" if mutation == "run" else "remote-1")
    if mutation == "unknown":
        value = json.loads(payload)
        value["extra"] = True
        payload = json.dumps(value, separators=(",", ":")).encode()
    if mutation == "order":
        value = json.loads(payload)
        value["relations"][0]["allen_relations"] = ["meets", "before"]
        payload = json.dumps(value, separators=(",", ":")).encode()
    digest = "b" * 64 if mutation == "digest" else hashlib.sha256(payload).hexdigest()
    with pytest.raises(TemporalJourneyArtifactError):
        parse_temporal_journey_artifact(
            payload,
            expected_run_id="remote-1",
            expected_snapshot_id="snapshot-1",
            expected_input_digest_sha256="a" * 64,
            expected_artifact_digest_sha256=digest,
        )


@pytest.mark.parametrize(
    ("payload", "input_digest", "artifact_digest"),
    [
        (b"", "a" * 64, "0" * 64),
        (b"{}", "bad", hashlib.sha256(b"{}").hexdigest()),
        (b"\xff", "a" * 64, hashlib.sha256(b"\xff").hexdigest()),
        (b" {\"x\":1}", "a" * 64, hashlib.sha256(b" {\"x\":1}").hexdigest()),
        (b"[]", "a" * 64, hashlib.sha256(b"[]").hexdigest()),
    ],
)
def test_parser_rejects_size_digest_encoding_and_top_level_shape(
    payload: bytes, input_digest: str, artifact_digest: str
) -> None:
    """Every outer wire boundary rejects before relation persistence."""

    with pytest.raises(TemporalJourneyArtifactError):
        parse_temporal_journey_artifact(
            payload,
            expected_run_id="remote-1",
            expected_snapshot_id="snapshot-1",
            expected_input_digest_sha256=input_digest,
            expected_artifact_digest_sha256=artifact_digest,
        )


def test_parser_rejects_empty_and_malformed_relation_collections() -> None:
    """An empty result or untyped relation is not journey evidence."""

    for relations in ([], ["not-an-object"]):
        value = json.loads(_payload())
        value["relations"] = relations
        payload = json.dumps(value, separators=(",", ":")).encode()
        with pytest.raises(TemporalJourneyArtifactError):
            _parse(payload)


class _Connection:
    """Capture the normalized producer statements."""

    def __init__(
        self,
        remote_run_id: str = "remote-1",
        existing_digest: str | None = None,
    ) -> None:
        self.remote_run_id = remote_run_id
        self.existing_digest = existing_digest
        self.execute_calls: list[tuple[str, tuple[object, ...]]] = []
        self.many_calls: list[tuple[str, list[tuple[object, ...]]]] = []

    async def fetchrow(self, query: str, *args: object):
        """Return the terminal binding and no prior artifact."""

        if "analysis_run_tepp_result" in query:
            return {"remote_run_id": self.remote_run_id}
        return (
            {"artifact_digest_sha256": self.existing_digest}
            if self.existing_digest is not None
            else None
        )

    async def execute(self, query: str, *args: object):
        """Capture artifact metadata persistence."""

        self.execute_calls.append((query, args))

    async def executemany(self, query: str, args: list[tuple[object, ...]]):
        """Capture normalized relation children."""

        self.many_calls.append((query, args))


def test_producer_persists_relation_kinds_and_support_separately() -> None:
    """One accepted artifact produces normalized, auditable rows."""

    payload = _payload()
    connection = _Connection()
    asyncio.run(
        persist_project_journey_temporal_artifact(
            connection,
            analysis_run_id="00000000-0000-0000-0000-000000000010",
            payload=payload,
            expected_run_id="remote-1",
            expected_snapshot_id="snapshot-1",
            expected_input_digest_sha256="a" * 64,
            expected_artifact_digest_sha256=hashlib.sha256(payload).hexdigest(),
        )
    )
    assert len(connection.execute_calls) == 1
    assert [len(rows) for _query, rows in connection.many_calls] == [1, 2, 2]


def test_producer_rejects_a_terminal_run_mismatch() -> None:
    """A valid artifact cannot be attached to another persisted run."""

    payload = _payload()
    with pytest.raises(TemporalArtifactAdmissionError):
        asyncio.run(
            persist_project_journey_temporal_artifact(
                _Connection("different"),
                analysis_run_id="00000000-0000-0000-0000-000000000010",
                payload=payload,
                expected_run_id="remote-1",
                expected_snapshot_id="snapshot-1",
                expected_input_digest_sha256="a" * 64,
                expected_artifact_digest_sha256=hashlib.sha256(payload).hexdigest(),
            )
        )


def test_producer_is_idempotent_and_rejects_changed_artifact() -> None:
    """A run may replay identical bytes but cannot change immutable evidence."""

    payload = _payload()
    digest = hashlib.sha256(payload).hexdigest()
    same = _Connection(existing_digest=digest)
    asyncio.run(
        persist_project_journey_temporal_artifact(
            same,
            analysis_run_id="00000000-0000-0000-0000-000000000010",
            payload=payload,
            expected_run_id="remote-1",
            expected_snapshot_id="snapshot-1",
            expected_input_digest_sha256="a" * 64,
            expected_artifact_digest_sha256=digest,
        )
    )
    assert same.execute_calls == []
    with pytest.raises(TemporalArtifactAdmissionError):
        asyncio.run(
            persist_project_journey_temporal_artifact(
                _Connection(existing_digest="b" * 64),
                analysis_run_id="00000000-0000-0000-0000-000000000010",
                payload=payload,
                expected_run_id="remote-1",
                expected_snapshot_id="snapshot-1",
                expected_input_digest_sha256="a" * 64,
                expected_artifact_digest_sha256=digest,
            )
        )
