"""Persist product mentions after fail-closed normalized catalog resolution."""

from __future__ import annotations

from typing import Any, Protocol

from lineageweave.product_semantics import (
    ProductMention,
    ResolvedProductMention,
    normalize_product_alias,
    resolve_product_mention,
)


class _Connection(Protocol):
    def transaction(self) -> Any:
        """Open an atomic database transaction."""
        pass  # pragma: no cover - structural protocol declaration

    async def fetch(self, query: str, *args: object) -> list[Any]:
        """Fetch parameterized rows."""
        pass  # pragma: no cover - structural protocol declaration

    async def execute(self, query: str, *args: object) -> Any:
        """Execute one parameterized statement."""
        pass  # pragma: no cover - structural protocol declaration


async def resolve_product_mentions(
    conn: _Connection, mentions: tuple[ProductMention, ...]
) -> tuple[ResolvedProductMention, ...]:
    """Resolve every mention by exact normalized alias, retaining ties."""
    resolved: list[ResolvedProductMention] = []
    for mention in mentions:
        rows = await conn.fetch(
            "select product_catalog_id from product_catalog_alias "
            "where normalized_alias_text = $1 order by product_catalog_id",
            normalize_product_alias(mention.extracted_product_name),
        )
        resolved.append(
            resolve_product_mention(
                mention, tuple(str(row["product_catalog_id"]) for row in rows)
            )
        )
    return tuple(resolved)


async def persist_product_mentions(
    conn: _Connection,
    post_id: str,
    source_body_sha256: str,
    analysis_input_sha256: str,
    orchestrator_session_id: str,
    mentions: tuple[ResolvedProductMention, ...],
) -> None:
    """Atomically replace one exact post's product analysis projection."""
    async with conn.transaction():
        await conn.execute("delete from post_product_analysis where post_id = $1", post_id)
        await conn.execute(
            "insert into post_product_analysis "
            "(post_id, source_body_sha256, analysis_input_sha256, orchestrator_session_id) "
            "values ($1, $2, $3, $4)",
            post_id,
            source_body_sha256,
            analysis_input_sha256,
            orchestrator_session_id,
        )
        for ordinal, resolved in enumerate(mentions):
            mention = resolved.mention
            await conn.execute(
                "insert into post_product_mention "
                "(post_id, mention_ordinal, product_catalog_id, extracted_product_name, "
                "resolution_status_code, evidence_text, evidence_post_id, evidence_input_sha256) "
                "values ($1, $2, $3, $4, $5, $6, $7, $8)",
                post_id,
                ordinal,
                resolved.product_catalog_id,
                mention.extracted_product_name,
                resolved.resolution_status_code,
                mention.evidence_text,
                mention.evidence_post_id,
                mention.evidence_input_sha256,
            )
