"""Unit tests for ADR 0224 public-claim envelopes. Synthetic fixtures only."""

from __future__ import annotations

import pytest

from lineageweave.public_claim_verification import (
    KIND_ORGANIZATION_PRESENCE,
    KIND_PUBLIC_EVENT,
    NullPublicClaimSearchClient,
    PublicClaimEnvelope,
    STATUS_NOT_ENOUGH_INFORMATION,
    STATUS_SUPPORTED,
    STATUS_UNAVAILABLE,
    SearxngPublicClaimSearchClient,
    cited_post_ids_exclude_external,
    classify_public_claim,
    envelope_from_authorized_row,
    public_evidence_url,
    verify_public_claims,
)


def _envelope(**overrides: object) -> PublicClaimEnvelope:
    payload = dict(
        public_claim_envelope_id="env-1",
        source_post_id="post-demo-public",
        source_post_title="Demo public post",
        claim_kind_code=KIND_ORGANIZATION_PRESENCE,
        subject_label="Northridge Grid",
        claim_text="Northridge Grid is a power utility named on the Demo public post.",
        truth_status_code="truth_observed",
        event_occurred_at="2026-01-10T12:00:00+00:00",
        egress_eligible=True,
        visibility_code="public",
    )
    payload.update(overrides)
    return PublicClaimEnvelope(**payload)  # type: ignore[arg-type]


def test_private_or_ineligible_rows_are_dropped() -> None:
    assert envelope_from_authorized_row(
        {
            "public_claim_envelope_id": "env-1",
            "source_post_id": "post-private",
            "source_post_title": "Demo private post",
            "claim_kind_code": KIND_ORGANIZATION_PRESENCE,
            "subject_label": "Northridge Grid",
            "claim_text": "secret",
            "truth_status_code": "truth_observed",
            "event_occurred_at": None,
            "egress_eligible": True,
            "visibility_code": "private",
        }
    ) is None
    assert envelope_from_authorized_row(
        {
            "public_claim_envelope_id": "env-2",
            "source_post_id": "post-demo-public",
            "source_post_title": "Demo public post",
            "claim_kind_code": "keyman",
            "subject_label": "Ada West",
            "claim_text": "Ada West is a Keyman",
            "truth_status_code": "truth_observed",
            "event_occurred_at": None,
            "egress_eligible": True,
            "visibility_code": "public",
        }
    ) is None
    assert envelope_from_authorized_row(
        {
            "public_claim_envelope_id": "env-3",
            "source_post_id": "post-demo-public",
            "source_post_title": "Demo public post",
            "claim_kind_code": KIND_ORGANIZATION_PRESENCE,
            "subject_label": "Northridge Grid",
            "claim_text": "Northridge Grid is a power utility.",
            "truth_status_code": "truth_observed",
            "event_occurred_at": None,
            "egress_eligible": False,
            "visibility_code": "public",
        }
    ) is None


def test_authorized_public_row_becomes_an_envelope() -> None:
    envelope = envelope_from_authorized_row(
        {
            "public_claim_envelope_id": "env-1",
            "source_post_id": "post-demo-public",
            "source_post_title": "Demo public post",
            "claim_kind_code": KIND_ORGANIZATION_PRESENCE,
            "subject_label": "Northridge Grid",
            "claim_text": "Northridge Grid is a power utility.",
            "truth_status_code": "truth_observed",
            "event_occurred_at": None,
            "egress_eligible": True,
            "visibility_code": "public",
        }
    )
    assert envelope is not None
    assert envelope.source_post_title == "Demo public post"


def test_public_evidence_url_rejects_search_localhost_and_private_hosts() -> None:
    assert public_evidence_url("https://www.google.com/search?q=x") is None
    assert public_evidence_url("https://localhost/secret") is None
    assert public_evidence_url("http://127.0.0.1/x") is None
    assert public_evidence_url("http://10.0.0.8/intranet") is None
    assert public_evidence_url("http://192.168.1.4/x") is None
    assert public_evidence_url("file:///etc/passwd") is None
    assert public_evidence_url("https://user:pass@example.test/x") is None
    assert public_evidence_url("https://northridgegrid.example/about") == (
        "https://northridgegrid.example/about"
    )


def test_empty_authorized_set_is_unavailable_and_does_not_search() -> None:
    class _Exploding:
        available = True

        def search_urls(self, claim_text: str, *, limit: int = 5) -> tuple[str, ...]:
            raise AssertionError("must not search without an authorized envelope")

    payload = verify_public_claims((), _Exploding())
    assert payload["status_code"] == STATUS_UNAVAILABLE
    assert payload["claims"] == []
    assert "no egress-eligible" in payload["next_action"]


