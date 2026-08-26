"""Post-scoped source-reference research library tests."""

from __future__ import annotations

import json

import pytest

from lineageweave.public_resource_retrieval import PublicResource, PublicTargetRejected
from lineageweave.source_reference_research import (
    JUDGMENT_NOT_ENOUGH_INFORMATION,
    JUDGMENT_SUPPORTED,
    JUDGMENT_UNAVAILABLE,
    LEAD_IMAGE_REGION,
    LEAD_SEMANTIC_UNIT,
    NEXT_ACTION,
    NullSourceResearchClient,
    SearxngOrchestratedSourceResearchClient,
    SourceResearchLead,
    parse_research_adjudication,
    select_source_research_leads,
    unavailable_citation,
)


def _unit_lead() -> SourceResearchLead:
    return SourceResearchLead(
        lead_kind_code=LEAD_SEMANTIC_UNIT,
        lead_source_unit_id="11111111-1111-1111-1111-111111111111",
        lead_excerpt_text="Demo Corp delayed the Apollo transformer shipment.",
    )


def test_select_source_research_leads_skips_image_units_and_empty_text() -> None:
    units = [
        {
            "post_content_unit_id": "unit-image",
            "unit_kind_code": "image",
            "unit_text": "diagram",
        },
        {
            "post_content_unit_id": "unit-empty",
            "unit_kind_code": "plain_text",
            "unit_text": "  ",
        },
        {
            "post_content_unit_id": "unit-ok",
            "unit_kind_code": "plain_text",
            "unit_text": "Apollo transformer delay",
        },
    ]
    regions = [
        {
            "post_content_image_region_id": "region-empty",
            "caption": "",
            "extracted_text": None,
        },
        {
            "post_content_image_region_id": "region-ok",
            "caption": "Nameplate",
            "extracted_text": "Apollo 500 kVA",
        },
    ]
    leads = select_source_research_leads(units, regions, maximum_leads=3)
    assert [lead.lead_kind_code for lead in leads] == [
        LEAD_SEMANTIC_UNIT,
        LEAD_IMAGE_REGION,
    ]
    assert leads[0].lead_source_unit_id == "unit-ok"
    assert leads[1].lead_image_region_id == "region-ok"
    assert "Apollo 500 kVA" in leads[1].lead_excerpt_text


def test_select_source_research_leads_honors_zero_budget() -> None:
    assert select_source_research_leads(
        [{"post_content_unit_id": "unit-ok", "unit_kind_code": "plain_text", "unit_text": "x"}],
        [],
        maximum_leads=0,
    ) == ()


def test_null_client_is_unavailable() -> None:
    client = NullSourceResearchClient()
    assert client.available is False
    with pytest.raises(RuntimeError):
        client.research(_unit_lead())


def test_supported_without_cited_resource_downgrades() -> None:
    resource = PublicResource(
        url="https://example.com/apollo",
        title="Apollo",
        excerpt_text="Apollo is a public project.",
        media_type="text/html",
    )
    result = parse_research_adjudication(
        json.dumps(
            {
                "status_code": JUDGMENT_SUPPORTED,
                "rationale": "I already knew this.",
                "cited_resource": False,
            }
        ),
        _unit_lead(),
        resource,
    )
    assert result.judgment_code == JUDGMENT_NOT_ENOUGH_INFORMATION
    assert result.evidence_url is None
    assert result.next_action_text == NEXT_ACTION


def test_supported_with_cited_resource_keeps_url() -> None:
    resource = PublicResource(
        url="https://example.com/apollo",
        title="Apollo",
        excerpt_text="Apollo is a public project.",
        media_type="text/html",
    )
    result = parse_research_adjudication(
        json.dumps(
            {
                "status_code": JUDGMENT_SUPPORTED,
                "rationale": "The retrieved page describes the delay.",
                "cited_resource": True,
            }
        ),
        _unit_lead(),
        resource,
    )
    assert result.judgment_code == JUDGMENT_SUPPORTED
    assert result.evidence_url == "https://example.com/apollo"
    assert result.evidence_title_text == "Apollo"


@pytest.mark.parametrize("content", ["not json", "[]", '{"status_code":"claim_supported"}'])
def test_adjudication_invalid_payloads_fail_closed(content: str) -> None:
    with pytest.raises(ValueError):
        parse_research_adjudication(content, _unit_lead(), None)


def test_unavailable_citation_does_not_invent_a_negative_judgment() -> None:
    citation = unavailable_citation(_unit_lead(), "search missing")
    assert citation.judgment_code == JUDGMENT_UNAVAILABLE
    assert citation.evidence_url is None


def test_orchestrated_client_searches_retrieves_and_verifies(monkeypatch) -> None:
    calls: dict[str, object] = {}
    lead = _unit_lead()

    def fake_get_json(url: str, *, timeout: float, service_peer_name: str):
        calls["search_url"] = url
        calls["search_peer"] = service_peer_name
        return {
            "results": [
                {"url": "http://127.0.0.1/secret", "title": "private"},
                {"url": "https://example.com/apollo", "title": "Apollo"},
            ]
        }

    def fake_fetch(url: str, *, timeout: float):
        calls["fetched_url"] = url
        calls["fetch_timeout"] = timeout
        assert url == "https://example.com/apollo"
        return PublicResource(
            url=url,
            title="Apollo evidence",
            excerpt_text="Demo Corp delayed the Apollo transformer shipment.",
            media_type="text/html",
        )

    def fake_post_json(url: str, payload: dict, *, headers: dict, timeout: float):
        calls["orchestrator_url"] = url
        calls["payload"] = payload
        calls["headers"] = headers
        assert payload["mode"] == "verify"
        assert payload["reasoning_effort"] == "auto"
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "status_code": JUDGMENT_SUPPORTED,
                                "rationale": "The public page matches the source unit.",
                                "cited_resource": True,
                            }
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(
        "lineageweave.source_reference_research.get_json",
        fake_get_json,
    )
    monkeypatch.setattr(
        "lineageweave.source_reference_research.post_json",
        fake_post_json,
    )
    client = SearxngOrchestratedSourceResearchClient(
        "https://search.example",
        "https://orchestrator.example",
        "test-key",
        fetch_resource=fake_fetch,
    )
    result = client.research(lead)
    assert result.judgment_code == JUDGMENT_SUPPORTED
    assert result.evidence_url == "https://example.com/apollo"
    assert "q=Demo%20Corp" in str(calls["search_url"])
    assert calls["search_peer"] == "searxng"
    assert calls["payload"]["mode"] == "verify"


def test_orchestrated_client_skips_rejected_retrievals(monkeypatch) -> None:
    def fake_get_json(url: str, *, timeout: float, service_peer_name: str):
        return {"results": [{"url": "https://example.com/blocked"}]}

    def fake_fetch(url: str, *, timeout: float):
        raise PublicTargetRejected("redirects are not followed")

    monkeypatch.setattr(
        "lineageweave.source_reference_research.get_json",
        fake_get_json,
    )
    client = SearxngOrchestratedSourceResearchClient(
        "https://search.example",
        "https://orchestrator.example",
        "test-key",
        fetch_resource=fake_fetch,
    )
    result = client.research(_unit_lead())
    assert result.judgment_code == JUDGMENT_UNAVAILABLE
    assert result.evidence_url is None
