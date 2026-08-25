"""Execution tests for the external Naruon-facing lineage adapter."""

from __future__ import annotations

import pytest

from lineageweave.channel_weight_estimation import estimate_fixture_channel_weights
from lineageweave.external_lineage_analysis import (
    _BoundedAdjudicationClient,
    _channel_evidence,
    _selected_llm,
)
from lineageweave.external_lineage_analysis import (
    analyze_external_lineage as _analyze_external_lineage,
)
from lineageweave.external_lineage_contract import (
    LineageContractError,
    parse_lineage_analysis_request,
    request_digest,
    result_digest,
)

_FIXTURE_ESTIMATE = estimate_fixture_channel_weights()
assert _FIXTURE_ESTIMATE is not None
_FIXTURE_WEIGHTS = dict(_FIXTURE_ESTIMATE.weights)
# Four identical-information synthetic items have equal normalized expected
# information; this vector is test truth, never a production fallback.
_EQUAL_INFORMATION_WEIGHTS = {
    "temporal": 0.25,
    "secondary_key": 0.25,
    "text": 0.25,
    "llm": 0.25,
}


def analyze_external_lineage(request, *, llm=None):
    """Run the adapter with psychometrically estimated synthetic-fixture weights."""
    return _analyze_external_lineage(request, channel_weights=_FIXTURE_WEIGHTS, llm=llm)


def test_external_analysis_rejects_missing_calibrated_weights() -> None:
    """The public adapter never supplies compatibility weights."""
    request = _request([_record("email:001", "One", "2026-08-20T09:00:00Z")])
    with pytest.raises(LineageContractError, match="channel_weights"):
        _analyze_external_lineage(request, channel_weights={})


class AvailableLlm:
    """Deterministic available adjudication channel for contract tests."""

    available = True

    def judge(self, candidate_label: str, record_label: str) -> float:
        """Return a high score for labels sharing their first token."""

        return (
            0.9
            if candidate_label.split()[0] == record_label.split()[0]
            else 0.1
        )


class InvalidLlm:
    """Available client returning an invalid score for fail-closed coverage."""

    available = True

    def judge(self, candidate_label: str, record_label: str) -> float:
        """Return an intentionally invalid value."""

        return 2.0


class TextLlm:
    """Available client returning a non-numeric score."""

    available = True

    def judge(self, candidate_label: str, record_label: str) -> str:
        """Return an intentionally malformed score."""

        return "unknown"


class BrokenProviderLlm:
    """Available client surfacing an unexpected raw provider failure."""

    available = True

    def judge(self, candidate_label: str, record_label: str) -> float:
        """Raise a raw provider message that must not cross the contract."""

        raise RuntimeError("provider secret response body")


class CountingLlm:
    """Available client recording calls for pre-provider budget tests."""

    available = True

    def __init__(self) -> None:
        """Initialize an empty call counter."""

        self.call_count = 0

    def judge(self, candidate_label: str, record_label: str) -> float:
        """Count one call and return a bounded score."""

        self.call_count += 1
        return 0.5


@pytest.mark.parametrize(
    "weights",
    [
        {"temporal": 0.5, "secondary_key": 0.25, "text": 0.25, "unknown": 0.1},
        {"temporal": True, "secondary_key": 0.5, "text": 0.5},
        {"temporal": float("nan"), "secondary_key": 0.5, "text": 0.5},
        {"temporal": 0.0, "secondary_key": 0.5, "text": 0.5},
        {"temporal": 0.2, "secondary_key": 0.2, "text": 0.2},
    ],
)
def test_external_analysis_rejects_malformed_calibrated_weights(weights) -> None:
    """Malformed host vectors fail closed without repair or renormalization."""
    request = _request([_record("email:001", "One", "2026-08-20T09:00:00Z")])
    with pytest.raises(LineageContractError, match="channel_weights"):
        _analyze_external_lineage(request, channel_weights=weights)


@pytest.mark.parametrize(
    ("client", "code"),
    [
        (InvalidLlm(), "channel_score_out_of_bounds"),
        (TextLlm(), "channel_score_out_of_bounds"),
        (BrokenProviderLlm(), "llm_channel_error"),
    ],
)
def test_bounded_llm_rejects_unusable_scores(client, code: str) -> None:
    """The calibrated-channel wrapper exposes only stable contract errors."""
    with pytest.raises(LineageContractError) as captured:
        _BoundedAdjudicationClient(client).judge("Parent", "Child")
    assert captured.value.code == code


