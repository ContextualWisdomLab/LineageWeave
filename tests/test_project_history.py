"""Contracts for the Buyer project-history timeline."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import json

import pytest

from backend.app.project_history import (
    ProjectHistoryNotFound,
    ProjectHistoryConnection,
    _fetch_topic_lineage_projection,
    fetch_project_history_index,
    fetch_project_history_projection,
)
from lineageweave.topic_lineage_artifact import topic_lineage_artifact_sha256
from lineageweave.project_history import (
    build_project_history_projection,
    classify_project_event,
    normalize_project_key,
    responsibility_transition_code,
)


def _event_row(post_id: str = "00000000-0000-0000-0000-000000000001") -> dict[str, object]:
    """Return one synthetic authorized source row for pure projection tests."""

    return {
        "post_id": post_id,
        "post_title": "Contract awarded",
        "created_at": datetime(2022, 3, 11, 9, tzinfo=timezone.utc),
        "voc_type_code": None,
        "source_stage_code": None,
        "source_detail_state_code": None,
    }


class _IndexConnection:
    """Return one bounded index row for repository-level contract tests."""

    def __init__(self, rows=None) -> None:
        self.rows = rows or [
            {
                "normalized_project_key": "p-100",
                "project_key": "P-100",
                "project_name": "Synthetic project",
                "truth_status_code": "observed",
                "event_count": 2,
                "latest_event_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
                "source_scan_truncated": False,
            }
        ]
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, query: str, *args: object):
        """Capture bounded index arguments and return configured rows."""
        self.calls.append((query, args))
        return self.rows


class _ProjectionConnection:
    """Return event, optional focus, and child rows in query order."""

    def __init__(self, events, focus=()) -> None:
        self.events = list(events)
        self.focus = list(focus)
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, query: str, *args: object):
        """Serve the projection query sequence without bypassing its bounds."""
        self.calls.append((query, args))
        if len(self.calls) == 1:
            return self.events
        if "post_id = $4::uuid" in query:
            return self.focus
        return []


def test_topic_lineage_repository_filters_to_authorized_post_ids() -> None:
    """Persisted TEPP evidence is digest-bound before visible projection."""

    artifact = {
        "schema_version": "tepp.trsl_topic_lineage.v1",
        "run_id": "tepp-run-1",
        "snapshot_id": "ab" * 32,
        "knowledge_cutoff": "2026-01-12T12:00:00Z",
        "selected_seed": 7,
        "iterations": 4,
        "objective": 1.25,
        "topic_count": 2,
        "evidence_count": 2,
        "connected_post_count": 2,
        "lineage_count": 1,
        "sequence_edges": [
            {
                "predecessor_document_id": "00000000-0000-0000-0000-000000000001",
                "successor_document_id": "00000000-0000-0000-0000-000000000002",
                "topic_index": 0,
                "association_strength": 0.8,
            }
        ],
        "inference_status": "fitted_topic_association_not_causation",
    }
    envelope = {
        "status": "completed",
        "run_id": "tepp-run-1",
        "result_schema_version": artifact["schema_version"],
        "result_sha256": topic_lineage_artifact_sha256(artifact),
        "result": artifact,
    }
    stored = json.dumps(envelope, separators=(",", ":"), sort_keys=True)
    invalid_contract = {**envelope, "result_schema_version": "unknown"}
    invalid_contract_stored = json.dumps(
        invalid_contract, separators=(",", ":"), sort_keys=True
    )

    class Connection:
        async def fetch(self, query: str, *args: object):
            assert "analysis_run_topic_lineage_result" in query
            return [
                {
                    "result_json": "{not-json",
                    "result_sha256": "0" * 64,
                    "remote_run_id": "tepp-run-1",
                    "snapshot_sha256": "ab" * 32,
                    "knowledge_cutoff": datetime(2026, 1, 12, 12, tzinfo=timezone.utc),
                },
                {
                    "result_json": stored,
                    "result_sha256": "0" * 64,
                    "remote_run_id": "tepp-run-1",
                    "snapshot_sha256": "ab" * 32,
                    "knowledge_cutoff": datetime(2026, 1, 12, 12, tzinfo=timezone.utc),
                },
                {
                    "result_json": invalid_contract_stored,
                    "result_sha256": hashlib.sha256(invalid_contract_stored.encode()).hexdigest(),
                    "remote_run_id": "tepp-run-1",
                    "snapshot_sha256": "ab" * 32,
                    "knowledge_cutoff": datetime(2026, 1, 12, 12, tzinfo=timezone.utc),
                },
                {
                    "result_json": stored,
                    "result_sha256": hashlib.sha256(stored.encode()).hexdigest(),
                    "remote_run_id": "tepp-run-1",
                    "snapshot_sha256": "ab" * 32,
                    "knowledge_cutoff": datetime(2026, 1, 12, 12, tzinfo=timezone.utc),
                }
            ]

    projection = asyncio.run(
        _fetch_topic_lineage_projection(
            Connection(),
            visible_ids=[
                "00000000-0000-0000-0000-000000000001",
                "00000000-0000-0000-0000-000000000002",
            ],
            corporate_entity_ids=["11111111-1111-1111-1111-111111111111"],
            knowledge_cutoff=datetime(2026, 8, 20, tzinfo=timezone.utc),
        )
    )

    assert projection["connected_post_count"] == 2
    assert projection["lineage_count"] == 1


def test_project_history_keeps_an_already_visible_focus_without_a_second_lookup() -> None:
    """A visible focus stays in the authorized page without a focus query."""

    event = _event_row()
    connection = _ProjectionConnection([event])
    result = asyncio.run(
        fetch_project_history_projection(
            connection,
            project_key="P-100",
            focus_post_id=str(event["post_id"]),
            knowledge_cutoff=datetime(2026, 8, 20, tzinfo=timezone.utc),
            corporate_entity_ids=[],
        )
    )

    assert result["focus_event_id"] == event["post_id"]
    assert all("post_id = $4::uuid" not in query for query, _ in connection.calls)


def test_project_identity_is_exact_but_unicode_compatible() -> None:
    """Compatibility forms may normalize; fuzzy project binding may not."""

    assert normalize_project_key("  Ｐ－１００  ") == "p-100"
    assert normalize_project_key("P-100-A") != normalize_project_key("P-100")
    with pytest.raises(ValueError):
        normalize_project_key("   ")


def test_event_display_classification_does_not_create_authority() -> None:
    """The lifecycle label is presentation metadata over an existing post."""

    assert (
        classify_project_event(
            title="Contract awarded",
            source_stage_code=None,
            source_detail_state_code=None,
            voc_type_code=None,
            is_focus=False,
        )
        == "contract_awarded"
    )
    for is_focus in (False, True):
        assert (
            classify_project_event(
                title="Field complaint received",
                source_stage_code=None,
                source_detail_state_code=None,
                voc_type_code="voc",
                is_focus=is_focus,
            )
            == "voc_received"
        )


def test_responsibility_transition_describes_document_evidence_only() -> None:
    """Missing adjacent evidence is a visible evidence gap, not an HR fact."""

    assert responsibility_transition_code(["person:a"], ["person:a"]) == "continuous"
    assert responsibility_transition_code(["person:a"], ["person:b"]) == "handoff"
    assert responsibility_transition_code(["person:a"], []) == "assignment_gap"


def test_focused_assignment_gap_without_role_evidence_has_no_truth_status() -> None:
    """Two empty role sets must not manufacture an observed assignment fact."""
    second = _event_row("00000000-0000-0000-0000-000000000002")
    second["created_at"] = datetime(2022, 3, 12, 9, tzinfo=timezone.utc)

    projection = build_project_history_projection(
        project_key="P-100",
        focus_event_id=None,
        event_rows=[_event_row(), second],
        match_rows=[],
        role_rows=[],
        edge_rows=[],
    )

    transition = projection["events"][1]
    assert transition["responsibility_transition_code"] == "assignment_gap"
    assert transition["responsibility_transition_truth_status_code"] is None


@pytest.mark.parametrize("invalid_score", [float("nan"), float("inf"), float("-inf")])
def test_project_history_rejects_nonfinite_lineage_scores(invalid_score: float) -> None:
    """A non-finite edge score cannot enter the JSON evidence projection."""

    second = _event_row("00000000-0000-0000-0000-000000000002")
    second["created_at"] = datetime(2022, 3, 12, 9, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="lineage score must be finite"):
        build_project_history_projection(
            project_key="P-100",
            focus_event_id=None,
            event_rows=[_event_row(), second],
            match_rows=[],
            role_rows=[],
            edge_rows=[
                {
                    "parent_post_id": "00000000-0000-0000-0000-000000000001",
                    "child_post_id": "00000000-0000-0000-0000-000000000002",
                    "fused_score": invalid_score,
                }
            ],
        )


def test_project_history_counts_connected_posts_and_distinct_lineages() -> None:
    """Only forward edges form connected-post and lineage-component counts."""

    events = []
    for ordinal in range(1, 7):
        event = _event_row(f"00000000-0000-0000-0000-{ordinal:012d}")
        event["created_at"] = datetime(2022, 3, 10 + ordinal, 9, tzinfo=timezone.utc)
        events.append(event)
    edges = [
        {
            "parent_post_id": events[0]["post_id"],
            "child_post_id": events[1]["post_id"],
            "fused_score": 0.9,
        },
        {
            "parent_post_id": events[1]["post_id"],
            "child_post_id": events[2]["post_id"],
            "fused_score": 0.8,
        },
        {
            "parent_post_id": events[3]["post_id"],
            "child_post_id": events[4]["post_id"],
            "fused_score": 0.7,
        },
        {
            "parent_post_id": events[1]["post_id"],
            "child_post_id": events[2]["post_id"],
            "fused_score": 0.8,
        },
        {
            "parent_post_id": events[5]["post_id"],
            "child_post_id": events[0]["post_id"],
            "fused_score": 0.6,
        },
    ]

    projection = build_project_history_projection(
        project_key="P-100",
        focus_event_id=None,
        event_rows=events,
        match_rows=[],
        role_rows=[],
        edge_rows=edges,
    )

    assert projection["event_count"] == 6
    assert projection["connected_post_count"] is None
    assert projection["lineage_count"] is None
    assert projection["evidence_connected_post_count"] == 5
    assert projection["evidence_lineage_count"] == 2
    assert projection["topic_lineage"]["status"] == "unavailable"


def test_matching_observed_project_code_keeps_its_distinct_display_name() -> None:
    """A matching code may carry a human display name that is not itself the key."""

    event_id = "00000000-0000-0000-0000-000000000001"
    projection = build_project_history_projection(
        project_key="P-100",
        focus_event_id=event_id,
        event_rows=[_event_row(event_id)],
        match_rows=[
            {
                "post_id": event_id,
                "match_kind_code": "source_project_code",
                "matched_value": "P-100",
                "confidence": None,
                "ontology_iri": None,
                "provenance": "source_post.source_project_code",
            },
            {
                "post_id": event_id,
                "match_kind_code": "source_project_name",
                "identity_key": "P-100",
                "matched_value": "Transformer renewal",
                "confidence": None,
                "ontology_iri": None,
                "provenance": "source_post.source_project_name",
            },
        ],
        role_rows=[],
        edge_rows=[],
    )

    assert projection["project_name"] == "Transformer renewal"
    assert [row["matched_value"] for row in projection["events"][0]["project_matches"]] == [
        "P-100",
        "Transformer renewal",
    ]


def test_project_name_cannot_inherit_a_sibling_project_identity() -> None:
    """A display-name row without its own key cannot leak another project."""

    event_id = "00000000-0000-0000-0000-000000000001"
    projection = build_project_history_projection(
        project_key="P-100",
        focus_event_id=event_id,
        event_rows=[_event_row(event_id)],
        match_rows=[
            {
                "post_id": event_id,
                "match_kind_code": "source_project_code",
                "matched_value": "P-100",
                "confidence": None,
                "ontology_iri": None,
                "provenance": "source_post.source_project_code",
            },
            {
                "post_id": event_id,
                "match_kind_code": "source_project_name",
                "matched_value": "Unrelated project",
                "confidence": None,
                "ontology_iri": None,
                "provenance": "source_post.source_project_name",
            },
        ],
        role_rows=[],
        edge_rows=[],
    )

    assert [row["matched_value"] for row in projection["events"][0]["project_matches"]] == ["P-100"]


def test_summary_responsibilities_remain_inferred_evidence() -> None:
    """LLM-derived summary roles must not become observed or an HR assignment ledger."""

    event_id = "00000000-0000-0000-0000-000000000001"
    projection = build_project_history_projection(
        project_key="P-100",
        focus_event_id=event_id,
        event_rows=[_event_row(event_id)],
        match_rows=[
            {
                "post_id": event_id,
                "match_kind_code": "source_project_code",
                "matched_value": "P-100",
                "confidence": None,
                "ontology_iri": None,
                "provenance": "source_post.source_project_code",
            }
        ],
        role_rows=[
            {
                "post_id": event_id,
                "actor_name": "Synthetic Project Manager",
                "responsibility": "Coordinate the specification revision",
                "actor_type_code": "prov_person",
                "affiliated_organization_name": "Demo Corp",
                "cataloged_person_id": None,
                "cataloged_team_id": None,
                "cataloged_corporate_entity_id": None,
                "truth_status_code": "inferred",
                "provenance": "post_summary_role",
            }
        ],
        edge_rows=[],
    )

    role = projection["events"][0]["responsibility_evidence"][0]
    assert role["truth_status_code"] == "inferred"
    assert role["provenance"] == "post_summary_role"


def test_assignment_gap_without_role_evidence_has_no_truth_status() -> None:
    """An empty adjacent evidence pair remains unknown, never observed."""

    first = _event_row("00000000-0000-0000-0000-000000000001")
    second = _event_row("00000000-0000-0000-0000-000000000002")
    second["created_at"] = datetime(2022, 3, 12, 9, tzinfo=timezone.utc)
    projection = build_project_history_projection(
        project_key="P-100",
        focus_event_id=second["post_id"],
        event_rows=[first, second],
        match_rows=[],
        role_rows=[],
        edge_rows=[],
    )

    transition = projection["events"][1]
    assert transition["responsibility_transition_code"] == "assignment_gap"
    assert transition["responsibility_transition_truth_status_code"] is None


def test_project_history_connection_protocol_fails_explicitly() -> None:
    """The protocol default is not an executable ellipsis/no-op."""

    async def invoke() -> None:
        await ProjectHistoryConnection.fetch(object(), "select 1")

    with pytest.raises(NotImplementedError):
        asyncio.run(invoke())


def test_invalid_focus_identifier_fails_before_a_database_cast() -> None:
    """A malformed focus identifier must fail closed before reaching PostgreSQL."""

    class FocusConnection:
        def __init__(self) -> None:
            self.calls = 0

        async def fetch(self, query: str, *args: object) -> list[dict[str, object]]:
            self.calls += 1
            if self.calls == 1:
                return [_event_row()]
            raise AssertionError("malformed focus identifier reached a database query")

    connection = FocusConnection()
    with pytest.raises(ValueError, match="focus_post_id"):
        asyncio.run(
            fetch_project_history_projection(
                connection,
                project_key="P-100",
                focus_post_id="not-a-uuid",
                knowledge_cutoff=datetime(2026, 8, 20, tzinfo=timezone.utc),
                corporate_entity_ids=[],
            )
        )
    assert connection.calls == 0


def test_project_history_index_is_authorized_bounded_and_versioned() -> None:
    """The index exposes only the versioned, bounded projection contract."""
    connection = _IndexConnection()
    result = asyncio.run(
        fetch_project_history_index(
            connection,
            knowledge_cutoff=datetime(2026, 8, 20, tzinfo=timezone.utc),
            corporate_entity_ids=["corp-1"],
            limit=1,
        )
    )

    assert result["contract_version"] == 1
    assert result["project_count"] == 1
    assert result["projects"][0]["truth_status_code"] == "observed"
    assert result["projects"][0]["latest_event_at"] == "2026-01-02T00:00:00Z"
    assert result["knowledge_cutoff"] == "2026-08-20T00:00:00Z"
    assert connection.calls[0][1][0] == ["corp-1"]
    assert connection.calls[0][1][-2] == 2
    assert "set_config(" in connection.calls[0][0]
    assert "'statement_timeout'" in connection.calls[0][0]
    assert "limit ($4 + 1)" in connection.calls[0][0]

    connection.rows[0]["source_scan_truncated"] = True
    truncated = asyncio.run(
        fetch_project_history_index(
            connection,
            knowledge_cutoff=datetime(2026, 8, 20, tzinfo=timezone.utc),
            corporate_entity_ids=["corp-1"],
            limit=1,
        )
    )
    assert truncated["truncated"] is True

    with pytest.raises(ValueError):
        asyncio.run(
            fetch_project_history_index(
                connection,
                knowledge_cutoff=datetime(2026, 8, 20, tzinfo=timezone.utc),
                corporate_entity_ids=[],
                limit=201,
            )
        )
    with pytest.raises(ValueError, match="offset-aware"):
        asyncio.run(
            fetch_project_history_index(
                connection,
                knowledge_cutoff=datetime(2026, 8, 20),
                corporate_entity_ids=[],
            )
        )


def test_project_history_projection_keeps_focus_and_authorization_bounds() -> None:
    """A focused event outside the first page is appended only when returned by the focus query."""
    first = _event_row("00000000-0000-0000-0000-000000000001")
    second = _event_row("00000000-0000-0000-0000-000000000002")
    second["created_at"] = datetime(2026, 1, 2, tzinfo=timezone.utc)
    focus = _event_row("00000000-0000-0000-0000-000000000099")
    focus["created_at"] = datetime(2026, 1, 3, tzinfo=timezone.utc)
    connection = _ProjectionConnection([first, second, focus], [focus])

    result = asyncio.run(
        fetch_project_history_projection(
            connection,
            project_key="P-100",
            focus_post_id="00000000-0000-0000-0000-000000000099",
            knowledge_cutoff=datetime(2026, 8, 20, tzinfo=timezone.utc),
            corporate_entity_ids=[],
            limit=2,
        )
    )

    assert result["truncated"] is True
    assert result["focus_event_id"] == "00000000-0000-0000-0000-000000000099"
    assert result["knowledge_cutoff"] == "2026-08-20T00:00:00Z"
    assert len(connection.calls) == 6
    assert connection.calls[0][1][-1] == 3


def test_project_history_projection_empty_and_invalid_focus_fail_closed() -> None:
    """Missing authorized evidence and malformed boundaries never become a result."""
    with pytest.raises(ProjectHistoryNotFound):
        asyncio.run(
            fetch_project_history_projection(
                _ProjectionConnection([]),
                project_key="P-100",
                focus_post_id=None,
                knowledge_cutoff=datetime(2026, 8, 20, tzinfo=timezone.utc),
                corporate_entity_ids=[],
            )
        )
    first = _event_row()
    with pytest.raises(ProjectHistoryNotFound):
        asyncio.run(
            fetch_project_history_projection(
                _ProjectionConnection([first], []),
                project_key="P-100",
                focus_post_id="00000000-0000-0000-0000-000000000099",
                knowledge_cutoff=datetime(2026, 8, 20, tzinfo=timezone.utc),
                corporate_entity_ids=[],
            )
        )
    with pytest.raises(ValueError):
        asyncio.run(
            fetch_project_history_projection(
                _ProjectionConnection([first]),
                project_key="P-100",
                focus_post_id=None,
                knowledge_cutoff=datetime(2026, 8, 20, tzinfo=timezone.utc),
                corporate_entity_ids=[],
                limit=0,
            )
        )
    with pytest.raises(ValueError, match="offset-aware"):
        asyncio.run(
            fetch_project_history_projection(
                _ProjectionConnection([first]),
                project_key="P-100",
                focus_post_id=None,
                knowledge_cutoff=datetime(2026, 8, 20),
                corporate_entity_ids=[],
            )
        )
