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
    user_account_id: str,
) -> tuple[GlobalAskContentBlock, ...]:
    """Return images only when the caller remains authorized at media-read time.

    Source selection and model citation filtering happen earlier in the request,
    but neither is an authorization lease. The media query therefore resolves
    the caller's live ``post_read`` grant and corporate affiliations from the
    database again immediately before any embedded bytes are returned.
    """
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
        select sp.post_id, sp.post_title, sp.post_body
          from source_post sp
         where sp.post_id = any($1::uuid[])
           and exists (
                 select 1
                   from account_role_assignment ara
                   join role_permission rp
                     on rp.access_role_id = ara.access_role_id
                  where ara.user_account_id = $2::uuid
                    and rp.permission_code = 'post_read'
               )
           and (
                 sp.visibility_code = 'public'
                 or exists (
                       select 1
                         from account_affiliation aa
                        where aa.user_account_id = $2::uuid
                          and aa.corporate_entity_id = sp.corporate_entity_id
                     )
               )
         order by array_position($1::uuid[], sp.post_id)
        """,
        ordered_ids,
        user_account_id,
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
