import lineageweave.relation_verification as relation_verification


def test_searxng_verification_drops_malformed_or_search_page_results(monkeypatch) -> None:
    responses = iter(
        [
            {"results": {}},
            {
                "results": [
                    None,
                    {},
                    {"url": "https://www.google.example/search?q=Aurora"},
                    {"url": "https://unrelated.example/page", "content": "generic result"},
                ]
            },
        ]
    )
    monkeypatch.setattr(relation_verification, "get_json", lambda *_args, **_kwargs: next(responses))
    client = relation_verification.SearxngRelationVerificationClient("http://searxng")

    assert client.verify("Aurora Grid Power", "customer").status_code == relation_verification.STATUS_UNCORROBORATED
    assert client.verify("Aurora Grid Power", "customer").status_code == relation_verification.STATUS_UNCORROBORATED


def test_corroborating_evidence_requires_distinctive_org_token() -> None:
    assert relation_verification.corroborating_evidence_url("Corp Ltd", {"url": "https://corp.example"}) is None
    assert relation_verification.corroborating_evidence_url("Aurora Grid Power", {"url": ""}) is None
    assert (
        relation_verification.corroborating_evidence_url(
            "Aurora Grid Power",
            {"url": "https://aurora.example/about", "content": "Aurora Grid Power"},
        )
        == "https://aurora.example/about"
    )
