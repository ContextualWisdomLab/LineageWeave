from __future__ import annotations

import json

import pytest

from lineageweave import claim_verification as cv
from lineageweave.post_chat import ChatSourceDocument


def _public_source(*facts: str) -> cv.GlobalAskSourceDocument:
    return cv.GlobalAskSourceDocument(
        post_id="11111111-1111-1111-1111-111111111111",
        post_title="Public evidence",
        post_body="Acme semantic evidence",
        external_claim_facts=tuple(facts),
    )


def test_only_global_ask_sources_can_contribute_public_claims() -> None:
    ordinary = ChatSourceDocument(
        post_id="22222222-2222-2222-2222-222222222222",
        post_title="Private-capability-free source",
        post_body="Apollo",
        evidence_facts=("project: Apollo | evidence: internal",),
    )
    assert cv.public_claim_candidates([ordinary], "Apollo") == ()


def test_public_claim_candidates_keep_public_semantic_and_graph_claims_bounded() -> None:
    source = _public_source(
        "project: Apollo | evidence: Acme launch | ontology_iri: https://example.test/ontology#Project | extraction_method: llm | confidence: 0.90 [provenance=post_project_mention]",
        'node_team "Apollo Team" --edge_team_affiliation (https://example.test/ontology#teamAffiliation)--> node_organization "Acme" [evidence_post_id=11111111-1111-1111-1111-111111111111]',
        'node_person "Alice" --edge_affiliation--> node_organization "Acme" [evidence_post_id=11111111-1111-1111-1111-111111111111]',
    )

    claims = cv.public_claim_candidates([source], "Is Apollo at Acme?", maximum_claims=8)

    assert [claim.claim_kind for claim in claims] == [
        "knowledge_graph_relation",
        "semantic_project",
    ]
    assert all("node_person" not in claim.claim_text for claim in claims)
    assert claims[0].source_post_ids == (source.post_id,)
    assert "extraction_method" not in claims[1].claim_text
    assert "confidence" not in claims[1].claim_text


def test_public_claim_candidates_require_query_overlap_and_positive_budget() -> None:
    source = _public_source("project: Apollo | evidence: Acme launch")
    assert cv.public_claim_candidates([source], "Zephyr") == ()
    assert cv.public_claim_candidates([source], "Apollo", maximum_claims=0) == ()


def test_safe_external_document_rejects_search_local_and_private_hosts() -> None:
    assert cv._safe_external_document({"url": "http://localhost/a", "title": "x"}) is None
    assert cv._safe_external_document({"url": "http://127.0.0.1/a", "title": "x"}) is None
    assert cv._safe_external_document({"url": "https://searx.example/search", "title": "x"}) is None
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


def test_searxng_orchestrated_client_uses_verify_mode_and_selected_evidence(monkeypatch) -> None:
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
    assert calls["payload"]["mode"] == "verify"
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


@pytest.mark.parametrize(
    "response",
    (
        {},
        {"choices": []},
        {"choices": [None]},
        {"choices": [{}]},
        {"choices": [{"message": {"content": None}}]},
    ),
)
def test_searxng_orchestrated_client_rejects_malformed_adjudication_envelopes(
    monkeypatch, response: dict
) -> None:
    """Malformed provider envelopes fail closed through the public client contract."""

    monkeypatch.setattr(
        cv,
        "get_json",
        lambda url, *, timeout, service_peer_name: {
            "results": [{"url": "https://example.com/evidence", "title": "Evidence"}]
        },
    )
    monkeypatch.setattr(cv, "post_json", lambda *args, **kwargs: response)
    client = cv.SearxngOrchestratedClaimVerificationClient(
        "https://search.example",
        "https://orchestrator.example",
        "secret",
    )

    with pytest.raises(ValueError):
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


def test_claim_kind_classifies_project_ontology_and_plain_facts() -> None:
    """The fact-kind classifier maps source conventions to claim kinds."""
    assert cv._claim_kind("project: Apollo | evidence: launch") == "semantic_project"
    assert cv._claim_kind("ontology_iri: https://example.test/ontology#Project") == (
        "ontology_reference"
    )
    assert cv._claim_kind("node_team A --edge_affiliation--> node_organization B") == (
        "knowledge_graph_relation"
    )
    assert cv._claim_kind("plain customer-safe sentence") is None


def test_safe_external_document_rejects_malformed_and_non_http_urls() -> None:
    """Only well-formed http(s), reachable documents are admissible."""
    assert cv._safe_external_document("not-a-dict") is None
    assert cv._safe_external_document({}) is None
    assert cv._safe_external_document({"url": "  "}) is None
    assert cv._safe_external_document({"url": "file:///etc/passwd"}) is None
    assert cv._safe_external_document({"url": "javascript:alert(1)"}) is None
    assert cv._safe_external_document({"url": ""}) is None


def test_null_claim_verification_client_raises_unavailable_runtime_error() -> None:
    """An unavailable client signals the missing capability contractually."""
    client = cv.NullClaimVerificationClient()
    assert client.available is False
    with pytest.raises(RuntimeError, match="not configured"):
        client.verify(_public_claim("Acme launch?"))


