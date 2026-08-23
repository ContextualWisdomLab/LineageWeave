"""Synthetic contract tests for ADR 0133 source-reference research."""

from __future__ import annotations

import asyncio
import json
import socket
from contextlib import asynccontextmanager

import pytest

from backend.app.source_research_ingestion import (
    decode_research_retrievals,
    research_post_sources,
)
from lineageweave.http_client import HttpClientError
from lineageweave.source_research import (
    ContextualOrchestratorSourceResearchJudge,
    NullSourceResearchJudge,
    ResearchJudgment,
    ResearchLead,
    RetrievedPassage,
    SearxngSourceResearchClient,
    _public_host,
    crawl_public_page,
    discover_research_leads,
)


def test_discovers_explicit_url_and_patent_leads_without_binding_an_actor() -> None:
    leads = discover_research_leads(
        [
            "Synthetic team shared https://example.test/reference.",
            "A synthetic patent application describes the mechanism.",
        ]
    )

    assert [(lead.lead_type_code, lead.query_text) for lead in leads] == [
        ("source_reference_url", "https://example.test/reference"),
        (
            "source_reference_patent",
            (
                "Synthetic team shared https://example.test/reference. "
                "A synthetic patent application describes the mechanism."
            ),
        ),
    ]
    assert all(not hasattr(lead, "sharing_actor_name") for lead in leads)


def test_discovered_leads_preserve_content_unit_and_image_region_identity() -> None:
    leads = discover_research_leads(
        [
            (
                "Synthetic source https://example.test/reference",
                "content-unit-1",
                None,
            ),
            (
                "Synthetic patent evidence",
                None,
                "image-region-1",
            ),
        ]
    )

    assert [
        (lead.source_content_unit_id, lead.source_image_region_id) for lead in leads
    ] == [
        ("content-unit-1", None),
        (None, "image-region-1"),
    ]


def test_lead_discovery_drops_blank_and_duplicate_references_per_source() -> None:
    leads = discover_research_leads(
        [
            "  ",
            "https://example.test/reference https://example.test/reference",
        ]
    )

    assert [lead.query_text for lead in leads] == ["https://example.test/reference"]


def test_lead_discovery_deduplicates_equal_patent_contexts() -> None:
    leads = discover_research_leads(["Synthetic patent"] * 3)

    assert [lead.query_text for lead in leads] == [
        "Synthetic patent Synthetic patent",
        "Synthetic patent Synthetic patent Synthetic patent",
    ]


@pytest.mark.parametrize(
    ("addresses", "expected"),
    [
        (["93.184.216.34"], True),
        (["127.0.0.1"], False),
        ([], False),
    ],
)
def test_public_host_requires_every_resolved_address_to_be_global(
    monkeypatch: pytest.MonkeyPatch,
    addresses: list[str],
    expected: bool,
) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args: [
            (None, None, None, None, (address, 0)) for address in addresses
        ],
    )

    assert _public_host("example.test") is expected


def test_public_host_treats_dns_failure_as_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_resolution(*_args: object) -> object:
        raise socket.gaierror

    monkeypatch.setattr(socket, "getaddrinfo", fail_resolution)
    assert _public_host("unresolvable.test") is False


def test_crawl_returns_visible_text_and_drops_hidden_markup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("lineageweave.source_research._public_host", lambda _host: True)
    monkeypatch.setattr(
        "lineageweave.source_research._request",
        lambda *_args, **_kwargs: (
            200,
            b"<main>Visible <script>hidden()</script><style>.x{}</style> evidence</main>",
        ),
    )

    assert crawl_public_page("https://example.test/evidence") == "Visible evidence"


@pytest.mark.parametrize(
    ("url", "is_public", "status", "error"),
    [
        ("file:///tmp/item", True, 200, "requires an http"),
        ("http://127.0.0.1/item", False, 200, "non-public"),
        ("https://example.test/redirect", True, 302, "canonical result URL"),
        ("https://example.test/missing", True, 404, "HTTP 404"),
    ],
)
def test_crawl_fails_closed_for_invalid_private_redirect_and_http_error(
    monkeypatch: pytest.MonkeyPatch,
    url: str,
    is_public: bool,
    status: int,
    error: str,
) -> None:
    monkeypatch.setattr(
        "lineageweave.source_research._public_host", lambda _host: is_public
    )
    monkeypatch.setattr(
        "lineageweave.source_research._request",
        lambda *_args, **_kwargs: (status, b"ignored"),
    )

    with pytest.raises((HttpClientError, ValueError), match=error):
        crawl_public_page(url)