def test_selected_llm_marks_an_admitted_calibrated_channel_not_used() -> None:
    """Admission alone is not reported as a completed provider call."""
    request = _request(
        [_record("email:001", "Same parent", "2026-08-20T09:00:00Z")],
        allow_llm=True,
    )
    client, status = _selected_llm(request, AvailableLlm(), {"llm": 1.0})
    assert client.judge("Same parent", "Same child") == 0.9
    assert status == "not_used"


def test_analysis_distinguishes_admitted_not_used_from_completed_llm() -> None:
    """Completion requires at least one actual adjudicator call."""
    single = _request(
        [_record("email:001", "Same parent", "2026-08-20T09:00:00Z")],
        allow_llm=True,
    )
    unused = _analyze_external_lineage(
        single,
        channel_weights=_EQUAL_INFORMATION_WEIGHTS,
        llm=AvailableLlm(),
    )
    assert unused.llm_status_code == "not_used"

    pair = _request(
        [
            _record("email:001", "Same parent", "2026-08-20T09:00:00Z"),
            _record("email:002", "Same child", "2026-08-20T09:01:00Z"),
        ],
        allow_llm=True,
    )
    completed = _analyze_external_lineage(
        pair,
        channel_weights=_EQUAL_INFORMATION_WEIGHTS,
        llm=AvailableLlm(),
    )
    assert completed.llm_status_code == "completed"
    assert "llm" in {
        channel.channel_code for channel in completed.edges[0].channel_evidence
    }


def _record(
    evidence_ref: str,
    label: str,
    occurred_at: str,
    *,
    available_at: str | None = None,
    secondary_key: str | None = "thread:opaque",
    project_ref: str | None = "project:opaque",
    explicit_parent: dict[str, str] | None = None,
    group_ref: str = "workspace:demo",
) -> dict[str, object]:
    return {
        "evidence_ref": evidence_ref,
        "group_ref": group_ref,
        "source_kind_code": "email",
        "truth_status_code": "observed",
        "label": label,
        "occurred_at": occurred_at,
        "available_at": available_at or occurred_at,
        "secondary_key": secondary_key,
        "project_ref": project_ref,
        "explicit_parent": explicit_parent,
    }


def _request(
    records: list[dict[str, object]],
    *,
    cutoff: str | None = None,
    allow_llm: bool = False,
    scope: str = "email_lineage",
):
    return parse_lineage_analysis_request(
        {
            "contract_version": "1.0.0",
            "analysis_id": "analysis:integration-001",
            "analysis_scope_code": scope,
            "knowledge_cutoff": cutoff,
            "policy": {
                "candidate_window": 50,
                "maximum_pair_evaluations": 1000,
                "minimum_fused_score": 0.1,
                "allow_llm": allow_llm,
            },
            "records": records,
        }
    )


def test_cutoff_uses_available_time_and_discloses_excluded_evidence() -> None:
    request = _request(
        [
            _record(
                "email:early",
                "Project update",
                "2026-08-18T09:00:00Z",
                available_at="2026-08-18T09:01:00Z",
            ),
            _record(
                "email:late",
                "Earlier event reported late",
                "2026-08-17T09:00:00Z",
                available_at="2026-08-20T09:00:00Z",
            ),
        ],
        cutoff="2026-08-19T00:00:00Z",
    )

    result = analyze_external_lineage(request)

    assert result.included_evidence_refs == ("email:early",)
    assert result.excluded_evidence_refs == ("email:late",)
    assert result.edges == ()
    assert [
        (item.limitation_code, item.evidence_ref)
        for item in result.limitations
    ] == [
        ("evidence_after_cutoff_excluded", "email:late"),
    ]


def test_explicit_rfc_reply_overrides_semantic_parent_and_remains_observed() -> None:
    request = _request(
        [
            _record(
                "email:observed-parent",
                "Unrelated root",
                "2026-08-20T09:00:00Z",
            ),
            _record(
                "email:semantic-parent",
                "Phoenix status",
                "2026-08-20T09:01:00Z",
            ),
            _record(
                "email:child",
                "Phoenix status follow-up",
                "2026-08-20T09:02:00Z",
                explicit_parent={
                    "evidence_ref": "email:observed-parent",
                    "relation_code": "rfc_reply",
                },
            ),
        ]
    )

    result = analyze_external_lineage(request)
    child_edges = [
        edge
        for edge in result.edges
        if edge.child_evidence_ref == "email:child"
    ]

    assert len(child_edges) == 1
    assert child_edges[0].parent_evidence_ref == "email:observed-parent"
    assert child_edges[0].relation_type_code == "rfc_reply"
    assert child_edges[0].truth_status_code == "observed"
    assert child_edges[0].channel_evidence[0].channel_code == "rfc_reply"


