"""Tests for normalized product semantic persistence."""

from contextlib import asynccontextmanager
import asyncio

import pytest

from backend.app.product_semantic_ingestion import (
    load_current_product_relation_targets,
    persist_product_mentions,
    resolve_product_mentions,
)
from lineageweave.product_semantics import (
    ProductEvidenceSource,
    ProductExtraction,
    ProductExtractionResult,
    ProductMention,
    ProductRelation,
    ProductRelationTarget,
    ResolvedProductMention,
    product_analysis_input_sha256,
)


class _Connection:
    def __init__(
        self,
        rows: list[dict[str, str]] | None = None,
        *,
        source_body: str = "Synthetic source body",
        source_digest: str | None = None,
        operation_rows: list[dict[str, object]] | None = None,
        project_rows: list[dict[str, object]] | None = None,
    ) -> None:
        self.rows = rows or []
        self.source_body = source_body
        self.source_digest = source_digest or ProductEvidenceSource(
            "post-a", source_body
        ).input_sha256
        self.operation_rows = operation_rows or []
        self.project_rows = project_rows or []
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    @asynccontextmanager
    async def transaction(self):
        yield

    async def fetch(self, query: str, *args: object) -> list[dict[str, str]]:
        self.calls.append((query, args))
        if "from operations_case_fact" in query:
            return self.operation_rows  # type: ignore[return-value]
        if "from post_project_mention" in query:
            return self.project_rows  # type: ignore[return-value]
        return self.rows

    async def fetchval(self, query: str, *args: object) -> str:
        self.calls.append((query, args))
        return self.source_digest

    async def fetchrow(self, query: str, *args: object) -> dict[str, str]:
        self.calls.append((query, args))
        return {
            "post_body": self.source_body,
            "source_body_sha256": self.source_digest,
        }

    async def execute(self, query: str, *args: object) -> None:
        self.calls.append((query, args))


def test_resolve_product_mentions_uses_parameterized_normalized_alias() -> None:
    connection = _Connection([{"product_catalog_id": "catalog-a"}])
    mention = ProductMention(" PRODUCT  Ｑ ", "PRODUCT", "post-a", "a" * 64)
    resolved = asyncio.run(resolve_product_mentions(connection, (mention,)))
    assert resolved[0].product_catalog_id == "catalog-a"
    assert connection.calls[0][1] == ("product q",)


def test_resolve_product_mentions_preserves_catalog_tie() -> None:
    connection = _Connection(
        [{"product_catalog_id": "catalog-a"}, {"product_catalog_id": "catalog-b"}]
    )
    mention = ProductMention("Product Q", "Product Q", "post-a", "a" * 64)
    resolved = asyncio.run(resolve_product_mentions(connection, (mention,)))
    assert resolved[0].resolution_status_code == "tie"
    assert resolved[0].product_catalog_id is None


def test_persist_product_mentions_replaces_exact_projection() -> None:
    connection = _Connection()
    source = ProductEvidenceSource("post-a", connection.source_body)
    input_digest = product_analysis_input_sha256((source,), ())
    mention = ProductMention("Product Q", "Product Q", "post-a", "a" * 64)
    resolved = ResolvedProductMention(mention, "missing", None)
    asyncio.run(
        persist_product_mentions(
            connection,
            "post-a",
            input_digest,
            "session-a",
            (resolved,),
            ProductExtractionResult(
                source.input_sha256,
                "receipt-a",
                ProductExtraction((mention,), ()),
            ),
            expected_operations_input_sha256=None,
        )
    )
    assert len(connection.calls) == 6
    assert "for update" in connection.calls[0][0]
    assert "from operations_case_fact" in connection.calls[1][0]
    assert "from post_project_mention" in connection.calls[2][0]
    assert connection.calls[3][1] == ("post-a",)
    assert connection.calls[5][1] == (
        "post-a",
        0,
        None,
        "Product Q",
        "missing",
        "Product Q",
        "post-a",
        "a" * 64,
    )


