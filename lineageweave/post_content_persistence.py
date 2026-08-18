"""Persist normalized DOM, image, and embedding artifacts in PostgreSQL.

The source post keeps the original body. This module stores searchable units
and image descriptions separately so formatting metadata never pollutes the
embedding text and a missing vision/embedding channel remains an absent signal.
"""

from __future__ import annotations

import asyncio
import hashlib
import math
from typing import Any

from .chunking import Chunk, chunk_by_dom
from .embedding_client import EmbeddingClient
from .image_content import ImageContentClient
from .post_content_normalization import ImageContentResult, normalize_post_body


def _render_image_text(result: ImageContentResult | None) -> str:
    """Render the same searchable placeholder used by normalization."""
    if result is None or result.description is None:
        return "[image: content unavailable]"
    description = result.description
    caption = description.caption or "no caption available"
    if description.extracted_text.strip():
        return f"[image: {caption} | text: {description.extracted_text.strip()}]"
    return f"[image: {caption}]"


async def persist_post_content(
    conn: Any,
    post_id: str,
    body: str,
    *,
    vision_client: ImageContentClient | None = None,
    embedding_client: EmbeddingClient | None = None,
    embedding_model_code: str | None = None,
    normalized_result: Any | None = None,
) -> int:
    """Replace one post's normalized content artifacts and return unit count.

    Provider calls happen before the short database transaction. A failed or
    unavailable embedding call writes no vector row; it never writes a zero or
    guessed vector. The raw body remains in ``source_post`` for future retry.
    """
    normalized = normalized_result or normalize_post_body(body, vision_client)
    chunks = chunk_by_dom(body)
    if not chunks and body:
        chunks = [Chunk(text=body, unit_type="plain_text", index=0)]
    image_results = {result.chunk_index: result for result in normalized.image_results}
    formatting = {hint.chunk_index: hint.style for hint in normalized.formatting_hints}

    prepared: list[tuple[Chunk, str, str | None]] = []
    for chunk in chunks:
        if chunk.unit_type == "image":
            result = image_results.get(chunk.index)
            unit_text = _render_image_text(result)
        else:
            unit_text = chunk.text
        prepared.append((chunk, unit_text, formatting.get(chunk.index)))

    vectors: list[tuple[int, list[float]]] = []
    if embedding_client is not None and embedding_client.available and embedding_model_code:
        embeddable = [(chunk.index, unit_text) for chunk, unit_text, _style in prepared if unit_text]
        embed_many = getattr(embedding_client, "embed_many", None)
        try:
            if callable(embed_many):
                embedded = await asyncio.to_thread(embed_many, [text for _, text in embeddable])
                candidates = zip((index for index, _ in embeddable), embedded, strict=True)
            else:
                candidates = (
                    (index, await asyncio.to_thread(embedding_client.embed, text))
                    for index, text in embeddable
                )
            for unit_index, vector in candidates:
                if isinstance(vector, list) and vector and all(
                    isinstance(value, (int, float)) and math.isfinite(float(value))
                    for value in vector
                ):
                    vectors.append((unit_index, [float(value) for value in vector]))
        except Exception:  # noqa: BLE001 - missing provider signal stays absent.
            vectors = []

    async with conn.transaction():
        await conn.execute("delete from post_content_unit where post_id = $1", post_id)
        unit_ids: dict[int, str] = {}
        for chunk, unit_text, style in prepared:
            unit_id = await conn.fetchval(
                """
                insert into post_content_unit
                    (post_id, unit_index, unit_kind_code, unit_label, unit_text, inline_style)
                values ($1, $2, $3, $4, $5, $6)
                returning post_content_unit_id
                """,
                post_id,
                chunk.index,
                chunk.unit_type,
                chunk.label,
                unit_text,
                style,
            )
            unit_ids[chunk.index] = str(unit_id)
            if chunk.unit_type != "image" or chunk.image_data is None:
                continue
            result = image_results.get(chunk.index)
            description = result.description if result else None
            image_id = await conn.fetchval(
                """
                insert into post_content_image
                    (post_content_unit_id, mime_type, content_sha256, byte_length,
                     description_status_code, extracted_text, caption)
                values ($1, $2, $3, $4, $5, $6, $7)
                returning post_content_image_id
                """,
                unit_id,
                chunk.label,
                hashlib.sha256(chunk.image_data).hexdigest(),
                len(chunk.image_data),
                result.status_code if result else "unavailable",
                description.extracted_text if description else None,
                description.caption if description else None,
            )
            for tag in description.tags if description else ():
                await conn.execute(
                    "insert into post_content_image_tag (post_content_image_id, tag_text) values ($1, $2) on conflict do nothing",
                    image_id,
                    tag,
                )

        if embedding_model_code:
            for unit_index, vector in vectors:
                embedding_id = await conn.fetchval(
                    """
                    insert into post_content_embedding
                        (post_content_unit_id, embedding_model_code, embedding_dimension_count)
                    values ($1, $2, $3)
                    returning post_content_embedding_id
                    """,
                    unit_ids[unit_index],
                    embedding_model_code,
                    len(vector),
                )
                for dimension_index, dimension_value in enumerate(vector):
                    await conn.execute(
                        "insert into post_content_embedding_value (post_content_embedding_id, dimension_index, dimension_value) values ($1, $2, $3)",
                        embedding_id,
                        dimension_index,
                        dimension_value,
                    )
    return len(prepared)