def test_inferred_edge_exposes_active_channel_weights_and_contributions() -> None:
    request = _request(
        [
            _record(
                "email:001",
                "Phoenix delivery status",
                "2026-08-20T09:00:00Z",
            ),
            _record(
                "email:002",
                "Phoenix delivery status update",
                "2026-08-20T09:05:00Z",
            ),
        ]
    )

    result = analyze_external_lineage(request)

    assert len(result.edges) == 1
    edge = result.edges[0]
    assert edge.truth_status_code == "inferred"
    assert edge.relation_type_code == "reconstructed_continuation"
    assert {item.channel_code for item in edge.channel_evidence} == {
        "temporal",
        "secondary_key",
        "text",
    }
    assert sum(item.weight for item in edge.channel_evidence) == pytest.approx(
        1.0
    )
    assert sum(
        item.contribution
        for item in edge.channel_evidence
    ) == pytest.approx(edge.fused_score)


@pytest.mark.parametrize(
    ("allow_llm", "client", "expected_status", "llm_present"),
    [
        (False, AvailableLlm(), "not_requested", False),
        (True, None, "unavailable", False),
        (True, AvailableLlm(), "unavailable", False),
    ],
)
def test_llm_policy_is_explicit_and_never_fabricates_absent_scores(
    allow_llm: bool,
    client,
    expected_status: str,
    llm_present: bool,
) -> None:
    request = _request(
        [
            _record(
                "email:001",
                "Phoenix delivery status",
                "2026-08-20T09:00:00Z",
            ),
            _record(
                "email:002",
                "Phoenix delivery status update",
                "2026-08-20T09:05:00Z",
            ),
        ],
        allow_llm=allow_llm,
    )

    result = analyze_external_lineage(request, llm=client)

    assert result.llm_status_code == expected_status
    channels = {
        channel.channel_code
        for channel in result.edges[0].channel_evidence
    }
    assert ("llm" in channels) is llm_present


def test_project_projection_is_proposed_and_uses_only_included_evidence() -> None:
    request = _request(
        [
            _record(
                "email:001",
                "One",
                "2026-08-20T09:00:00Z",
            ),
            _record(
                "email:002",
                "Two",
                "2026-08-20T09:01:00Z",
            ),
            _record(
                "email:003",
                "Late",
                "2026-08-18T09:00:00Z",
                available_at="2026-08-22T09:00:00Z",
            ),
        ],
        cutoff="2026-08-21T00:00:00Z",
        scope="project_history",
    )

    result = analyze_external_lineage(request)

    assert result.project_projections[0].project_ref == "project:opaque"
    assert result.project_projections[0].evidence_refs == (
        "email:001",
        "email:002",
    )
    assert result.project_projections[0].truth_status_code == "proposed"


def test_analysis_is_deterministic_for_reordered_input_and_has_digest() -> None:
    records = [
        _record(
            "email:001",
            "Phoenix delivery status",
            "2026-08-20T09:00:00Z",
        ),
        _record(
            "email:002",
            "Phoenix delivery status update",
            "2026-08-20T09:05:00Z",
        ),
    ]
    first_request = _request(records)
    second_request = _request(list(reversed(records)))

    first = analyze_external_lineage(first_request)
    second = analyze_external_lineage(second_request)

    assert request_digest(first_request) == request_digest(second_request)
    assert first == second
    assert first.result_digest.startswith("sha256:")
    assert result_digest(first) == first.result_digest


