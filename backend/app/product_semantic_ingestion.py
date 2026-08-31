"""Persist product mentions after fail-closed normalized catalog resolution."""

from __future__ import annotations

from typing import Any, Protocol

from lineageweave.product_semantics import (
    ProductExtractionResult,
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

    async def fetchval(self, query: str, *args: object) -> Any:
        """Fetch one scalar value."""
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
    analysis_input_sha256: str,
    orchestrator_session_id: str,
    mentions: tuple[ResolvedProductMention, ...],
    result: ProductExtractionResult,
) -> None:
    """Atomically replace products only while their source revision is current."""
    async with conn.transaction():
        current_digest = await conn.fetchval(
            "select encode(sha256(convert_to(coalesce(post_body, ''), 'UTF8')), 'hex') "
            "from source_post where post_id = $1::uuid for update",
            post_id,
        )
        if current_digest != result.source_revision_digest:
            raise ValueError("product result no longer matches the source revision")
        await conn.execute("delete from post_product_analysis where post_id = $1", post_id)
        await conn.execute(
            "insert into post_product_analysis "
            "(post_id, source_body_sha256, analysis_input_sha256, orchestrator_session_id, "
            "orchestrator_model_receipt) values ($1, $2, $3, $4, $5)",
            post_id,
            result.source_revision_digest,
            analysis_input_sha256,
            orchestrator_session_id,
            result.orchestrator_model_receipt,
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
        for relation in result.extraction.relations:
            if relation.target_kind_code == "operations_fact":
                target_post_id, case_kind_code, fact_ordinal = relation.target_locator
                if target_post_id != post_id:
                    raise ValueError("product relation target is outside the focal post")
                await conn.execute(
                    "insert into product_operations_fact_relation "
                    "(post_id, mention_ordinal, case_kind_code, fact_ordinal, "
                    "relation_type_code, evidence_text, evidence_post_id, evidence_input_sha256) "
                    "values ($1, $2, $3, $4, $5, $6, $7, $8)",
                    post_id,
                    relation.mention_ordinal,
                    case_kind_code,
                    int(fact_ordinal),
                    relation.relation_type_code,
                    relation.evidence_text,
                    relation.evidence_post_id,
                    relation.evidence_input_sha256,
                )
            elif relation.target_kind_code == "project":
                target_post_id, project_key = relation.target_locator
                if target_post_id != post_id:
                    raise ValueError("product relation target is outside the focal post")
                await conn.execute(
                    "insert into product_project_relation "
                    "(post_id, mention_ordinal, project_key, relation_type_code, "
                    "evidence_text, evidence_post_id, evidence_input_sha256) "
                    "values ($1, $2, $3, $4, $5, $6, $7)",
                    post_id,
                    relation.mention_ordinal,
                    project_key,
                    relation.relation_type_code,
                    relation.evidence_text,
                    relation.evidence_post_id,
                    relation.evidence_input_sha256,
                )
            else:  # pragma: no cover - parser owns the closed vocabulary
                raise ValueError("unsupported product relation target kind")
