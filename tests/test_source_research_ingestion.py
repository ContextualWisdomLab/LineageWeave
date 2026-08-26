from __future__ import annotations

import asyncio

from backend.app.source_research_ingestion import (
    list_source_research_citations,
    persist_source_research_citation,
    research_post_sources_from_pool,
)
from lineageweave.source_reference_research import (
    JUDGMENT_SUPPORTED,
    JUDGMENT_UNAVAILABLE,
    NEXT_ACTION,
    NO_LEAD_UNAVAILABLE,
    PRIVATE_POST_UNAVAILABLE,
    SourceResearchCitation,
    SourceResearchLead,
    research_query_text,
)


class _Connection:
    def __init__(self, units: list[dict], regions: list[dict] | None = None) -> None:
        self.units = units
        self.regions = regions or []
        self.fetched: list[tuple[str, str]] = []
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, query: str, post_id: str):
        self.fetched.append((query, post_id))
        if "post_content_image_region" in query:
            return self.regions
        return self.units

    async def execute(self, query: str, *args: object):
        self.executed.append((query, args))
        return "INSERT 0 1"

    def transaction(self):
        return _Transaction()


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _Acquire:
    def __init__(self, pool: "_Pool") -> None:
        self.pool = pool

    async def __aenter__(self):
        assert not self.pool.acquired
        self.pool.acquired = True
        return self.pool.connection

    async def __aexit__(self, exc_type, exc, traceback):
        self.pool.acquired = False


class _Pool:
    def __init__(self, connection: _Connection) -> None:
        self.connection = connection
        self.acquired = False

    def acquire(self):
        return _Acquire(self)


class _Client:
    available = True
    maximum_leads = 1

    def __init__(self, pool: _Pool) -> None:
        self.pool = pool

    def research(self, lead: SourceResearchLead) -> SourceResearchCitation:
        assert not self.pool.acquired
        return SourceResearchCitation(
            lead_kind_code=lead.lead_kind_code,
            lead_source_unit_id=lead.lead_source_unit_id,
            lead_image_region_id=lead.lead_image_region_id,
            lead_excerpt_text=lead.lead_excerpt_text,
            search_query_text=research_query_text(lead),
            judgment_code=JUDGMENT_SUPPORTED,
            rationale_text="The retrieved public page matches the source unit.",
            evidence_url="https://example.com/apollo",
            evidence_title_text="Apollo",
            evidence_excerpt_text="Public corroboration.",
        )


class _OneMalformedClient(_Client):
    maximum_leads = 2

    def research(self, lead: SourceResearchLead) -> SourceResearchCitation:
        if lead.lead_source_unit_id == "unit-2":
            raise ValueError("malformed provider response")
        return super().research(lead)


def test_private_posts_do_not_load_leads_or_search() -> None:
    pool = _Pool(_Connection([{"post_content_unit_id": "unit-1", "unit_kind_code": "plain_text", "unit_text": "secret"}]))
    run = asyncio.run(
        research_post_sources_from_pool(pool, _Client(pool), "post-private", "private")
    )
    assert run.unavailable_reason == PRIVATE_POST_UNAVAILABLE
    assert run.citations == ()
    assert pool.connection.executed == []


def test_missing_leads_are_unavailable_without_search() -> None:
    pool = _Pool(_Connection([]))
    run = asyncio.run(
        research_post_sources_from_pool(pool, _Client(pool), "post-public", "public")
    )
    assert run.unavailable_reason == NO_LEAD_UNAVAILABLE
    assert run.citations == ()


def test_public_research_releases_the_pool_during_search() -> None:
    conn = _Connection(
        [
            {
                "post_content_unit_id": "unit-1",
                "unit_kind_code": "plain_text",
                "unit_text": "Demo Corp delayed Apollo.",
            }
        ]
    )
    pool = _Pool(conn)
    run = asyncio.run(research_post_sources_from_pool(pool, _Client(pool), "post-public", "public"))
    assert run.unavailable_reason is None
    assert len(run.citations) == 1
    assert run.citations[0].judgment_code == JUDGMENT_SUPPORTED
    assert run.citations[0].next_action_text == NEXT_ACTION
    assert conn.executed
    assert "source_research_citation" in conn.executed[0][0]
    assert conn.executed[0][1][2] == "unit-1"


def test_malformed_adjudication_fails_closed_for_only_its_lead() -> None:
    conn = _Connection(
        [
            {
                "post_content_unit_id": "unit-1",
                "unit_kind_code": "plain_text",
                "unit_text": "Demo Corp delayed Apollo.",
            },
            {
                "post_content_unit_id": "unit-2",
                "unit_kind_code": "plain_text",
                "unit_text": "A second synthetic passage.",
            },
        ]
    )
    pool = _Pool(conn)
    run = asyncio.run(
        research_post_sources_from_pool(
            pool,
            _OneMalformedClient(pool),
            "post-public",
            "public",
        )
    )
    assert [citation.judgment_code for citation in run.citations] == [
        JUDGMENT_SUPPORTED,
        JUDGMENT_UNAVAILABLE,
    ]
    assert len(conn.executed) == 2


def test_unavailable_recheck_does_not_replace_determinate_evidence() -> None:
    conn = _Connection([])
    citation = SourceResearchCitation(
        lead_kind_code="research_lead_semantic_unit",
        lead_source_unit_id="unit-1",
        lead_excerpt_text="Synthetic public lead.",
        search_query_text="Synthetic public lead.",
        judgment_code=JUDGMENT_UNAVAILABLE,
        rationale_text="Provider unavailable.",
    )

    asyncio.run(persist_source_research_citation(conn, "post-public", citation))

    query = conn.executed[0][0]
    assert "excluded.judgment_code <> 'research_unavailable'" in query
    assert "source_research_citation.judgment_code = 'research_unavailable'" in query


def test_citation_reads_preserve_source_order_for_same_run() -> None:
    conn = _Connection([])

    asyncio.run(list_source_research_citations(conn, "post-public"))

    query = conn.fetched[0][0]
    assert "case when citation.lead_source_unit_id is not null then 0 else 1 end" in query
    assert "unit.unit_index" in query
    assert "image_unit.unit_index" in query
    assert "region.region_index" in query
