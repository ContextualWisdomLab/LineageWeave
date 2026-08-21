"""Security and evidence contracts for opt-in Global Ask web verification."""

from __future__ import annotations

import pytest

from backend.app import global_ask_verification as verification


def test_public_search_query_never_contains_internal_answer_text() -> None:
    question = "Is this public ontology statement correct?"
    internal_answer = "CONFIDENTIAL-CUSTOMER-ANSWER-SHOULD-NOT-BE-SEARCHED"

    query = verification._bounded_search_query(question)

    assert query == question
    assert internal_answer not in query


def test_supported_without_valid_external_citation_downgrades_to_insufficient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = verification.SearxngOrchestratorGlobalAskVerifier(
        "https://search.example",
        "https://orchestrator.example",
        "secret",
    )
    monkeypatch.setattr(
        verification,
        "get_json",
        lambda *_args, **_kwargs: {
            "results": [
                {
                    "title": "Evidence",
                    "url": "https://evidence.example/fact",
                    "content": "Relevant public evidence",
                }
            ]
        },
    )
    monkeypatch.setattr(
        verification,
        "post_json",
        lambda *_args, **_kwargs: {
            "choices": [
                {
                    "message": {
                        "content": '{"status_code":"supported","cited_evidence_numbers":[],"rationale":"claim"}'
                    }
                }
            ]
        },
    )

    result = verifier.verify("public question", "internal answer")

    assert result.status_code == verification.STATUS_INSUFFICIENT
    assert result.evidence_urls == ()


def test_fenced_structured_judgment_is_parsed_without_accepting_extra_prose() -> None:
    parsed = verification._parse_judgment(
        '```json\n{"status_code":"refuted","cited_evidence_numbers":[1],"rationale":"contradicted"}\n```'
    )
    assert parsed == {
        "status_code": "refuted",
        "cited_evidence_numbers": [1],
        "rationale": "contradicted",
    }
