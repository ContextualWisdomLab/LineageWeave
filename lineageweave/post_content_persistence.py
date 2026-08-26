"""Persist normalized DOM, image, and embedding artifacts in PostgreSQL.

The source post keeps the original body. This module stores searchable units
and image descriptions separately so formatting metadata never pollutes the
embedding text and a missing vision/embedding channel remains an absent signal.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
from typing import Any, TypeVar

from .chunking import Chunk, chunk_by_source_body
from .embedding_client import EmbeddingClient
from .image_content import ImageContentClient, ImageDescription
from .http_client import HttpClientError, json_request_body
from .post_content_normalization import ImageContentResult, normalize_post_body
from .post_structure import (
    ContextualOrchestratorPostStructureClient,
    NullPostStructureClient,
    PostStructureClient,
    StructureDecision,
)

_LLM_BATCH_MAX_UNITS = 32
_LLM_BATCH_MAX_CHARS = 24_000
_STRUCTURE_UNIT_MAX_CHARS = 8_000
_BatchKey = TypeVar("_BatchKey")
_LOGGER = logging.getLogger(__name__)


def _persisted_unit_kind(chunk: Chunk) -> str:
    """Map explicit source boundaries onto the governed semantic-unit vocabulary."""
    if chunk.unit_type in {"image", "conversation_turn"}:
        return chunk.unit_type
    if chunk.label == "math":
        return "formula"
    if chunk.label in {"tr", "w:tr"}:
        return "table"
    if chunk.label == "li":
        return "list"
    if chunk.unit_type in {"plain_text", "paragraph"} or chunk.label in {"p", "w:p"}:
        return "paragraph"
    return "dom"


def _bounded_unit_batches(  # noqa: UP047 - retain Python 3.10 compatibility.
    units: list[tuple[_BatchKey, str | dict[str, object]]],
) -> list[list[tuple[_BatchKey, str | dict[str, object]]]]:
    """Keep provider requests bounded without changing persisted source units."""
    batches: list[list[tuple[_BatchKey, str | dict[str, object]]]] = []
    batch: list[tuple[_BatchKey, str | dict[str, object]]] = []
    batch_chars = 0
    for unit in units:
        payload = unit[1]
        unit_chars = (
            len(payload)
            if isinstance(payload, str)
            else len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        )
        if batch and (
            len(batch) >= _LLM_BATCH_MAX_UNITS
            or batch_chars + unit_chars > _LLM_BATCH_MAX_CHARS
        ):
            batches.append(batch)
            batch = []
            batch_chars = 0
        batch.append(unit)
        batch_chars += unit_chars
    if batch:
        batches.append(batch)
    return batches


def _bounded_structure_batches(
    units: list[tuple[int, dict[str, object]]], post_title: str
) -> list[list[tuple[int, dict[str, object]]]]:
    """Bound structure batches by their exact serialized HTTP request body."""
    batches: list[list[tuple[int, dict[str, object]]]] = []
    batch: list[tuple[int, dict[str, object]]] = []
    for unit in units:
        candidate = [*batch, unit]
        candidate_body = json_request_body(
            ContextualOrchestratorPostStructureClient.request_payload(
                post_title, [payload for _index, payload in candidate]
            )
        )
        if batch and (
            len(batch) >= _LLM_BATCH_MAX_UNITS
            or len(candidate_body) > _LLM_BATCH_MAX_CHARS
        ):
            batches.append(batch)
            batch = [unit]
        else:
            batch = candidate
    if batch:
        batches.append(batch)
    return batches


def _render_description(description: ImageDescription | None) -> str:
    """Render one image or visual-region description as searchable text."""
    if description is None:
        return "[image: content unavailable]"
    caption = description.caption or "no caption available"
    if description.extracted_text.strip():
        return f"[image: {caption} | text: {description.extracted_text.strip()}]"
    return f"[image: {caption}]"


def _render_image_text(result: ImageContentResult | None) -> str:
    """Render the same searchable placeholder used by normalization."""
    return _render_description(result.description if result else None)


async def persist_post_content(
    conn: Any,
    post_id: str,
    body: str,
    *,
    vision_client: ImageContentClient | None = None,
    embedding_client: EmbeddingClient | None = None,
    normalized_result: Any | None = None,
    structure_client: PostStructureClient | None = None,
    post_title: str = "",
    semantic_units: list[Chunk] | None = None,
) -> int:
    """Replace one post's normalized content artifacts and return unit count.

    Provider calls happen before the short database transaction. A failed or
    unavailable embedding call writes no vector row; it never writes a zero or
    guessed vector. The raw body remains in ``source_post`` for future retry.
    ``semantic_units`` admits caller-parsed source boundaries such as RFC 5322
    conversation turns without inferring them from an opaque body string.
    """
    normalized = normalized_result or normalize_post_body(body, vision_client)
    chunks = semantic_units if semantic_units is not None else chunk_by_source_body(body)
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

    region_embeddable: list[tuple[str, str]] = []
    for chunk, _unit_text, _style in prepared:
        if chunk.unit_type != "image":
            continue
        result = image_results.get(chunk.index)
        for region in result.regions if result else ():
            if region.description is not None:
                region_embeddable.append(
                    (
                        f"region:{chunk.index}:{region.region_index}",
                        _render_description(region.description),
                    )
                )

    text_chunks = [
        chunk for chunk, unit_text, _style in prepared
        if chunk.unit_type != "image" and unit_text
    ]
    explicit_widths = sorted(
        {
            int(chunk.declared_indent_width)
            for chunk in text_chunks
            if int(chunk.declared_indent_width) > 0
        }
    )
    # CSS/XML indentation values are presentation widths, not semantic depth.
    # Rank declared widths instead of dividing by a gcd: 56px and 80px are two
    # nesting levels even when their pixel-unit gcd is 1. Leading source
    # whitespace is deliberately excluded: editors use it for visual alignment
    # and it is not authoritative hierarchy without an orchestrator decision.
    explicit_levels = {width: level for level, width in enumerate(explicit_widths, start=1)}
    unresolved = [
        chunk for chunk in text_chunks if int(chunk.declared_indent_width) <= 0
    ]
    unresolved_indexes = {chunk.index for chunk in unresolved}
    structure_by_index: dict[int, StructureDecision] = {}
    for chunk in text_chunks:
        width = int(chunk.declared_indent_width)
        if width > 0:
            structure_by_index[chunk.index] = StructureDecision(
                unit_index=chunk.index,
                indent_level=explicit_levels[width],
                confidence=1.0,
                evidence="Explicit HTML, CSS, or OOXML indentation.",
                source_code="explicit",
            )
    client = structure_client or NullPostStructureClient()
    if unresolved and client.available:
        structure_units = [
            (
                chunk.index,
                {
                    "unit_index": chunk.index,
                    "text": chunk.text[:_STRUCTURE_UNIT_MAX_CHARS]
                    + (
                        "\n[truncated for structure adjudication]"
                        if len(chunk.text) > _STRUCTURE_UNIT_MAX_CHARS
                        else ""
                    ),
                    "label": chunk.label,
                    "style": formatting.get(chunk.index),
                    "source_indent_width": max(
                        0,
                        int(chunk.indent_width) - int(chunk.declared_indent_width),
                    ),
                    "declared_indent_width": int(chunk.declared_indent_width),
                },
            )
            for chunk in unresolved
        ]
        for batch in _bounded_structure_batches(structure_units, post_title):
            try:
                request_body = json_request_body(
                    ContextualOrchestratorPostStructureClient.request_payload(
                        post_title, [payload for _index, payload in batch]
                    )
                )
                if len(request_body) > _LLM_BATCH_MAX_CHARS:
                    raise HttpClientError("structure adjudication request exceeds size limit")
                decisions = await asyncio.to_thread(
                    client.infer,
                    post_title,
                    [payload for _index, payload in batch],
                )
                for decision in decisions:
                    if decision.unit_index in unresolved_indexes:
                        structure_by_index[decision.unit_index] = decision
            except (OSError, RuntimeError, ValueError) as exc:
                _LOGGER.warning(
                    "post content structure batch unavailable",
                    extra={
                        "post_id": post_id,
                        "batch_size": len(batch),
                        "exception_type": type(exc).__name__,
                    },
                )
    for chunk in unresolved:
        structure_by_index.setdefault(
            chunk.index,
            StructureDecision(
                unit_index=chunk.index,
                indent_level=0,
                confidence=0.0,
                evidence="No explicit indentation and no complete adjudication evidence.",
                source_code="unresolved",
            ),
        )

    vectors: dict[str, list[float]] = {}
    if embedding_client is not None and embedding_client.available:
        embeddable = [
            (f"unit:{chunk.index}", unit_text)
            for chunk, unit_text, _style in prepared
            if unit_text
        ] + region_embeddable
        embed_many = getattr(embedding_client, "embed_many", None)
        for batch in _bounded_unit_batches(embeddable):
            try:
                if callable(embed_many):
                    embedded = await asyncio.to_thread(embed_many, [text for _, text in batch])
                    candidates = zip((index for index, _ in batch), embedded, strict=True)
                else:
                    candidates = [
                        (index, await asyncio.to_thread(embedding_client.embed, text))
                        for index, text in batch
                    ]
                for embedding_key, vector in candidates:
                    if isinstance(vector, list) and vector and all(
                        isinstance(value, (int, float)) and math.isfinite(float(value))
                        for value in vector
                    ):
                        vectors[embedding_key] = [float(value) for value in vector]
            except (OSError, RuntimeError, ValueError) as exc:
                _LOGGER.warning(
                    "post content embedding batch unavailable",
                    extra={
                        "post_id": post_id,
                        "batch_size": len(batch),
                        "exception_type": type(exc).__name__,
                    },
                )

    embedding_model_code = (
        getattr(embedding_client, "resolved_model", None)
        if embedding_client is not None
        else None
    )
    if vectors and not embedding_model_code:
        _LOGGER.warning(
            "post content embeddings omitted because the orchestrator returned no model identity",
            extra={"post_id": post_id},
        )
        vectors.clear()

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
                _persisted_unit_kind(chunk),
                chunk.label,
                unit_text,
                style,
            )
            unit_ids[chunk.index] = str(unit_id)
            structure = structure_by_index.get(chunk.index)
            if structure is not None:
                await conn.execute(
                    """
                    insert into post_content_unit_structure
                        (post_content_unit_id, indent_level, decision_source_code,
                         confidence, evidence_text)
                    values ($1, $2, $3, $4, $5)
                    """,
                    unit_id,
                    structure.indent_level,
                    structure.source_code,
                    structure.confidence,
                    structure.evidence,
                )
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
            for region in result.regions if result else ():
                region_id = await conn.fetchval(
                    """
                    insert into post_content_image_region
                        (post_content_image_id, region_index, x_ratio, y_ratio,
                         width_ratio, height_ratio, description_status_code,
                         extracted_text, caption)
                    values ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    returning post_content_image_region_id
                    """,
                    image_id,
                    region.region_index,
                    region.region.x,
                    region.region.y,
                    region.region.width,
                    region.region.height,
                    region.status_code,
                    region.description.extracted_text if region.description else None,
                    region.description.caption if region.description else None,
                )
                for tag in region.description.tags if region.description else ():
                    await conn.execute(
                        "insert into post_content_image_region_tag (post_content_image_region_id, tag_text) values ($1, $2) on conflict do nothing",
                        region_id,
                        tag,
                    )
                vector = vectors.get(f"region:{chunk.index}:{region.region_index}")
                if embedding_model_code and vector:
                    region_embedding_id = await conn.fetchval(
                        """
                        insert into post_content_image_region_embedding
                            (post_content_image_region_id, embedding_model_code,
                             embedding_dimension_count)
                        values ($1, $2, $3)
                        returning post_content_image_region_embedding_id
                        """,
                        region_id,
                        embedding_model_code,
                        len(vector),
                    )
                    for dimension_index, dimension_value in enumerate(vector):
                        await conn.execute(
                            "insert into post_content_image_region_embedding_value (post_content_image_region_embedding_id, dimension_index, dimension_value) values ($1, $2, $3)",
                            region_embedding_id,
                            dimension_index,
                            dimension_value,
                        )

        if embedding_model_code:
            for embedding_key, vector in vectors.items():
                if not embedding_key.startswith("unit:"):
                    continue
                unit_index = int(embedding_key.removeprefix("unit:"))
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
