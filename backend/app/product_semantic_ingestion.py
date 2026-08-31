"""Persist product mentions after fail-closed normalized catalog resolution."""

from __future__ import annotations

from typing import Any, Protocol

from lineageweave.product_semantics import (
    ProductEvidenceSource,
    ProductExtractionResult,
    ProductMention,
    ProductRelationTarget,
    ResolvedProductMention,
    normalize_product_alias,
    product_analysis_input_sha256,
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

    async def fetchrow(self, query: str, *args: object) -> Any:
        """Fetch one row."""
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


async def load_current_product_relation_targets(
    conn: _Connection,
    post_id: str,
    source_body_digest: str,
    expected_operations_input_sha256: str | None,
) -> tuple[ProductRelationTarget, ...]:
    """Load relation targets that remain bound to the exact focal evidence."""
    operation_rows = await conn.fetch(
        "select fact.case_kind_code, fact.fact_ordinal, fact.fact_type_code, "
        "fact.value_text from operations_case_fact fact "
        "join operations_case_analysis analysis on analysis.post_id = fact.post_id "
        "where fact.post_id = $1 and analysis.source_body_sha256 = $2 "
        "and $3::text is not null and analysis.analysis_input_sha256 = $3 "
        "order by fact.case_kind_code, fact.fact_ordinal",
        post_id,
        source_body_digest,
        expected_operations_input_sha256,
    )
    project_rows = await conn.fetch(
        "select project.project_key, project.project_name "
        "from post_project_mention project join source_post source "
        "on source.post_id = project.post_id where project.post_id = $1 "
        "and encode(sha256(convert_to(coalesce(source.post_body, ''), 'UTF8')), 'hex') = $2 "
        "and btrim(project.evidence_text) <> '' "
        "and strpos(coalesce(source.post_body, ''), project.evidence_text) > 0 "
        "order by project.project_key",
        post_id,
        source_body_digest,
    )
    return tuple(
        ProductRelationTarget(
            f"operations_fact:{row['case_kind_code']}:{row['fact_ordinal']}",
            "operations_fact",
            f"{row['fact_type_code']}: {row['value_text']}",
            (post_id, str(row["case_kind_code"]), str(row["fact_ordinal"])),
        )
        for row in operation_rows
    ) + tuple(
        ProductRelationTarget(
            f"project:{row['project_key']}",
            "project",
            str(row["project_name"]),
            (post_id, str(row["project_key"])),
        )
        for row in project_rows
    )


async def persist_product_mentions(
    conn: _Connection,
    post_id: str,
    analysis_input_sha256: str,
    orchestrator_session_id: str,
    mentions: tuple[ResolvedProductMention, ...],
    result: ProductExtractionResult,
    *,
    expected_operations_input_sha256: str | None,
) -> None:
    """Replace products only while their complete evidence window is current."""
    async with conn.transaction():
        current_source = await conn.fetchrow(
            "select coalesce(post_body, '') as post_body, "
            "encode(sha256(convert_to(coalesce(post_body, ''), 'UTF8')), 'hex') "
            "as source_body_sha256 "
            "from source_post where post_id = $1::uuid for update",
            post_id,
        )
        if (
            current_source is None
            or current_source["source_body_sha256"] != result.source_revision_digest
        ):
            raise ValueError("product result no longer matches the source revision")
        current_targets = await load_current_product_relation_targets(
            conn,
            post_id,
            result.source_revision_digest,
            expected_operations_input_sha256,
        )
        current_input_sha256 = product_analysis_input_sha256(
            (ProductEvidenceSource(post_id, str(current_source["post_body"])),),
            current_targets,
        )
        if current_input_sha256 != analysis_input_sha256:
            raise ValueError("product result no longer matches the relation targets")
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
