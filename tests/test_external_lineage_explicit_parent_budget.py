"""Regression tests for explicit-parent budget and provider minimization."""

from __future__ import annotations

from lineageweave.external_lineage_analysis import analyze_external_lineage
from lineageweave.external_lineage_contract import parse_lineage_analysis_request


class CountingLlm:
    """Available adjudication client that records every disclosed label pair."""

    available = True

    def __init__(self) -> None:
        """Initialize an empty provider-call ledger."""

        self.calls: list[tuple[str, str]] = []

    def judge(self, candidate_label: str, record_label: str) -> float:
        """Record one adjudication pair and return a bounded score."""

        self.calls.append((candidate_label, record_label))
        return 0.5


def _record(
    evidence_ref: str,
    label: str,
    occurred_at: str,
    *,
    explicit_parent: str | None = None,
) -> dict[str, object]:
    """Build one synthetic authorized email evidence record."""

    return {
        "evidence_ref": evidence_ref,
        "group_ref": "workspace:synthetic",
        "source_kind_code": "email",
        "truth_status_code": "observed",
        "label": label,
        "occurred_at": occurred_at,
        "available_at": occurred_at,
        "secondary_key": "thread:synthetic",
        "project_ref": "project:synthetic",
        "explicit_parent": (
            {
                "evidence_ref": explicit_parent,
                "relation_code": "rfc_reply",
            }
            if explicit_parent is not None
            else None
        ),
    }


def _request(
    records: list[dict[str, object]],
    *,
    allow_llm: bool,
    maximum_pair_evaluations: int,
):
    """Parse one strict external-lineage request for the regression cases."""

    return parse_lineage_analysis_request(
        {
            "contract_version": "1.0.0",
            "analysis_id": "analysis:explicit-parent-budget",
            "analysis_scope_code": "email_lineage",
            "knowledge_cutoff": None,
            "policy": {
                "candidate_window": 50,
                "maximum_pair_evaluations": maximum_pair_evaluations,
                "minimum_fused_score": 0.1,
                "allow_llm": allow_llm,
            },
            "records": records,
        }
    )


def test_explicit_parent_chain_spends_no_inference_budget_or_llm_calls() -> None:
    """Caller-observed edges must not be rescored or charged as inferred work."""

    request = _request(
        [
            _record("email:one", "One", "2026-08-21T09:00:00Z"),
            _record(
                "email:two",
                "Two",
                "2026-08-21T09:01:00Z",
                explicit_parent="email:one",
            ),
            _record(
                "email:three",
                "Three",
                "2026-08-21T09:02:00Z",
                explicit_parent="email:two",
            ),
            _record(
                "email:four",
                "Four",
                "2026-08-21T09:03:00Z",
                explicit_parent="email:three",
            ),
        ],
        allow_llm=True,
        maximum_pair_evaluations=1,
    )
    client = CountingLlm()

    result = analyze_external_lineage(request, llm=client)

    assert client.calls == []
    assert [
        (
            edge.parent_evidence_ref,
            edge.child_evidence_ref,
            edge.truth_status_code,
        )
        for edge in result.edges
    ] == [
        ("email:one", "email:two", "observed"),
        ("email:two", "email:three", "observed"),
        ("email:three", "email:four", "observed"),
    ]


def test_explicit_child_remains_available_as_a_later_inference_candidate() -> None:
    """Skipping its own scoring must not remove an explicit child from history."""

    request = _request(
        [
            _record("email:root", "Root", "2026-08-21T09:00:00Z"),
            _record(
                "email:observed-child",
                "Phoenix delivery update",
                "2026-08-21T09:01:00Z",
                explicit_parent="email:root",
            ),
            _record(
                "email:later-child",
                "Phoenix delivery update",
                "2026-08-21T09:02:00Z",
            ),
        ],
        allow_llm=False,
        maximum_pair_evaluations=2,
    )

    result = analyze_external_lineage(request)

    assert any(
        edge.parent_evidence_ref == "email:observed-child"
        and edge.child_evidence_ref == "email:later-child"
        and edge.truth_status_code == "inferred"
        for edge in result.edges
    )
