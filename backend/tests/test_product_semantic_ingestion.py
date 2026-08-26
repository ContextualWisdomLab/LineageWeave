"""Tests for normalized product semantic persistence."""

from contextlib import asynccontextmanager
import asyncio

from backend.app.product_semantic_ingestion import (
    persist_product_mentions,
    resolve_product_mentions,
)
from lineageweave.product_semantics import (
    ProductExtraction,
    ProductMention,
    ProductRelation,
    ResolvedProductMention,
)


class _Connection:
    def __init__(self, rows: list[dict[str, str]] | None = None) -> None:
        self.rows = rows or []
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    @asynccontextmanager
    async def transaction(self):
        yield

    async def fetch(self, query: str, *args: object) -> list[dict[str, str]]:
        self.calls.append((query, args))
        return self.rows

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
    mention = ProductMention("Product Q", "Product Q", "post-a", "a" * 64)
    resolved = ResolvedProductMention(mention, "missing", None)
    asyncio.run(
        persist_product_mentions(
            connection, "post-a", "b" * 64, "c" * 64, "session-a", (resolved,)
        )
    )
    assert len(connection.calls) == 3
    assert connection.calls[0][1] == ("post-a",)
    assert connection.calls[2][1] == (
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
    connection = _Connection()
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
            "b" * 64,
            "c" * 64,
            "session-a",
            (ResolvedProductMention(mention, "missing", None),),
            ProductExtraction((mention,), (relation,)),
        )
    )
    assert "insert into product_project_relation" in connection.calls[-1][0]
    assert connection.calls[-1][1][0:4] == ("post-a", 0, "project-a", "used_by_project")