def test_missing_search_channel_is_unavailable_not_not_enough_information() -> None:
    payload = verify_public_claims((_envelope(),), NullPublicClaimSearchClient())
    assert payload["status_code"] == STATUS_UNAVAILABLE
    assert payload["claims"][0]["external_evidence_urls"] == []
    assert "search service" in payload["next_action"]


def test_no_usable_urls_are_not_enough_information() -> None:
    class _Empty:
        available = True

        def search_urls(self, claim_text: str, *, limit: int = 5) -> tuple[str, ...]:
            assert "Northridge Grid" in claim_text
            return ()

    payload = verify_public_claims((_envelope(),), _Empty())
    assert payload["status_code"] == STATUS_NOT_ENOUGH_INFORMATION
    assert payload["claims"][0]["status_code"] == STATUS_NOT_ENOUGH_INFORMATION


def test_organization_presence_with_distinctive_url_is_supported() -> None:
    url = "https://northridgegrid.example/about"
    verdict = classify_public_claim(
        _envelope(),
        (url,),
        search_available=True,
    )
    assert verdict.status_code == STATUS_SUPPORTED
    assert verdict.external_evidence_urls == (url,)
    assert "supports" in verdict.next_action


def test_other_kinds_stay_unavailable_even_with_urls() -> None:
    verdict = classify_public_claim(
        _envelope(claim_kind_code=KIND_PUBLIC_EVENT),
        ("https://events.example/northridge",),
        search_available=True,
    )
    assert verdict.status_code == STATUS_UNAVAILABLE
    assert verdict.external_evidence_urls == ("https://events.example/northridge",)


def test_external_urls_cannot_become_cited_post_ids() -> None:
    verification = {
        "claims": [
            {
                "external_evidence_urls": ["https://northridgegrid.example/about"],
            }
        ]
    }
    cited_post_ids_exclude_external(["post-demo-public"], verification)
    with pytest.raises(ValueError, match="cited_post_ids"):
        cited_post_ids_exclude_external(
            ["https://northridgegrid.example/about"], verification
        )


def test_searxng_client_filters_private_and_search_hits(monkeypatch) -> None:
    def _fake_get_json(_url: str, **_kwargs: object) -> dict[str, object]:
        return {
            "results": [
                {"url": "https://www.bing.com/search?q=Northridge"},
                {"url": "http://127.0.0.1/x"},
                None,
                {"url": "https://northridgegrid.example/about"},
                {"url": "https://northridgegrid.example/about"},
            ]
        }

    monkeypatch.setattr(
        "lineageweave.public_claim_verification.get_json", _fake_get_json
    )
    client = SearxngPublicClaimSearchClient("http://searxng:8080")
    assert client.search_urls(
        "Northridge Grid is a power utility named on the Demo public post."
    ) == ("https://northridgegrid.example/about",)


def test_searxng_client_refuses_non_http_scheme() -> None:
    with pytest.raises(ValueError, match="unsupported Searxng base URL scheme"):
        SearxngPublicClaimSearchClient("file:///etc/passwd")


def test_searxng_malformed_results_are_empty(monkeypatch) -> None:
    monkeypatch.setattr(
        "lineageweave.public_claim_verification.get_json",
        lambda *_args, **_kwargs: {"results": {"not": "a list"}},
    )
    client = SearxngPublicClaimSearchClient("http://searxng")
    assert client.search_urls("Northridge Grid is a power utility.") == ()


def test_blank_row_fields_are_dropped() -> None:
    assert envelope_from_authorized_row(
        {
            "public_claim_envelope_id": "env-1",
            "source_post_id": "post-demo-public",
            "source_post_title": "Demo public post",
            "claim_kind_code": KIND_ORGANIZATION_PRESENCE,
            "subject_label": "   ",
            "claim_text": "Northridge Grid is a power utility.",
            "truth_status_code": "truth_observed",
            "event_occurred_at": None,
            "egress_eligible": True,
            "visibility_code": "public",
        }
    ) is None


def test_unrelated_url_is_not_enough_information_for_organization_presence() -> None:
    verdict = classify_public_claim(
        _envelope(),
        ("https://unrelated.example/generic",),
        search_available=True,
    )
    assert verdict.status_code == STATUS_NOT_ENOUGH_INFORMATION


def test_blank_claim_text_does_not_search(monkeypatch) -> None:
    def _fake_get_json(_url: str, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("blank claim must not hit SearXNG")

    monkeypatch.setattr(
        "lineageweave.public_claim_verification.get_json", _fake_get_json
    )
    client = SearxngPublicClaimSearchClient("https://searxng.example")
    assert client.search_urls("   ") == ()