@pytest.mark.parametrize("maximum_results", [1, 2])
def test_search_bounds_results_to_maximum(monkeypatch, maximum_results: int) -> None:
    """At most ``maximum_results`` unique admissible documents are kept."""
    from lineageweave import claim_verification as cv_mod

    def fake_search(_url, *, timeout, service_peer_name="searxng"):  # noqa: ANN001
        return {
            "results": [
                {"url": f"https://example.test/doc/{index}", "title": f"Doc {index}"}
                for index in range(6)
            ]
        }

    monkeypatch.setattr(cv_mod, "get_json", fake_search)
    client = cv.SearxngOrchestratedClaimVerificationClient(
        "https://searxng.test",
        "https://orchestrator.test",
        "synthetic-key",
        maximum_results=maximum_results,
    )
    documents = client._search(_public_claim("Acme launch?"))
    assert len(documents) == maximum_results


def test_claim_result_to_payload_serializes_without_mixing_identifiers() -> None:
    """The payload keeps external URLs separate from internal post ids."""
    result = cv.ClaimVerificationResult(
        claim_text="Is Apollo at Acme?",
        claim_kind="knowledge_graph_relation",
        status_code=cv.CLAIM_SUPPORTED,
        rationale="Public search corroborates",
        source_post_ids=("11111111-1111-1111-1111-111111111111",),
        evidence=(
            cv.ExternalEvidenceDocument("Acme", "https://example.test/a", "snippet"),
        ),
    )
    payload = result.to_payload()
    assert payload["claim_text"] == "Is Apollo at Acme?"
    assert payload["claim_kind"] == "knowledge_graph_relation"
    assert payload["status_code"] == cv.CLAIM_SUPPORTED
    assert payload["source_post_ids"] == ["11111111-1111-1111-1111-111111111111"]
    assert payload["evidence"][0]["url"] == "https://example.test/a"


def test_public_claim_candidates_skip_overlong_facts() -> None:
    """Facts whose cleaned text exceeds 800 characters never become claims."""
    long_fact = "project: " + ("x" * 900) + " | evidence: short"
    source = cv.GlobalAskSourceDocument(
        post_id="11111111-1111-1111-1111-111111111111",
        post_title="Public evidence",
        post_body="Long fact body",
        external_claim_facts=(long_fact,),
    )
    assert cv.public_claim_candidates([source], "Long", maximum_claims=4) == ()


def test_ontology_lookup_codes_reject_zero_budget_and_blank_question() -> None:
    """A zero budget or a blank question nominates nothing."""
    assert cv.ontology_lookup_codes_for_question("anything", maximum_codes=0) == ()
    assert cv.ontology_lookup_codes_for_question("   ", maximum_codes=8) == ()


def test_ontology_lookup_codes_match_an_explicit_ontology_iri() -> None:
    """A question naming an ontology IRI nominates that entity's lookup code."""
    codes = cv.ontology_lookup_codes_for_question(
        "https://contextualwisdomlab.github.io/LineageWeave/ontology#post",
        maximum_codes=16,
    )
    assert "node_post" in codes


def test_ontology_lookup_codes_deduplicate_like_matches() -> None:
    """Repeated candidates collapse through the final deduplication."""
    codes = cv.ontology_lookup_codes_for_question(
        "post post post post project project",
        maximum_codes=16,
    )
    assert len(codes) == len(set(codes))


def test_search_non_list_results_return_empty() -> None:
    """A malformed search body with no results list yields no evidence."""
    from lineageweave import claim_verification as cv_mod

    def fake_search(_url, *, timeout, service_peer_name="searxng"):  # noqa: ANN001
        return {"results": "not-a-list"}

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(cv_mod, "get_json", fake_search)
    client = cv.SearxngOrchestratedClaimVerificationClient(
        "https://searxng.test",
        "https://orchestrator.test",
        "synthetic-key",
        maximum_results=5,
    )
    assert client._search(_public_claim("Acme launch?")) == ()
    monkeypatch.undo()


def test_search_deduplicates_repeated_admissible_documents() -> None:
    """Duplicate URLs collapse before the maximum-result budget applies."""
    from lineageweave import claim_verification as cv_mod

    def fake_search(_url, *, timeout, service_peer_name="searxng"):  # noqa: ANN001
        return {
            "results": [
                {"url": "https://example.test/a", "title": "A"},
                {"url": "https://example.test/a", "title": "A-again"},
                {"url": "https://example.test/b", "title": "B"},
            ]
        }

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(cv_mod, "get_json", fake_search)
    client = cv.SearxngOrchestratedClaimVerificationClient(
        "https://searxng.test",
        "https://orchestrator.test",
        "synthetic-key",
        maximum_results=5,
    )
    documents = client._search(_public_claim("Acme launch?"))
    assert {document.url for document in documents} == {
        "https://example.test/a",
        "https://example.test/b",
    }
    monkeypatch.undo()


def _public_claim(text: str) -> cv.PublicClaimCandidate:
    """One minimal PublicClaimCandidate for client-contract tests."""
    return cv.PublicClaimCandidate(
        claim_text=text,
        claim_kind="knowledge_graph_relation",
        source_post_ids=("11111111-1111-1111-1111-111111111111",),
    )