def test_searxng_client_validates_endpoint_and_handles_invalid_result_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="must be http"):
        SearxngSourceResearchClient("file:///tmp/search")

    monkeypatch.setattr(
        "lineageweave.source_research.get_json", lambda *_args, **_kwargs: {}
    )
    client = SearxngSourceResearchClient("https://search.test/")
    assert (
        client.retrieve(ResearchLead("source_reference_patent", "query", "evidence"))
        == []
    )


def test_searxng_client_keeps_crawled_text_and_bounded_snippet_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("lineageweave.source_research._public_host", lambda _host: True)
    monkeypatch.setattr(
        "lineageweave.source_research.get_json",
        lambda *_args, **_kwargs: {
            "results": [
                "invalid",
                {"title": "Missing URL"},
                {"url": "https://evidence.test/crawled", "title": "Crawled"},
                {
                    "url": "https://evidence.test/fallback",
                    "title": "Fallback",
                    "content": "  Search   snippet  ",
                },
                {"url": "https://evidence.test/empty", "content": ""},
                {"url": "https://evidence.test/out-of-budget", "content": "ignored"},
            ]
        },
    )

    def crawl(url: str, **_kwargs: object) -> str:
        if url.endswith("crawled"):
            return "Crawled page"
        raise HttpClientError("unavailable")

    monkeypatch.setattr("lineageweave.source_research.crawl_public_page", crawl)
    passages = SearxngSourceResearchClient("https://search.test").retrieve(
        ResearchLead("source_reference_url", "ignored", "source URL evidence")
    )

    assert passages == [
        RetrievedPassage("https://evidence.test/crawled", "Crawled", "Crawled page"),
        RetrievedPassage(
            "https://evidence.test/fallback", "Fallback", "Search snippet"
        ),
    ]


def test_searxng_client_drops_rebound_result_instead_of_trusting_its_snippet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "lineageweave.source_research.get_json",
        lambda *_args, **_kwargs: {
            "results": [
                {
                    "url": "https://evidence.test/rebound",
                    "title": "Rebound",
                    "content": "Untrusted rebound snippet",
                }
            ]
        },
    )
    monkeypatch.setattr("lineageweave.source_research._public_host", lambda _host: True)
    monkeypatch.setattr(
        "lineageweave.source_research.crawl_public_page",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("research crawl refuses a non-public network target")
        ),
    )

    passages = SearxngSourceResearchClient("https://search.test").retrieve(
        ResearchLead("source_reference_url", "url", "evidence")
    )

    assert passages == []


def test_searxng_client_drops_non_public_result_before_crawling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "lineageweave.source_research.get_json",
        lambda *_args, **_kwargs: {
            "results": [
                {
                    "url": "http://127.0.0.1/internal",
                    "title": "Private",
                    "content": "Untrusted private snippet",
                }
            ]
        },
    )
    monkeypatch.setattr(
        "lineageweave.source_research.crawl_public_page",
        lambda *_args, **_kwargs: pytest.fail("private result must not be crawled"),
    )

    passages = SearxngSourceResearchClient("https://search.test").retrieve(
        ResearchLead("source_reference_url", "url", "evidence")
    )

    assert passages == []


