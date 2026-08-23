"""Persist ADR 0133 source-reference research with citation lineage."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass

import asyncpg

from lineageweave.source_research import (
    ContextualOrchestratorSourceResearchJudge,
    ResearchJudgment,
    ResearchLead,
    RetrievedPassage,
    SearxngSourceResearchClient,
    discover_research_leads,
)

_STATUS_CODES = {
    "supported": "research_supported",
    "refuted": "research_refuted",
    "not_enough_information": "research_not_enough_information",
}


@dataclass(frozen=True)
class PersistedResearch:
    """One persisted lead and its evidence-bearing judgment."""

    lead: ResearchLead
    passages: tuple[RetrievedPassage, ...]
    judgment: ResearchJudgment


def decode_research_retrievals(value: object) -> list[dict[str, object]]:
    """Normalize asyncpg's JSONB text codec into the API's array contract."""
    decoded = json.loads(value) if isinstance(value, str) else value
    if not isinstance(decoded, list) or any(not isinstance(item, dict) for item in decoded):
        raise ValueError("source research retrievals must be a JSON array of objects")
    return decoded


async def research_post_sources(
    pool: asyncpg.Pool,
    post_id: str,
    search_client: SearxngSourceResearchClient,
    judge_client: ContextualOrchestratorSourceResearchJudge,
) -> tuple[PersistedResearch, ...]:
    """Research persisted semantic units and atomically replace prior results."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
        select unit.unit_text as evidence_text,
               unit.post_content_unit_id::text as source_content_unit_id,
               null::text as source_image_region_id,
               unit.unit_index, -1 as region_index
          from post_content_unit unit
         where unit.post_id = $1
           and unit.unit_kind_code <> 'image'
           and btrim(unit.unit_text) <> ''
        union all
        select concat_ws(' ', image.image_caption, image.extracted_text),
               unit.post_content_unit_id::text,
               null::text,
               unit.unit_index, -1
          from post_content_unit unit
          join post_content_image image using (post_content_unit_id)
         where unit.post_id = $1
           and image.description_status_code = 'described'
           and btrim(concat_ws(' ', image.image_caption, image.extracted_text)) <> ''
           and not exists (
               select 1
                 from post_content_image_region region
                where region.post_content_image_id = image.post_content_image_id
                  and region.description_status_code = 'described'
           )
        union all
        select concat_ws(' ', region.image_caption, region.extracted_text),
               null::text,
               region.post_content_image_region_id::text,
               unit.unit_index, region.region_index
          from post_content_unit unit
          join post_content_image image using (post_content_unit_id)
          join post_content_image_region region using (post_content_image_id)
         where unit.post_id = $1
           and region.description_status_code = 'described'
           and btrim(concat_ws(' ', region.image_caption, region.extracted_text)) <> ''
         order by unit_index, region_index
            """,
            post_id,
        )
    leads = discover_research_leads(
        [
            (
                str(row["evidence_text"]),
                row["source_content_unit_id"],
                row["source_image_region_id"],
            )
            for row in rows
        ]
    )

    def research() -> list[PersistedResearch]:
        researched: list[PersistedResearch] = []
        for lead in leads:
            passages = search_client.retrieve(lead)
            judgment = judge_client.judge(lead, passages)
            researched.append(PersistedResearch(lead, tuple(passages), judgment))
        return researched

    researched = await asyncio.to_thread(research)
    async with pool.acquire() as conn, conn.transaction():
        await conn.execute(
            "delete from post_source_research_lead where post_id = $1", post_id
        )
        for lead_ordinal, item in enumerate(researched):
            lead_id = await conn.fetchval(
                """
                insert into post_source_research_lead
                    (post_id, source_content_unit_id, source_image_region_id,
                     lead_ordinal, lead_type_code, query_text, evidence_text)
                values ($1, $2, $3, $4, $5, $6, $7)
                returning post_source_research_lead_id
                """,
                post_id,
                item.lead.source_content_unit_id,
                item.lead.source_image_region_id,
                lead_ordinal,
                item.lead.lead_type_code,
                item.lead.query_text,
                item.lead.evidence_text,
            )
            retrieval_ids: dict[str, str] = {}
            for retrieval_ordinal, passage in enumerate(item.passages):
                retrieval_id = await conn.fetchval(
                    """
                    insert into post_source_research_retrieval
                        (post_source_research_lead_id, retrieval_ordinal,
                         evidence_url, evidence_title, passage_text, content_sha256)
                    values ($1, $2, $3, $4, $5, $6)
                    returning post_source_research_retrieval_id
                    """,
                    lead_id,
                    retrieval_ordinal,
                    passage.url,
                    passage.title,
                    passage.text,
                    hashlib.sha256(passage.text.encode("utf-8")).hexdigest(),
                )
                retrieval_ids[passage.url] = str(retrieval_id)
            judgment_id = await conn.fetchval(
                """
                insert into post_source_research_judgment
                    (post_source_research_lead_id, research_status_code,
                     sharing_actor_name, rationale_text)
                values ($1, $2, $3, $4)
                returning post_source_research_judgment_id
                """,
                lead_id,
                _STATUS_CODES[item.judgment.status_code],
                item.judgment.sharing_actor_name,
                item.judgment.rationale,
            )
            for cited_url in item.judgment.cited_urls:
                await conn.execute(
                    """
                    insert into post_source_research_citation
                        (post_source_research_lead_id,
                         post_source_research_judgment_id,
                         post_source_research_retrieval_id)
                    values ($1, $2, $3)
                    """,
                    lead_id,
                    judgment_id,
                    retrieval_ids[cited_url],
                )
    return tuple(researched)
