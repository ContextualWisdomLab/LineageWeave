from __future__ import annotations

import json

import pytest

from lineageweave import claim_verification as cv
from lineageweave.post_chat import ChatSourceDocument


def _public_source(*claims: cv.PublicClaimCandidate) -> cv.GlobalAskSourceDocument:
    return cv.GlobalAskSourceDocument(
        post_id="11111111-1111-1111-1111-111111111111",
        post_title="Public evidence",
        post_body="Acme semantic evidence",
        external_claims=tuple(claims),
    )


def test_only_global_ask_sources_can_contribute_public_claims() -> None:
    ordinary = ChatSourceDocument(
        post_id="22222222-2222-2222-2222-222222222222",
        post_title="Private-capability-free source",
        post_body="Apollo",
        evidence_facts=("project: Apollo | evidence: internal",),
    )
    assert cv.public_claim_candidates([ordinary]) == ()


def test_public_claim_candidates_keep_public_semantic_and_graph_claims_bounded() -> None:
    source = _public_source(
        cv.PublicClaimCandidate(
            "Project Apollo is evidenced by Acme launch",
            "semantic_project",
            ("11111111-1111-1111-1111-111111111111",),
        ),
        cv.PublicClaimCandidate(
            'Team "Apollo" is affiliated with organization "Acme"',
            "knowledge_graph_relation",
            ("11111111-1111-1111-1111-111111111111",),
        ),
    )

    claims = cv.public_claim_candidates([source], maximum_claims=8)

    assert [claim.claim_kind for claim in claims] == [
        "semantic_project",
        "knowledge_graph_relation",
    ]
    assert claims[0].source_post_ids == (source.post_id,)


def test_public_claim_candidates_require_positive_budget_without_heuristic_filtering() -> None:
    source = _public_source(cv.PublicClaimCandidate("Project Apollo", "semantic_project"))
    assert cv.public_claim_candidates([source]) == source.external_claims
    assert cv.public_claim_candidates([source], maximum_claims=0) == ()


def test_public_claim_candidates_filters_citations_before_budget() -> None:
    source = _public_source(
        cv.PublicClaimCandidate("missing citation", "semantic_project"),
        cv.PublicClaimCandidate("uncited", "semantic_project", ("other",)),
        cv.PublicClaimCandidate("cited", "semantic_project", ("post-1",)),
    )
    assert cv.public_claim_candidates(
        [source], maximum_claims=1, allowed_source_post_ids=frozenset({"post-1"})
    ) == (source.external_claims[2],)


def test_public_claim_payload_keeps_internal_post_ids_out_of_public_evidence() -> None:
    result = cv.ClaimVerificationResult(
        claim_text="Project Apollo is public",
        claim_kind="semantic_project",
        status_code=cv.CLAIM_SUPPORTED,
        rationale="The cited public source supports the claim.",
        source_post_ids=("internal-post-id",),
        evidence=(
            cv.ExternalEvidenceDocument(
                "Public evidence",
                "https://example.com/evidence",
                "Published corroboration",
            ),
        ),
    )

    payload = result.to_payload()

    assert "source_post_ids" not in payload
    assert payload["evidence"] == [
        {
            "title": "Public evidence",
            "url": "https://example.com/evidence",
            "snippet": "Published corroboration",
        }
    ]


def test_safe_external_document_rejects_search_local_and_private_hosts() -> None:
    assert cv._safe_external_document({"url": "http://localhost/a", "title": "x"}) is None
    assert cv._safe_external_document({"url": "http://127.0.0.1/a", "title": "x"}) is None
    assert cv._safe_external_document(
        {"url": "https://searx.example/search", "title": "x"},
        search_host="searx.example",
    ) is None
    assert cv._safe_external_document(
        {"url": "https://example.com/search?q=claim", "title": "x"}
    ) is None
    assert cv._safe_external_document({"url": "file:///tmp/x", "title": "x"}) is None
    assert cv._safe_external_document({"url": "https://example.com/a"}) is None

    document = cv._safe_external_document(
        {
            "url": "https://example.com/evidence",
            "title": " Evidence ",
            "content": " Public corroboration ",
        }
    )
    assert document == cv.ExternalEvidenceDocument(
        title="Evidence",
        url="https://example.com/evidence",
        snippet="Public corroboration",
    )


def test_adjudication_without_cited_evidence_downgrades_supported_claim() -> None:
    claim = cv.PublicClaimCandidate("Acme acquired Example", "knowledge_graph_relation")
    result = cv._parse_adjudication(
        json.dumps(
            {
                "status_code": cv.CLAIM_SUPPORTED,
                "rationale": "The evidence supports the claim.",
                "evidence_numbers": [],
            }
        ),
        claim,
        (cv.ExternalEvidenceDocument("Evidence", "https://example.com", "snippet"),),
    )
    assert result.status_code == cv.CLAIM_NOT_ENOUGH_INFORMATION
    assert result.evidence == ()


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "[]",
        '{"status_code":"unknown","rationale":"x","evidence_numbers":[1]}',
    ],
)
def test_adjudication_invalid_payloads_fail_closed(content: str) -> None:
    claim = cv.PublicClaimCandidate("claim", "semantic_project")
    with pytest.raises(ValueError):
        cv._parse_adjudication(content, claim, ())


