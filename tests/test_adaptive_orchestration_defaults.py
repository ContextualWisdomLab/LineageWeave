"""Adaptive contextual-orchestrator defaults remain explicit at every consumer boundary."""

from __future__ import annotations

import json

import pytest

from lineageweave.commitment_extraction import (
    ContextualOrchestratorCommitmentExtractionClient,
)
from lineageweave.entity_relationship_classification import (
    ContextualOrchestratorEntityRelationshipClient,
)
from lineageweave.keyman_extraction import (
    ContextualOrchestratorKeymanExtractionClient,
)
from lineageweave.post_evaluation import (
    ContextualOrchestratorPostEvaluationClient,
    CriterionResponse,
    irt_responses_from_result,
)
from lineageweave.post_summary import ContextualOrchestratorPostSummaryClient


@pytest.mark.parametrize(
    ("module_name", "client_factory", "invoke", "content"),
    [
        (
            "lineageweave.post_summary",
            lambda: ContextualOrchestratorPostSummaryClient("https://orchestrator.test", "token"),
            lambda client: client.summarize("Title", "Body"),
            json.dumps(
                {
                    "korean_summary": "요약",
                    "key_events": [],
                    "roles_and_responsibilities": [],
                }
            ),
        ),
        (
            "lineageweave.keyman_extraction",
            lambda: ContextualOrchestratorKeymanExtractionClient(
                "https://orchestrator.test", "token"
            ),
            lambda client: client.extract("Title", "Body"),
            "[]",
        ),
        (
            "lineageweave.commitment_extraction",
            lambda: ContextualOrchestratorCommitmentExtractionClient(
                "https://orchestrator.test", "token"
            ),
            lambda client: client.extract("Title", "Body", "2026-08-16"),
            json.dumps(
                {
                    "has_commitment": False,
                    "commitment_summary": None,
                    "due_date": None,
                }
            ),
        ),
        (
            "lineageweave.entity_relationship_classification",
            lambda: ContextualOrchestratorEntityRelationshipClient(
                "https://orchestrator.test", "token"
            ),
            lambda client: client.classify("Title", "Body", ["Example Corp"]),
            json.dumps(
                [
                    {
                        "organization_name": "Example Corp",
                        "relationship_type_code": "rel_voc",
                    }
                ]
            ),
        ),
    ],
)
def test_structured_consumers_request_auto_mode(
    monkeypatch, module_name, client_factory, invoke, content
) -> None:
    observed: dict[str, object] = {}
    call_count = 0

    def fake_post_json(url, payload, *, headers, timeout):
        nonlocal call_count
        call_count += 1
        observed["url"] = url
        observed["payload"] = payload
        observed["headers"] = headers
        observed["timeout"] = timeout
        response_content = content
        if module_name == "lineageweave.post_summary":
            response_content = (
                "요약\nKEY EVENTS: NONE"
                if call_count == 1
                else "ROLES:\nNONE\nPROJECTS:\nNONE"
            )
        return {"choices": [{"message": {"content": response_content}}]}

    module = __import__(module_name, fromlist=["post_json"])
    monkeypatch.setattr(module, "post_json", fake_post_json)

    invoke(client_factory())

    assert observed["payload"]["mode"] == "auto"
    assert observed["payload"]["reasoning_effort"] == "auto"
    if module_name == "lineageweave.post_summary":
        assert call_count == 2


def test_post_evaluation_judge_defaults_to_auto(monkeypatch) -> None:
    observed: dict[str, object] = {}

    def fake_post_json(url, payload, *, headers, timeout):
        observed["payload"] = payload
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "meets_threshold": True,
                                "rationale": "Evidence meets this boundary.",
                            }
                        )
                    }
                }
            ]
        }

    import lineageweave.post_evaluation as module

    monkeypatch.setattr(module, "post_json", fake_post_json)
    client = ContextualOrchestratorPostEvaluationClient(
        "https://orchestrator.test", "token"
    )

    result = client.evaluate("Title", "Body")

    assert observed["payload"]["mode"] == "auto"
    assert observed["payload"]["reasoning_effort"] == "auto"
    assert result.category_method == "binary_threshold"
    assert irt_responses_from_result(result) == tuple(
        CriterionResponse(criterion_code=criterion_id, response_category=4)
        for criterion_id in sorted(result.criterion_scores)
    )
