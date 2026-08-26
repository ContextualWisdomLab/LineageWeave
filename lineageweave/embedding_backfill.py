"""Atomic, cross-post embedding backfill for already-normalized semantic units."""

from __future__ import annotations

import asyncio
import math
from typing import Any

from .embedding_client import ContextualOrchestratorEmbeddingClient
from .llm_context import build_post_llm_metadata

_SELECT_UNITS_SQL = """
with candidates as (
    select unit.post_content_unit_id, unit.unit_text, unit.unit_index,
           post.post_id, post.author_account_id, post.source_process_unit_code,
           post.source_author_code, post.source_company_code,
           post.source_customer_code, post.source_project_code,
           post.source_sales_pool_code, entity.corporate_entity_code,
           row_number() over (
               order by post.created_at, post.post_id, unit.unit_index
           ) as candidate_ordinal,
           sum(octet_length(unit.unit_text) + 1) over (
               order by post.created_at, post.post_id, unit.unit_index
           ) as cumulative_text_bytes
      from post_content_unit unit
      join source_post post using (post_id)
      left join corporate_entity entity using (corporate_entity_id)
     where nullif(btrim(unit.unit_text), '') is not null
       and not exists (
           select 1 from post_content_embedding existing
            where existing.post_content_unit_id = unit.post_content_unit_id
       )
)
select * from candidates
 where candidate_ordinal = 1
    or (cumulative_text_bytes <= $1 and candidate_ordinal <= $2)
 order by cumulative_text_bytes
"""


async def backfill_post_content_embeddings(
    conn: Any,
    embedding_client: ContextualOrchestratorEmbeddingClient,
    *,
    max_request_body_bytes: int,
    max_inputs: int,
) -> dict[str, int | str]:
    """Embed one explicitly bounded unit set and atomically persist the complete batch.

    The provider call finishes and validates every vector before the transaction
    starts. Consequently a provider failure cannot delete or partially replace a
    persisted embedding. The candidate query and final prefix are both bounded
    by contextual-orchestrator's advertised request-body ceiling.
    """
    if max_request_body_bytes < 1:
        raise ValueError("max_request_body_bytes must be positive")
    if max_inputs < 1:
        raise ValueError("max_inputs must be positive")
    rows = list(await conn.fetch(_SELECT_UNITS_SQL, max_request_body_bytes, max_inputs))
    if not rows:
        return {"selected_units": 0, "persisted_units": 0, "dimension_values": 0}

    texts = [str(row["unit_text"]) for row in rows]
    metadata = []
    attributions = []
    for row in rows:
        item_metadata = build_post_llm_metadata(str(row["post_id"]), row)
        item_metadata["lineageweave_post_content_unit_id"] = str(
            row["post_content_unit_id"]
        )
        item_metadata["lineageweave_unit_index"] = str(row["unit_index"])
        metadata.append(item_metadata)
        attributions.append(
            {
                "service": "lineageweave",
                **(
                    {"team": str(row["source_process_unit_code"])}
                    if row["source_process_unit_code"]
                    else {}
                ),
                **(
                    {"company": str(row["corporate_entity_code"])}
                    if row["corporate_entity_code"]
                    else {}
                ),
            }
        )

    selected_count = 0
    lower = 1
    upper = len(rows)
    while lower <= upper:
        candidate_count = (lower + upper) // 2
        body_size = embedding_client.batch_request_body_size(
            texts[:candidate_count],
            input_attributions=attributions[:candidate_count],
            input_metadata=metadata[:candidate_count],
        )
        if body_size > max_request_body_bytes:
            upper = candidate_count - 1
        else:
            selected_count = candidate_count
            lower = candidate_count + 1
    if selected_count == 0:
        raise ValueError("one semantic unit exceeds the advertised embedding request ceiling")
    rows = rows[:selected_count]
    texts = texts[:selected_count]
    metadata = metadata[:selected_count]
    attributions = attributions[:selected_count]

    vectors = await asyncio.to_thread(
        embedding_client.embed_many,
        texts,
        input_attributions=attributions,
        input_metadata=metadata,
    )
    if len(vectors) != len(rows):
        raise ValueError("embedding batch did not return one vector per input")
    dimension_count = len(vectors[0]) if vectors else 0
    if dimension_count < 1 or any(
        len(vector) != dimension_count
        or not all(isinstance(value, (int, float)) and math.isfinite(float(value)) for value in vector)
        for vector in vectors
    ):
        raise ValueError("embedding batch returned inconsistent vectors")
    model = embedding_client.resolved_model
    if not model:
        raise ValueError("embedding batch did not identify its resolved model")

    unit_ids = [row["post_content_unit_id"] for row in rows]
    async with conn.transaction():
        await conn.executemany(
            """
            insert into post_content_embedding
                (post_content_unit_id, embedding_model_code, embedding_dimension_count)
            values ($1, $2, $3)
            on conflict (post_content_unit_id, embedding_model_code) do update
                set embedding_dimension_count = excluded.embedding_dimension_count,
                    created_at = now()
            """,
            [(unit_id, model, dimension_count) for unit_id in unit_ids],
        )
        embedding_rows = await conn.fetch(
            """
            select post_content_embedding_id, post_content_unit_id
              from post_content_embedding
             where embedding_model_code = $1
               and post_content_unit_id = any($2::uuid[])
            """,
            model,
            unit_ids,
        )
        embedding_by_unit = {
            row["post_content_unit_id"]: row["post_content_embedding_id"]
            for row in embedding_rows
        }
        if len(embedding_by_unit) != len(unit_ids):
            raise RuntimeError("embedding headers were not persisted completely")
        embedding_ids = [embedding_by_unit[unit_id] for unit_id in unit_ids]
        await conn.execute(
            "delete from post_content_embedding_value where post_content_embedding_id = any($1::uuid[])",
            embedding_ids,
        )
        values = [
            (embedding_by_unit[unit_id], dimension_index, float(dimension_value))
            for unit_id, vector in zip(unit_ids, vectors, strict=True)
            for dimension_index, dimension_value in enumerate(vector)
        ]
        await conn.executemany(
            """
            insert into post_content_embedding_value
                (post_content_embedding_id, dimension_index, dimension_value)
            values ($1, $2, $3)
            """,
            values,
        )
    return {
        "selected_units": len(rows),
        "persisted_units": len(rows),
        "dimension_values": len(rows) * dimension_count,
        "model": model,
    }