def test_searxng_orchestrated_client_uses_adaptive_mode_and_selected_evidence(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def fake_get_json(url: str, *, timeout: float, service_peer_name: str):
        calls["search_url"] = url
        calls["search_timeout"] = timeout
        calls["search_peer"] = service_peer_name
        return {
            "results": [
                {"url": "http://127.0.0.1/secret", "title": "private", "content": "no"},
                {
                    "url": "https://example.com/evidence",
                    "title": "Evidence",
                    "content": "Acme publicly describes Apollo as a project.",
                },
            ]
        }

    def fake_post_json(url: str, payload: dict, *, headers: dict, timeout: float):
        calls["orchestrator_url"] = url
        calls["payload"] = payload
        calls["headers"] = headers
        calls["adjudication_timeout"] = timeout
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "status_code": cv.CLAIM_SUPPORTED,
                                "rationale": "Public evidence corroborates the claim.",
                                "evidence_numbers": [1],
                            }
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(cv, "get_json", fake_get_json)
    monkeypatch.setattr(cv, "post_json", fake_post_json)
    client = cv.SearxngOrchestratedClaimVerificationClient(
        "https://search.example",
        "https://orchestrator.example",
        "secret",
    )
    claim = cv.PublicClaimCandidate(
        "project: Apollo | evidence: Acme launch",
        "semantic_project",
        ("11111111-1111-1111-1111-111111111111",),
    )

    result = client.verify(claim)

    assert result.status_code == cv.CLAIM_SUPPORTED
    assert [item.url for item in result.evidence] == ["https://example.com/evidence"]
    assert calls["payload"]["mode"] == "auto"
    assert calls["payload"]["reasoning_effort"] == "auto"
    assert calls["headers"] == {"authorization": "Bearer secret"}
    assert calls["search_peer"] == "searxng"
    assert "format=json" in calls["search_url"]


def test_searxng_orchestrated_client_returns_nei_when_search_has_no_usable_evidence(monkeypatch) -> None:
    monkeypatch.setattr(
        cv,
        "get_json",
        lambda url, *, timeout, service_peer_name: {
            "results": [{"url": "http://127.0.0.1/a", "title": "x"}]
        },
    )
    client = cv.SearxngOrchestratedClaimVerificationClient(
        "https://search.example",
        "https://orchestrator.example",
        "secret",
    )
    result = client.verify(cv.PublicClaimCandidate("claim", "semantic_project"))
    assert result.status_code == cv.CLAIM_NOT_ENOUGH_INFORMATION
    assert result.evidence == ()


def test_searxng_orchestrated_client_rejects_an_empty_adjudication(monkeypatch) -> None:
    monkeypatch.setattr(
        cv,
        "get_json",
        lambda url, *, timeout, service_peer_name: {
            "results": [{"url": "https://example.com/a", "title": "Evidence"}]
        },
    )
    monkeypatch.setattr(
        cv,
        "post_json",
        lambda url, payload, *, headers, timeout: {"choices": []},
    )
    client = cv.SearxngOrchestratedClaimVerificationClient(
        "https://search.example", "https://orchestrator.example", "secret"
    )

    with pytest.raises(ValueError, match="no choice"):
        client.verify(cv.PublicClaimCandidate("claim", "semantic_project"))


def test_client_configuration_fails_closed() -> None:
    with pytest.raises(ValueError):
        cv.SearxngOrchestratedClaimVerificationClient(
            "file:///search", "https://orchestrator.example", "secret"
        )
    with pytest.raises(ValueError):
        cv.SearxngOrchestratedClaimVerificationClient(
            "https://search.example", "file:///orchestrator", "secret"
        )
    with pytest.raises(ValueError):
        cv.SearxngOrchestratedClaimVerificationClient(
            "https://search.example",
            "https://orchestrator.example",
            "secret",
            maximum_results=0,
        )
    with pytest.raises(ValueError):
        cv.SearxngOrchestratedClaimVerificationClient(
            "https://user:secret@search.example",
            "https://orchestrator.example",
            "secret",
        )
    with pytest.raises(ValueError):
        cv.SearxngOrchestratedClaimVerificationClient(
            "https://search.example",
            "https://orchestrator.example",
            "secret",
            maximum_results=6,
        )
    with pytest.raises(ValueError):
        cv.SearxngOrchestratedClaimVerificationClient(
            "https://search.example",
            "https://orchestrator.example",
            "secret",
            search_timeout=float("nan"),
        )
