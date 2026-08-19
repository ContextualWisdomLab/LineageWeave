"""External Global Ask verification keeps web corroboration separate from post authority."""

from __future__ import annotations

import pytest

from backend.app import global_ask_verification as verification
from lineageweave.http_client import HttpClientError


def test_search_results_are_bounded_deduplicated_and_http_only() -> None:
    payload = {
        "results": [
            {"title": "One", "url": "https://example.org/a", "content": "A" * 3000},
            {"title": "Duplicate", "url": "https://example.org/a", "content": "duplicate"},
            {"title": "Unsafe", "url": "file:///etc/passwd", "content": "unsafe"},
        ]
        + [
            {"title": f"Extra {index}", "url": f"https://example.org/{index}", "content": "x"}
            for index in range(10)
        ]
    }

    evidence = verification._parse_search_results(payload)

    assert len(evidence) == verification.MAX_EXTERNAL_RESULTS
    assert evidence[0].url == "https://example.org/a"
    assert len(evidence[0].snippet) == verification.MAX_EXTERNAL_SNIPPET_CHARS
    assert len({item.url for item in evidence}) == len(evidence)


def test_null_verifier_is_explicitly_unavailable() -> None:
    verifier = verification.NullGlobalAskExternalVerifier()
    assert verifier.available is False
    assert verifier.verify("question", "answer").status_code == verification.STATUS_UNAVAILABLE


def test_searxng_orchestrator_verifier_returns_only_cited_external_urls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = verification.SearxngOrchestratorGlobalAskVerifier(
        "https://search.example",
        "https://orchestrator.example",
        "secret",
    )
    calls: dict[str, object] = {}

    def fake_get_json(url: str, *, timeout: float):
        calls["search_url"] = url
        calls["search_timeout"] = timeout
        return {
            "results": [
                {"title": "Evidence A", "url": "https://a.example/fact", "content": "supports claim"},
                {"title": "Evidence B", "url": "https://b.example/context", "content": "more context"},
            ]
        }

    def fake_post_json(url, payload, *, headers, timeout):
        calls["orchestrator_url"] = url
        calls["payload"] = payload
        calls["headers"] = headers
        calls["verification_timeout"] = timeout
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"status_code":"supported","cited_evidence_numbers":[1,1,99],"rationale":"Evidence A supports the material claim."}'
                    }
                }
            ]
        }

    monkeypatch.setattr(verification, "get_json", fake_get_json)
    monkeypatch.setattr(verification, "post_json", fake_post_json)

    result = verifier.verify("Is the relation true?", "The relation exists.")

    assert result.status_code == verification.STATUS_SUPPORTED
    assert result.evidence_urls == ("https://a.example/fact",)
    assert result.rationale == "Evidence A supports the material claim."
    assert "format=json" in str(calls["search_url"])
    assert calls["headers"] == {"authorization": "Bearer secret"}


def test_external_verification_fails_closed_on_search_or_judge_errors(
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
        lambda *_args, **_kwargs: (_ for _ in ()).throw(HttpClientError("down")),
    )
    assert verifier.verify("question", "answer").status_code == verification.STATUS_UNAVAILABLE

    monkeypatch.setattr(
        verification,
        "get_json",
        lambda *_args, **_kwargs: {
            "results": [{"title": "A", "url": "https://a.example", "content": "snippet"}]
        },
    )
    monkeypatch.setattr(
        verification,
        "post_json",
        lambda *_args, **_kwargs: {"choices": [{"message": {"content": "not-json"}}]},
    )
    assert verifier.verify("question", "answer").status_code == verification.STATUS_UNAVAILABLE


def test_no_web_results_means_insufficient_not_refuted(monkeypatch: pytest.MonkeyPatch) -> None:
    verifier = verification.SearxngOrchestratorGlobalAskVerifier(
        "https://search.example",
        "https://orchestrator.example",
        "secret",
    )
    monkeypatch.setattr(verification, "get_json", lambda *_args, **_kwargs: {"results": []})

    result = verifier.verify("question", "answer")

    assert result.status_code == verification.STATUS_INSUFFICIENT
    assert result.evidence_urls == ()
