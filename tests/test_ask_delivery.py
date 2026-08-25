"""Checks for the transport-neutral Ask delivery contract."""

from lineageweave.ask_delivery import build_ask_delivery


def test_delivery_links_only_cited_evidence_without_keyword_classification() -> None:
    """Reports and alerts retain citation identity and safe resource links."""
    delivery = build_ask_delivery(
        "A prior response is documented.",
        ({"post_id": "post/a", "post_title": "Response record"},),
        ({"post_id": "post/a", "facts": [{"kind": "source_field", "text": "Recorded"}]},),
    )

    assert delivery == {
        "contract_version": "1.0",
        "report": {
            "media_type": "text/markdown",
            "body": "A prior response is documented.",
            "source_documents": [
                {
                    "post_id": "post/a",
                    "title": "Response record",
                    "api_path": "/api/posts/post%2Fa",
                    "resource_uri": "lineageweave://posts/post%2Fa",
                    "evidence_facts": [{"kind": "source_field", "text": "Recorded"}],
                }
            ],
        },
        "alert": {
            "trigger_code": "cited_evidence_changed",
            "delivery_status_code": "not_subscribed",
            "eligible": True,
            "watched_resource_uris": ["lineageweave://posts/post%2Fa"],
        },
    }


def test_delivery_without_citations_cannot_offer_an_evidence_alert() -> None:
    """An unsupported answer never becomes a fabricated alert target."""
    delivery = build_ask_delivery("", (), ())

    assert delivery["report"]["source_documents"] == []
    assert delivery["alert"]["eligible"] is False
    assert delivery["alert"]["watched_resource_uris"] == []