def test_persist_product_mentions_writes_authorized_relation_in_same_transaction() -> None:
    source_body = "Synthetic source body with Product Q"
    project_row = {"project_key": "project-a", "project_name": "Project A"}
    connection = _Connection(source_body=source_body, project_rows=[project_row])
    source = ProductEvidenceSource("post-a", source_body)
    target = ProductRelationTarget(
        "project:project-a", "project", "Project A", ("post-a", "project-a")
    )
    input_digest = product_analysis_input_sha256((source,), (target,))
    mention = ProductMention("Product Q", "Product Q", "post-a", "a" * 64)
    relation = ProductRelation(
        0,
        "project:project-a",
        "project",
        "used_by_project",
        "Product Q",
        "post-a",
        "a" * 64,
        ("post-a", "project-a"),
    )
    asyncio.run(
        persist_product_mentions(
            connection,
            "post-a",
            input_digest,
            "session-a",
            (ResolvedProductMention(mention, "missing", None),),
            ProductExtractionResult(
                source.input_sha256,
                "receipt-a",
                ProductExtraction((mention,), (relation,)),
            ),
            expected_operations_input_sha256=None,
        )
    )
    assert "insert into product_project_relation" in connection.calls[-1][0]
    assert connection.calls[-1][1][0:4] == ("post-a", 0, "project-a", "used_by_project")


def test_persist_product_mentions_rejects_stale_source_revision() -> None:
    """A provider result cannot replace products after the focal body changes."""
    connection = _Connection()
    mention = ProductMention("Product Q", "Product Q", "post-a", "a" * 64)
    result = ProductExtractionResult(
        "c" * 64,
        "receipt-a",
        ProductExtraction((mention,), ()),
    )
    with pytest.raises(ValueError, match="source revision"):
        asyncio.run(
            persist_product_mentions(
                connection,
                "post-a",
                "d" * 64,
                "session-a",
                (ResolvedProductMention(mention, "missing", None),),
                result,
                expected_operations_input_sha256=None,
            )
        )
    assert len(connection.calls) == 1


def test_persist_product_mentions_rejects_changed_target_window() -> None:
    """A target added during extraction prevents stale relation publication."""
    source_body = "Synthetic source body with project evidence"
    source = ProductEvidenceSource("post-a", source_body)
    connection = _Connection(
        source_body=source_body,
        project_rows=[{"project_key": "project-a", "project_name": "Project A"}],
    )
    stale_input_digest = product_analysis_input_sha256((source,), ())
    result = ProductExtractionResult(
        source.input_sha256,
        "receipt-a",
        ProductExtraction((), ()),
    )

    with pytest.raises(ValueError, match="relation targets"):
        asyncio.run(
            persist_product_mentions(
                connection,
                "post-a",
                stale_input_digest,
                "session-a",
                (),
                result,
                expected_operations_input_sha256=None,
            )
        )

    assert all("delete from post_product_analysis" not in query for query, _ in connection.calls)


def test_load_current_product_relation_targets_binds_exact_analysis() -> None:
    """Only typed targets from the exact evidence digests enter the prompt."""
    connection = _Connection(
        operation_rows=[{
            "case_kind_code": "claim_investigation",
            "fact_ordinal": 0,
            "fact_type_code": "order",
            "value_text": "Synthetic order",
        }],
        project_rows=[{"project_key": "project-a", "project_name": "Project A"}],
    )
    targets = asyncio.run(
        load_current_product_relation_targets(
            connection, "post-a", "a" * 64, "b" * 64
        )
    )
    assert [target.target_kind_code for target in targets] == [
        "operations_fact",
        "project",
    ]
    assert connection.calls[0][1] == ("post-a", "a" * 64, "b" * 64)
    assert connection.calls[1][1] == ("post-a", "a" * 64)
