"""Bounded inline raster images for cited Global Ask evidence."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Literal, Sequence
from uuid import UUID

from lineageweave.chunking import chunk_by_dom

MAX_GLOBAL_ASK_IMAGE_COUNT = 3
MAX_GLOBAL_ASK_IMAGE_BYTES = 2 * 1024 * 1024
MAX_GLOBAL_ASK_TOTAL_IMAGE_BYTES = 4 * 1024 * 1024
_ALLOWED_IMAGE_MIME_TYPES = frozenset(
    {"image/png", "image/jpeg", "image/webp", "image/gif"}
)


@dataclass(frozen=True)
class GlobalAskContentBlock:
    """One prose or source-image block returned to an MCP host."""

    type: Literal["text", "image"]
    text: str | None = None
    post_id: str | None = None
    unit_index: int | None = None
    mime_type: str | None = None
    data_base64: str | None = None
    alt_text: str | None = None
    caption: str | None = None


async def load_global_ask_content_blocks(
    conn: Any,
    answer_text: str,
    cited_post_ids: Sequence[str],
    visible_corporate_entity_ids: Sequence[str] = (),
) -> tuple[GlobalAskContentBlock, ...]:
    """Return answer text and images from citations still visible to the caller."""
    blocks: list[GlobalAskContentBlock] = [
        GlobalAskContentBlock(type="text", text=answer_text)
    ]
    ordered_ids: list[UUID] = []
    seen: set[UUID] = set()
    for post_id in cited_post_ids:
        try:
            parsed = UUID(post_id)
        except (TypeError, ValueError):
            continue
        if parsed not in seen:
            seen.add(parsed)
            ordered_ids.append(parsed)
    if not ordered_ids:
        return tuple(blocks)

    rows = await conn.fetch(
        """
        select post_id, post_title, post_body
          from source_post
         where post_id = any($1::uuid[])
           and (
                 visibility_code = 'public'
                 or corporate_entity_id = any($2::uuid[])
               )
         order by array_position($1::uuid[], post_id)
        """,
        ordered_ids,
        list(visible_corporate_entity_ids),
    )
    total_bytes = 0
    image_count = 0
    for row in rows:
        post_id = str(row["post_id"])
        post_title = str(row["post_title"] or "Source post")
        for chunk in chunk_by_dom(str(row["post_body"] or "")):
            if chunk.unit_type != "image" or chunk.image_data is None:
                continue
            mime_type = chunk.label.casefold()
            byte_length = len(chunk.image_data)
            if (
                mime_type not in _ALLOWED_IMAGE_MIME_TYPES
                or byte_length == 0
                or byte_length > MAX_GLOBAL_ASK_IMAGE_BYTES
            ):
                continue
            if total_bytes + byte_length > MAX_GLOBAL_ASK_TOTAL_IMAGE_BYTES:
                return tuple(blocks)
            blocks.append(
                GlobalAskContentBlock(
                    type="image",
                    post_id=post_id,
                    unit_index=chunk.index,
                    mime_type=mime_type,
                    data_base64=base64.b64encode(chunk.image_data).decode("ascii"),
                    alt_text=f"{post_title} - source image {chunk.index + 1}",
                    caption=post_title,
                )
            )
            image_count += 1
            total_bytes += byte_length
            if image_count == MAX_GLOBAL_ASK_IMAGE_COUNT:
                return tuple(blocks)
    return tuple(blocks)