def test_research_ingestion_reads_completed_region_ocr_and_persists_source_identity() -> (
    None
):
    class Connection:
        def __init__(self) -> None:
            self.fetch_query = ""
            self.fetchval_calls: list[tuple[str, tuple[object, ...]]] = []

        async def fetch(self, query: str, *_args: object):
            self.fetch_query = " ".join(query.split())
            return [
                {
                    "evidence_text": "Synthetic URL https://example.test/reference",
                    "source_content_unit_id": "content-unit-1",
                    "source_image_region_id": None,
                },
                {
                    "evidence_text": "Synthetic patent evidence",
                    "source_content_unit_id": None,
                    "source_image_region_id": "image-region-1",
                },
            ]

        @asynccontextmanager
        async def transaction(self):
            yield self

        async def execute(self, _query: str, *_args: object) -> str:
            return "OK"

        async def fetchval(self, query: str, *args: object) -> str:
            compact = " ".join(query.split())
            self.fetchval_calls.append((compact, args))
            if "post_source_research_lead" in compact:
                return f"lead-{len(self.fetchval_calls)}"
            if "post_source_research_retrieval" in compact:
                return f"retrieval-{len(self.fetchval_calls)}"
            return f"judgment-{len(self.fetchval_calls)}"

    class SearchClient:
        def retrieve(self, _lead: ResearchLead) -> list[RetrievedPassage]:
            return [
                RetrievedPassage(
                    "https://example.test/evidence",
                    "Synthetic evidence",
                    "Synthetic Publisher evidence",
                )
            ]

    class JudgeClient:
        def judge(
            self, _lead: ResearchLead, passages: list[RetrievedPassage]
        ) -> ResearchJudgment:
            return ResearchJudgment(
                "supported",
                "Synthetic Publisher",
                "The cited passage names the actor.",
                (passages[0].url,),
            )

    class Pool:
        def __init__(self, conn: Connection) -> None:
            self.conn = conn

        @asynccontextmanager
        async def acquire(self):
            yield self.conn

    conn = Connection()
    asyncio.run(
        research_post_sources(Pool(conn), "post-1", SearchClient(), JudgeClient())  # type: ignore[arg-type]
    )

    assert "post_content_image_region" in conn.fetch_query
    assert "image.image_caption" in conn.fetch_query
    assert "image.description_status_code = 'described'" in conn.fetch_query
    assert "not exists" in conn.fetch_query
    assert "description_status_code = 'described'" in conn.fetch_query
    lead_calls = [
        args
        for query, args in conn.fetchval_calls
        if "insert into post_source_research_lead" in query
    ]
    assert [args[1:3] for args in lead_calls] == [
        ("content-unit-1", None),
        (None, "image-region-1"),
    ]


def test_reader_contract_normalizes_status_and_returns_exact_source_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.app import main

    class Connection:
        async def fetch(self, query: str, post_id: str):
            compact = " ".join(query.split())
            assert "when 'research_supported' then 'supported'" in compact
            assert "lead.source_content_unit_id::text" in compact
            assert "lead.source_image_region_id::text" in compact
            assert post_id == "post-1"
            return [
                {
                    "lead_ordinal": 0,
                    "research_status_code": "supported",
                    "source_content_unit_id": "content-unit-1",
                    "source_image_region_id": None,
                    "retrievals": "[]",
                }
            ]

    class Pool:
        @asynccontextmanager
        async def acquire(self):
            yield Connection()

    async def visible_post(*_args: object, **_kwargs: object):
        return {"post_id": "post-1"}

    monkeypatch.setattr(main, "_load_visible_post", visible_post)
    result = asyncio.run(
        main.read_post_source_research("post-1", object(), Pool())  # type: ignore[arg-type]
    )

    assert result["research"] == [
        {
            "lead_ordinal": 0,
            "research_status_code": "supported",
            "source_content_unit_id": "content-unit-1",
            "source_image_region_id": None,
            "retrievals": [],
        }
    ]


def test_null_judge_is_unavailable() -> None:
    judge = NullSourceResearchJudge()
    assert judge.available is False
    with pytest.raises(RuntimeError):
        judge.judge(
            ResearchLead("source_reference_patent", "synthetic", "synthetic"), []
        )


def test_decodes_asyncpg_jsonb_text_into_api_retrievals() -> None:
    assert decode_research_retrievals('[{"url":"https://example.test","cited":true}]') == [
        {"url": "https://example.test", "cited": True}
    ]
    with pytest.raises(ValueError):
        decode_research_retrievals('{"url":"https://example.test"}')


def test_judge_rejects_actor_not_present_in_its_cited_passage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_post_json(*_args, **_kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "status_code": "supported",
                                "sharing_actor_name": "Invented Publisher",
                                "rationale": "A citation was supplied.",
                                "cited_urls": ["https://evidence.test/item"],
                            }
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("lineageweave.source_research.post_json", fake_post_json)
    judge = ContextualOrchestratorSourceResearchJudge(
        "https://orchestrator.test", "key"
    )
    with pytest.raises(ValueError, match="absent from cited evidence"):
        judge.judge(
            ResearchLead(
                "source_reference_patent", "synthetic patent", "synthetic patent"
            ),
            [
                RetrievedPassage(
                    "https://evidence.test/item", "Patent record", "No publisher named"
                )
            ],
        )