@pytest.mark.parametrize(
    ("records", "expected_code"),
    [
        (
            [
                _record(
                    "email:child",
                    "Child",
                    "2026-08-20T09:00:00Z",
                    explicit_parent={
                        "evidence_ref": "email:missing",
                        "relation_code": "rfc_reply",
                    },
                )
            ],
            "explicit_parent_missing",
        ),
        (
            [
                _record(
                    "email:child",
                    "Child",
                    "2026-08-20T09:00:00Z",
                    explicit_parent={
                        "evidence_ref": "email:child",
                        "relation_code": "rfc_reply",
                    },
                )
            ],
            "explicit_parent_self_reference",
        ),
        (
            [
                _record(
                    "email:parent",
                    "Parent",
                    "2026-08-20T10:00:00Z",
                ),
                _record(
                    "email:child",
                    "Child",
                    "2026-08-20T09:00:00Z",
                    explicit_parent={
                        "evidence_ref": "email:parent",
                        "relation_code": "rfc_reply",
                    },
                ),
            ],
            "explicit_parent_after_child",
        ),
        (
            [
                _record(
                    "email:parent",
                    "Parent",
                    "2026-08-20T09:00:00Z",
                    group_ref="workspace:one",
                ),
                _record(
                    "email:child",
                    "Child",
                    "2026-08-20T10:00:00Z",
                    group_ref="workspace:two",
                    explicit_parent={
                        "evidence_ref": "email:parent",
                        "relation_code": "rfc_reply",
                    },
                ),
            ],
            "explicit_parent_group_mismatch",
        ),
    ],
)
def test_invalid_explicit_parent_semantics_fail_closed(
    records: list[dict[str, object]],
    expected_code: str,
) -> None:
    request = _request(records)

    with pytest.raises(LineageContractError) as captured:
        analyze_external_lineage(request)

    assert captured.value.code == expected_code


def test_explicit_parent_cycle_fails_closed_even_when_timestamps_tie() -> None:
    request = _request(
        [
            _record(
                "email:one",
                "One",
                "2026-08-20T09:00:00Z",
                explicit_parent={
                    "evidence_ref": "email:two",
                    "relation_code": "rfc_reply",
                },
            ),
            _record(
                "email:two",
                "Two",
                "2026-08-20T09:00:00Z",
                explicit_parent={
                    "evidence_ref": "email:one",
                    "relation_code": "rfc_reply",
                },
            ),
        ]
    )

    with pytest.raises(LineageContractError) as captured:
        analyze_external_lineage(request)

    assert captured.value.code == "explicit_parent_cycle"


def test_cutoff_excluded_explicit_parent_creates_limitation_not_edge() -> None:
    request = _request(
        [
            _record(
                "email:parent",
                "Parent",
                "2026-08-18T09:00:00Z",
                available_at="2026-08-22T09:00:00Z",
            ),
            _record(
                "email:child",
                "Child",
                "2026-08-20T09:00:00Z",
                available_at="2026-08-20T09:01:00Z",
                explicit_parent={
                    "evidence_ref": "email:parent",
                    "relation_code": "rfc_reply",
                },
            ),
        ],
        cutoff="2026-08-21T00:00:00Z",
    )

    result = analyze_external_lineage(request)

    assert all(
        edge.relation_type_code != "rfc_reply"
        for edge in result.edges
    )
    assert any(
        item.limitation_code == "explicit_parent_after_cutoff"
        and item.evidence_ref == "email:child"
        for item in result.limitations
    )


def test_all_evidence_after_cutoff_returns_empty_bounded_result() -> None:
    request = _request(
        [
            _record(
                "email:late",
                "Late",
                "2026-08-18T09:00:00Z",
                available_at="2026-08-22T09:00:00Z",
                project_ref=None,
            )
        ],
        cutoff="2026-08-21T00:00:00Z",
    )

    result = analyze_external_lineage(request)

    assert result.included_evidence_refs == ()
    assert result.edges == ()
    assert result.project_projections == ()


def test_uncalibrated_llm_channel_is_not_invoked() -> None:
    request = _request(
        [
            _record(
                "email:001",
                "Phoenix one",
                "2026-08-20T09:00:00Z",
            ),
            _record(
                "email:002",
                "Phoenix two",
                "2026-08-20T09:01:00Z",
            ),
        ],
        allow_llm=True,
    )

    result = analyze_external_lineage(request, llm=InvalidLlm())
    assert result.llm_status_code == "unavailable"


def test_uncalibrated_text_llm_channel_is_not_invoked() -> None:
    """An uncalibrated optional channel stays unavailable."""

    request = _request(
        [
            _record("email:001", "Phoenix one", "2026-08-20T09:00:00Z"),
            _record("email:002", "Phoenix two", "2026-08-20T09:01:00Z"),
        ],
        allow_llm=True,
    )

    result = analyze_external_lineage(request, llm=TextLlm())
    assert result.llm_status_code == "unavailable"


