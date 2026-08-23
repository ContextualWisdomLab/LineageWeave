"""Security regressions for ADR 0133 source-reference research."""

from __future__ import annotations

import json

import pytest

from lineageweave.source_research import (
    ContextualOrchestratorSourceResearchJudge,
    ResearchLead,
    RetrievedPassage,
    SearxngSourceResearchClient,
)


def test_search_drops_non_public_result_instead_of_persisting_its_snippet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "lineageweave.source_research.get_json",
        lambda *_args, **_kwargs: {
            "results": [
                {
                    "url": "http://127.0.0.1/internal",
                    "title": "Synthetic private result",
                    "content": "Synthetic snippet must not become evidence.",
                }
            ]
        },
    )
    monkeypatch.setattr(
        "lineageweave.source_research.crawl_public_page",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("non-public network target")
        ),
    )

    assert (
        SearxngSourceResearchClient("https://search.test").retrieve(
            ResearchLead("source_reference_patent", "synthetic patent", "evidence")
        )
        == []
    )


def test_url_lead_searches_the_extracted_url_not_surrounding_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested_urls: list[str] = []

    def fake_get_json(url: str, **_kwargs: object) -> dict[str, list[object]]:
        requested_urls.append(url)
        return {"results": []}

    monkeypatch.setattr("lineageweave.source_research.get_json", fake_get_json)
    SearxngSourceResearchClient("https://search.test").retrieve(
        ResearchLead(
            "source_reference_url",
            "https://example.test/reference",
            "Synthetic surrounding prose https://example.test/reference",
        )
    )

    assert "q=https%3A%2F%2Fexample.test%2Freference&" in requested_urls[0]


@pytest.mark.parametrize("status_code", ["supported", "refuted"])
def test_conclusive_judgment_requires_a_citation(
    monkeypatch: pytest.MonkeyPatch, status_code: str
) -> None:
    monkeypatch.setattr(
        "lineageweave.source_research.post_json",
        lambda *_args, **_kwargs: {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "status_code": status_code,
                                "sharing_actor_name": None,
                                "rationale": "Synthetic unsupported conclusion.",
                                "cited_urls": [],
                            }
                        )
                    }
                }
            ]
        },
    )

    with pytest.raises(ValueError, match="without a citation"):
        ContextualOrchestratorSourceResearchJudge(
            "https://orchestrator.test", "synthetic-key"
        ).judge(
            ResearchLead("source_reference_patent", "synthetic", "synthetic"),
            [RetrievedPassage("https://evidence.test/item", "Evidence", "Body")],
        )
