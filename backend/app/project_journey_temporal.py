"""Persist provider-owned temporal evidence for already-admitted journey edges."""

from __future__ import annotations

from typing import Any, Protocol

from lineageweave.temporal_journey_artifact import (
    ALLEN_RELATIONS,
    TemporalJourneyArtifact,
    parse_temporal_journey_artifact,
)


class TemporalArtifactConnection(Protocol):
    """Minimal transaction-scoped database port for artifact admission."""

    async def fetchrow(self, query: str, *args: object) -> Any:
        """Read one binding row."""

        ...

    async def execute(self, query: str, *args: object) -> Any:
        """Execute one immutable persistence statement."""

        ...

    async def executemany(self, query: str, args: list[tuple[object, ...]]) -> Any:
        """Execute bounded normalized child inserts."""

        ...


class TemporalArtifactAdmissionError(ValueError):
    """The artifact cannot be bound to the declared persisted run."""


async def persist_project_journey_temporal_artifact(
    conn: TemporalArtifactConnection,
    *,
    analysis_run_id: str,
    payload: bytes,
    expected_run_id: str,
    expected_snapshot_id: str,
    expected_input_digest_sha256: str,
    expected_artifact_digest_sha256: str,
) -> TemporalJourneyArtifact:
    """Validate and immutably persist temporal evidence for existing edges.

    The foreign key to ``post_lineage_edge`` is the semantic admission gate:
    interval order can corroborate an admitted predecessor, but cannot create
    a predecessor, branch, responsibility handoff, or causal transition.
    """

    artifact = parse_temporal_journey_artifact(
        payload,
        expected_run_id=expected_run_id,
        expected_snapshot_id=expected_snapshot_id,
        expected_input_digest_sha256=expected_input_digest_sha256,
        expected_artifact_digest_sha256=expected_artifact_digest_sha256,
    )
    binding = await conn.fetchrow(
        "select remote_run_id from analysis_run_tepp_result where analysis_run_id = $1::uuid",
        analysis_run_id,
    )
    if binding is None or str(binding["remote_run_id"]) != expected_run_id:
        raise TemporalArtifactAdmissionError("artifact run does not match a persisted terminal result")
    existing = await conn.fetchrow(
        "select artifact_digest_sha256 from project_journey_temporal_artifact "
        "where analysis_run_id = $1::uuid for update",
        analysis_run_id,
    )
    if existing is not None:
        if str(existing["artifact_digest_sha256"]) != expected_artifact_digest_sha256:
            raise TemporalArtifactAdmissionError("analysis run already has a different artifact")
        return artifact
    await conn.execute(
        "insert into project_journey_temporal_artifact "
        "(analysis_run_id, remote_run_id, schema_version, snapshot_id, input_digest_sha256, artifact_digest_sha256) "
        "values ($1::uuid, $2, $3, $4, $5, $6)",
        analysis_run_id,
        expected_run_id,
        "tepp.tdt_chronos_interval_consistency.v1",
        expected_snapshot_id,
        expected_input_digest_sha256,
        expected_artifact_digest_sha256,
    )
    relation_rows = [
        (analysis_run_id, relation.left_event_id, relation.right_event_id, relation.observed)
        for relation in artifact.relations
    ]
    await conn.executemany(
        "insert into project_journey_temporal_relation "
        "(analysis_run_id, left_post_id, right_post_id, observed) "
        "values ($1::uuid, $2::uuid, $3::uuid, $4)",
        relation_rows,
    )
    await conn.executemany(
        "insert into project_journey_temporal_relation_kind "
        "(analysis_run_id, left_post_id, right_post_id, relation_code, relation_ordinal) "
        "values ($1::uuid, $2::uuid, $3::uuid, $4, $5)",
        [
            (analysis_run_id, relation.left_event_id, relation.right_event_id, code, ALLEN_RELATIONS.index(code))
            for relation in artifact.relations
            for code in relation.allen_relations
        ],
    )
    await conn.executemany(
        "insert into project_journey_temporal_support "
        "(analysis_run_id, left_post_id, right_post_id, assertion_ordinal) "
        "values ($1::uuid, $2::uuid, $3::uuid, $4)",
        [
            (analysis_run_id, relation.left_event_id, relation.right_event_id, ordinal)
            for relation in artifact.relations
            for ordinal in relation.support_assertion_ordinals
        ],
    )
    return artifact
