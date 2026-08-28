"""Direct branch tests for evidence-gated similar-VOC adjudication.

The parser accepts only a positive result whose evidence strings appear
verbatim in the corresponding source bodies. These tests drive every
rejection guard and the client construction/boundary call.
"""

from __future__ import annotations

import json

import pytest

from lineageweave.similar_voc import (
    ContextualOrchestratorSimilarVocAnalysisClient,
    SimilarVocAnalysisClient,
    SimilarVocEvidence,
    parse_similar_voc_response,
)


_FOCAL = "The transformer cooling fan keeps tripping under load."
_CANDIDATE = "Cooling fan overload causes a shutdown after an hour of heavy load. A previous fix reused fan power from the blower circuit, which is the same issue."
_CANDIDATE_ID = "22222222-2222-2222-2222-222222222222"


def _payload(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "similar": True,
        "issue_summary": "Fan overload trips under load",
        "focal_evidence_text": "cooling fan keeps tripping",
        "candidate_evidence_text": "Cooling fan overload causes a shutdown",
        "customer_cohort_text": None,
        "action_history": ["reused fan power from the blower circuit"],
    }
    data.update(overrides)
    return data


def test_parse_accepts_a_positive_fully_cited_result() -> None:
    result = parse_similar_voc_response(
        json.dumps(_payload()), _CANDIDATE_ID, _FOCAL, _CANDIDATE
    )
    assert result is not None
    assert result.candidate_post_id == _CANDIDATE_ID
    assert result.action_history == ("reused fan power from the blower circuit",)


@pytest.mark.parametrize(
    "payload",
    [
        "not-json",
        None,
        {"similar": False},
        {"similar": "yes"},
        _payload(issue_summary="  "),
        _payload(focal_evidence_text="not in the focal body at all"),
        _payload(candidate_evidence_text="also never in the candidate"),
        _payload(customer_cohort_text="Acme"),
        _payload(customer_cohort_text=123),
        _payload(action_history="not-a-list"),
        _payload(action_history=["not in candidate body"]),
        _payload(action_history=[7]),
    ],
)
def test_parse_rejects_negative_or_uncited_results(payload: object) -> None:
    content = json.dumps(payload) if isinstance(payload, dict) else str(payload)
    assert (
        parse_similar_voc_response(content, _CANDIDATE_ID, _FOCAL, _CANDIDATE)
        is None
    )


def test_parse_accepts_a_null_cohort_and_normalizes_stripped_summary() -> None:
    payload = _payload(
        issue_summary="  Fan overload  ",
        customer_cohort_text=None,
    )
    result = parse_similar_voc_response(
        json.dumps(payload), _CANDIDATE_ID, _FOCAL, _CANDIDATE
    )
    assert result is not None
    assert result.issue_summary == "Fan overload"
    assert result.customer_cohort_text is None


def test_client_validate_contextual_orchestrator_construction(monkeypatch) -> None:
    """Construction strips trailing slashes and the boundary is called."""
    from lineageweave import similar_voc as similar_voc_mod

    calls: list[tuple[str, object]] = []

    def fake_post_json(url: str, payload: dict, *, headers=None, timeout=None):  # noqa: ANN001,ARG002
        calls.append((url, payload))
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "similar": True,
                                "issue_summary": "Fan overload",
                                "focal_evidence_text": "cooling fan keeps tripping",
                                "candidate_evidence_text": "Cooling fan overload causes a shutdown",
                                "customer_cohort_text": None,
                                "action_history": [
                                    "reused fan power from the blower circuit"
                                ],
                            }
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(similar_voc_mod, "post_json", fake_post_json)
    client = ContextualOrchestratorSimilarVocAnalysisClient(
        "https://orchestrator.test/", "synthetic-key", timeout=9
    )
    assert client._base_url == "https://orchestrator.test"
    result = client.analyze("t", _FOCAL, _CANDIDATE_ID, "c", _CANDIDATE)
    assert result is not None
    assert calls and calls[0][0].startswith("https://orchestrator.test/v1/chat/completions")
    assert calls[0][1]["mode"] == "auto"