def test_judge_accepts_only_cited_source_grounded_actor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_post_json(*_args, **_kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "status_code": "supported",
                                "sharing_actor_name": "Synthetic Publisher",
                                "rationale": "The cited register names the publisher.",
                                "cited_urls": ["https://evidence.test/item"],
                            }
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("lineageweave.source_research.post_json", fake_post_json)
    result = ContextualOrchestratorSourceResearchJudge(
        "https://orchestrator.test", "key"
    ).judge(
        ResearchLead("source_reference_patent", "synthetic patent", "synthetic patent"),
        [
            RetrievedPassage(
                "https://evidence.test/item",
                "Synthetic Publisher patent register",
                "Synthetic Publisher filed the synthetic patent.",
            )
        ],
    )

    assert result.status_code == "supported"
    assert result.sharing_actor_name == "Synthetic Publisher"
    assert result.cited_urls == ("https://evidence.test/item",)


def test_judge_rejects_non_json_provider_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "lineageweave.source_research.post_json",
        lambda *_args, **_kwargs: {"choices": [{"message": {"content": "not json"}}]},
    )

    with pytest.raises(ValueError, match="invalid JSON"):
        ContextualOrchestratorSourceResearchJudge(
            "https://orchestrator.test", "key"
        ).judge(ResearchLead("source_reference_url", "url", "evidence"), [])


@pytest.mark.parametrize(
    ("payload", "error"),
    [
        (
            {
                "status_code": "unknown",
                "sharing_actor_name": None,
                "rationale": "Unknown status.",
                "cited_urls": [],
            },
            "invalid judgment",
        ),
        (
            {
                "status_code": "supported",
                "sharing_actor_name": None,
                "rationale": 1,
                "cited_urls": [],
            },
            "invalid judgment",
        ),
        (
            {
                "status_code": "supported",
                "sharing_actor_name": 1,
                "rationale": "Bad actor type.",
                "cited_urls": [],
            },
            "invalid actor",
        ),
        (
            {
                "status_code": "supported",
                "sharing_actor_name": None,
                "rationale": "Bad citations type.",
                "cited_urls": "https://evidence.test/item",
            },
            "outside the retrieved set",
        ),
        (
            {
                "status_code": "supported",
                "sharing_actor_name": None,
                "rationale": "Unknown citation.",
                "cited_urls": ["https://other.test/item"],
            },
            "outside the retrieved set",
        ),
        (
            {
                "status_code": "supported",
                "sharing_actor_name": "Synthetic Publisher",
                "rationale": "Actor has no citation.",
                "cited_urls": [],
            },
            "without a citation",
        ),
        (
            {
                "status_code": "refuted",
                "sharing_actor_name": "Synthetic Publisher",
                "rationale": "A refutation cannot establish the sharing actor.",
                "cited_urls": ["https://evidence.test/item"],
            },
            "without supported evidence",
        ),
    ],
)
def test_judge_rejects_invalid_evidence_envelopes(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, object],
    error: str,
) -> None:
    monkeypatch.setattr(
        "lineageweave.source_research.post_json",
        lambda *_args, **_kwargs: {
            "choices": [{"message": {"content": json.dumps(payload)}}]
        },
    )
    passage = RetrievedPassage(
        "https://evidence.test/item",
        "Synthetic Publisher record",
        "Synthetic Publisher evidence",
    )

    with pytest.raises(ValueError, match=error):
        ContextualOrchestratorSourceResearchJudge(
            "https://orchestrator.test", "key"
        ).judge(
            ResearchLead("source_reference_patent", "synthetic", "synthetic"),
            [passage],
        )


def test_judge_deduplicates_citations_in_provider_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "lineageweave.source_research.post_json",
        lambda *_args, **_kwargs: {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "status_code": "supported",
                                "sharing_actor_name": None,
                                "rationale": "The passage supports the source.",
                                "cited_urls": [
                                    "https://evidence.test/item",
                                    "https://evidence.test/item",
                                ],
                            }
                        )
                    }
                }
            ]
        },
    )

    result = ContextualOrchestratorSourceResearchJudge(
        "https://orchestrator.test", "key"
    ).judge(
        ResearchLead("source_reference_url", "url", "evidence"),
        [RetrievedPassage("https://evidence.test/item", "Evidence", "Body")],
    )

    assert result.cited_urls == ("https://evidence.test/item",)
