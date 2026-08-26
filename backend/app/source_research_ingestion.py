"""Load source leads, run public research, and persist citations.

Private posts fail closed before any search or retrieval. Already-checked
leads are replaced in place so the buyer sees the latest public resource
for that unit or image region.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import asyncpg

from lineageweave.http_client import HttpClientError
from lineageweave.source_reference_research import (
    NO_LEAD_UNAVAILABLE,
    PRIVATE_POST_UNAVAILABLE,
    VISIBILITY_PUBLIC,
    SourceResearchCitation,
    SourceResearchClient,
    SourceResearchLead,
    select_source_research_leads,
    unavailable_citation,
)


@dataclass(frozen=True)
class SourceResearchRun:
    """One post-scoped research attempt, including fail-closed unavailability."""

    post_id: str
    visibility_code: str
    citations: tuple[SourceResearchCitation, ...]
    unavailable_reason: str | None = None


async def load_source_research_leads(
    conn: asyncpg.Connection,
    post_id: str,
) -> tuple[SourceResearchLead, ...]:
    """Read persisted semantic units and image regions for ``post_id``."""

    units = await conn.fetch(
        """
        select post_content_unit_id::text as post_content_unit_id,
               unit_kind_code,
               unit_text
          from post_content_unit
         where post_id = $1
         order by unit_index
        """,
        post_id,
    )
    regions = await conn.fetch(
        """
        select region.post_content_image_region_id::text as post_content_image_region_id,
               region.caption,
               region.extracted_text
          from post_content_image_region region
          join post_content_image image
            on image.post_content_image_id = region.post_content_image_id
          join post_content_unit unit
            on unit.post_content_unit_id = image.post_content_unit_id
         where unit.post_id = $1
         order by region.region_index, region.post_content_image_region_id
        """,
        post_id,
    )
    return select_source_research_leads(
        [dict(row) for row in units],
        [dict(row) for row in regions],
    )


async def list_source_research_citations(
    conn: asyncpg.Connection,
    post_id: str,
) -> list[dict[str, object]]:
    """Return persisted citations for one authorized post, newest first."""

    rows = await conn.fetch(
        """
        select lead_kind_code,
               lead_source_unit_id::text as lead_source_unit_id,
               lead_image_region_id::text as lead_image_region_id,
               lead_excerpt_text,
               search_query_text,
               evidence_url,
               evidence_title_text,
               evidence_excerpt_text,
               judgment_code,
               rationale_text,
               next_action_text,
               checked_at
          from source_research_citation
         where post_id = $1
         order by checked_at desc, source_research_citation_id
        """,
        post_id,
    )
    return [dict(row) for row in rows]


async def persist_source_research_citation(
    conn: asyncpg.Connection,
    post_id: str,
    citation: SourceResearchCitation,
) -> None:
    """Replace the latest citation for this lead."""

    values = (
        post_id,
        citation.lead_kind_code,
        citation.lead_source_unit_id,
        citation.lead_image_region_id,
        citation.lead_excerpt_text,
        citation.search_query_text,
        citation.evidence_url,
        citation.evidence_title_text,
        citation.evidence_excerpt_text,
        citation.judgment_code,
        citation.rationale_text,
        citation.next_action_text,
    )
    if citation.lead_source_unit_id is not None:
        await conn.execute(
            """
            insert into source_research_citation (
                post_id,
                lead_kind_code,
                lead_source_unit_id,
                lead_image_region_id,
                lead_excerpt_text,
                search_query_text,
                evidence_url,
                evidence_title_text,
                evidence_excerpt_text,
                judgment_code,
                rationale_text,
                next_action_text
            ) values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            on conflict (post_id, lead_source_unit_id)
                where lead_source_unit_id is not null
            do update set
                lead_excerpt_text = excluded.lead_excerpt_text,
                search_query_text = excluded.search_query_text,
                evidence_url = excluded.evidence_url,
                evidence_title_text = excluded.evidence_title_text,
                evidence_excerpt_text = excluded.evidence_excerpt_text,
                judgment_code = excluded.judgment_code,
                rationale_text = excluded.rationale_text,
                next_action_text = excluded.next_action_text,
                checked_at = now()
            """,
            *values,
        )
        return
    await conn.execute(
        """
        insert into source_research_citation (
            post_id,
            lead_kind_code,
            lead_source_unit_id,
            lead_image_region_id,
            lead_excerpt_text,
            search_query_text,
            evidence_url,
            evidence_title_text,
            evidence_excerpt_text,
            judgment_code,
            rationale_text,
            next_action_text
        ) values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        on conflict (post_id, lead_image_region_id)
            where lead_image_region_id is not null
        do update set
            lead_excerpt_text = excluded.lead_excerpt_text,
            search_query_text = excluded.search_query_text,
            evidence_url = excluded.evidence_url,
            evidence_title_text = excluded.evidence_title_text,
            evidence_excerpt_text = excluded.evidence_excerpt_text,
            judgment_code = excluded.judgment_code,
            rationale_text = excluded.rationale_text,
            next_action_text = excluded.next_action_text,
            checked_at = now()
        """,
        *values,
    )



async def research_post_sources_from_pool(
    pool: asyncpg.Pool,
    client: SourceResearchClient,
    post_id: str,
    visibility_code: str,
) -> SourceResearchRun:
    """Research public leads without holding a DB connection during web I/O."""

    if visibility_code != VISIBILITY_PUBLIC:
        return SourceResearchRun(
            post_id=post_id,
            visibility_code=visibility_code,
            citations=(),
            unavailable_reason=PRIVATE_POST_UNAVAILABLE,
        )
    async with pool.acquire() as conn:
        leads = await load_source_research_leads(conn, post_id)
    if not leads:
        return SourceResearchRun(
            post_id=post_id,
            visibility_code=visibility_code,
            citations=(),
            unavailable_reason=NO_LEAD_UNAVAILABLE,
        )
    citations: list[SourceResearchCitation] = []
    for lead in leads:
        try:
            citation = await asyncio.to_thread(client.research, lead)
        except (HttpClientError, OSError, ValueError):
            citation = unavailable_citation(
                lead,
                "Public evidence could not be verified. Try again later or review the post evidence manually.",
            )
        citations.append(citation)
    async with pool.acquire() as conn, conn.transaction():
        for citation in citations:
            await persist_source_research_citation(conn, post_id, citation)
    return SourceResearchRun(
        post_id=post_id,
        visibility_code=visibility_code,
        citations=tuple(citations),
    )