def test_uncalibrated_broken_provider_is_not_invoked() -> None:
    """A provider is not called until its channel has calibrated weight."""

    request = _request(
        [
            _record("email:001", "Phoenix one", "2026-08-20T09:00:00Z"),
            _record("email:002", "Phoenix two", "2026-08-20T09:01:00Z"),
        ],
        allow_llm=True,
    )

    result = analyze_external_lineage(request, llm=BrokenProviderLlm())
    assert result.llm_status_code == "unavailable"


def test_channel_evidence_rejects_invalid_score_before_serialization() -> None:
    """Defense in depth keeps direct channel projection fail-closed."""

    with pytest.raises(LineageContractError) as captured:
        _channel_evidence({"text": 2.0}, {"text": 1.0})

    assert captured.value.code == "channel_score_out_of_bounds"


def test_records_without_project_reference_are_not_projected() -> None:
    request = _request(
        [
            _record(
                "email:001",
                "No project",
                "2026-08-20T09:00:00Z",
                project_ref=None,
            )
        ]
    )

    result = analyze_external_lineage(request)

    assert result.project_projections == ()


def test_cutoff_excluded_explicit_parent_suppresses_alternative_inference() -> None:
    request = _request(
        [
            _record(
                "email:alternative",
                "Phoenix child",
                "2026-08-20T08:00:00Z",
                available_at="2026-08-20T08:01:00Z",
            ),
            _record(
                "email:observed-parent",
                "Observed parent",
                "2026-08-18T09:00:00Z",
                available_at="2026-08-22T09:00:00Z",
            ),
            _record(
                "email:child",
                "Phoenix child",
                "2026-08-20T09:00:00Z",
                available_at="2026-08-20T09:01:00Z",
                explicit_parent={
                    "evidence_ref": "email:observed-parent",
                    "relation_code": "rfc_reply",
                },
            ),
        ],
        cutoff="2026-08-21T00:00:00Z",
    )

    result = analyze_external_lineage(request)

    assert all(
        edge.child_evidence_ref != "email:child"
        for edge in result.edges
    )


def test_project_projections_do_not_merge_across_groups() -> None:
    request = _request(
        [
            _record(
                "email:one",
                "One",
                "2026-08-20T09:00:00Z",
                group_ref="workspace:one",
            ),
            _record(
                "email:two",
                "Two",
                "2026-08-20T09:00:00Z",
                group_ref="workspace:two",
            ),
        ],
        scope="project_history",
    )

    result = analyze_external_lineage(request)
    projections = [
        (item.group_ref, item.project_ref, item.evidence_refs)
        for item in result.project_projections
    ]

    assert projections == [
        ("workspace:one", "project:opaque", ("email:one",)),
        ("workspace:two", "project:opaque", ("email:two",)),
    ]


def test_pair_budget_rejects_before_any_optional_llm_call() -> None:
    records = [
        _record(
            f"email:{index}",
            f"Message {index}",
            f"2026-08-20T09:0{index}:00Z",
        )
        for index in range(4)
    ]
    payload = {
        "contract_version": "1.0.0",
        "analysis_id": "analysis:pair-budget",
        "analysis_scope_code": "email_lineage",
        "knowledge_cutoff": None,
        "policy": {
            "candidate_window": 50,
            "maximum_pair_evaluations": 2,
            "minimum_fused_score": 0.1,
            "allow_llm": True,
        },
        "records": records,
    }
    request = parse_lineage_analysis_request(payload)
    client = CountingLlm()

    with pytest.raises(LineageContractError) as captured:
        analyze_external_lineage(request, llm=client)

    assert captured.value.code == "pair_evaluation_budget_exceeded"
    assert client.call_count == 0


def test_missing_cutoff_includes_all_records() -> None:
    request = _request(
        [
            _record(
                "email:one",
                "One",
                "2026-08-20T09:00:00Z",
            ),
            _record(
                "email:two",
                "Two",
                "2026-08-21T09:00:00Z",
                available_at="2026-09-01T09:00:00Z",
            ),
        ],
        cutoff=None,
    )

    result = analyze_external_lineage(request)

    assert result.included_evidence_refs == ("email:one", "email:two")
    assert result.excluded_evidence_refs == ()
