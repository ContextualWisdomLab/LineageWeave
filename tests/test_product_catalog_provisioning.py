"""Synthetic tests for governed product-catalog provisioning."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

import pytest

from backend.app.product_catalog_provisioning import (
    ProductCatalogImport,
    ProductCatalogParentMissing,
    ProductCatalogProvisioningConflict,
    provision_product_catalog_entry,
)


_PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000101")


class _Connection:
    """Return one configurable catalog/source state and retain writes."""

    def __init__(self) -> None:
        self.source_row = None
        self.catalog_row = None
        self.parent_row = {"product_catalog_id": UUID(int=102)}
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    @asynccontextmanager
    async def transaction(self):
        """Provide the async transaction shape used by asyncpg."""
        yield

    async def fetchrow(self, query: str, *args: object):
        """Return rows by the exact normalized table queried."""
        self.calls.append((query, args))
        if "from product_catalog_source_record source" in query:
            return self.source_row
        if "where product_catalog_code = $1" in query and "for update" not in query:
            return self.parent_row
        if "where product_catalog_code = $1 for update" in query:
            return self.catalog_row
        if "insert into product_catalog " in query:
            return {
                "product_catalog_id": _PRODUCT_ID,
                "canonical_product_name": args[0],
                "product_level_code": args[1],
                "parent_product_catalog_id": args[2],
            }
        raise AssertionError(query)

    async def execute(self, query: str, *args: object) -> str:
        """Retain parameterized writes without a database dependency."""
        self.calls.append((query, args))
        return "INSERT 0 1"


def _entry(**changes: object) -> ProductCatalogImport:
    values = {
        "product_code": "SYNTHETIC-MODEL-Q",
        "preferred_label": "Synthetic Model Q",
        "product_level_code": "product_model",
        "parent_product_code": "SYNTHETIC-GROUP",
        "aliases": ("Model Q",),
        "corporate_entity_id": "00000000-0000-0000-0000-000000000201",
        "source_system_code": "synthetic_product_master",
        "source_record_key": "synthetic-record-1",
    }
    values.update(changes)
    return ProductCatalogImport(**values)  # type: ignore[arg-type]


def test_catalog_provisioning_persists_explicit_source_and_alias_evidence() -> None:
    """One source row creates one product plus preferred/explicit aliases."""
    conn = _Connection()
    result = asyncio.run(
        provision_product_catalog_entry(
            conn,
            _entry(),
            imported_by_account_id="00000000-0000-0000-0000-000000000301",
        )
    )

    assert result["created"] is True
    assert len(result["source_payload_sha256"]) == 64
    writes = [query for query, _args in conn.calls]
    assert sum("pg_advisory_xact_lock" in query for query in writes) == 2
    assert any("insert into product_catalog_source_record" in query for query in writes)
    assert sum("insert into product_catalog_alias " in query for query in writes) == 2
    assert sum("insert into product_catalog_alias_source" in query for query in writes) == 2


def test_catalog_provisioning_replay_is_idempotent() -> None:
    """The same governed source digest performs no second write."""
    entry = _entry()
    conn = _Connection()
    conn.source_row = {
        "product_catalog_id": _PRODUCT_ID,
        "product_catalog_code": entry.product_code,
        "source_payload_sha256": entry.source_payload_sha256(),
    }

    result = asyncio.run(
        provision_product_catalog_entry(conn, entry, imported_by_account_id=str(UUID(int=301)))
    )

    assert result == {
        "product_catalog_id": str(_PRODUCT_ID),
        "source_payload_sha256": entry.source_payload_sha256(),
        "created": False,
    }
    assert sum("pg_advisory_xact_lock" in query for query, _args in conn.calls) == 1
    assert not any(query.startswith("insert into") for query, _args in conn.calls)


def test_catalog_provisioning_rejects_source_or_catalog_redefinition() -> None:
    """A stable code/source key cannot silently acquire new semantics."""
    entry = _entry()
    source_conflict = _Connection()
    source_conflict.source_row = {
        "product_catalog_id": _PRODUCT_ID,
        "product_catalog_code": entry.product_code,
        "source_payload_sha256": "f" * 64,
    }
    with pytest.raises(ProductCatalogProvisioningConflict):
        asyncio.run(
            provision_product_catalog_entry(
                source_conflict, entry, imported_by_account_id=str(UUID(int=301))
            )
        )

    catalog_conflict = _Connection()
    catalog_conflict.catalog_row = {
        "product_catalog_id": _PRODUCT_ID,
        "canonical_product_name": "Different Product",
        "product_level_code": entry.product_level_code,
        "parent_product_catalog_id": UUID(int=102),
    }
    with pytest.raises(ProductCatalogProvisioningConflict):
        asyncio.run(
            provision_product_catalog_entry(
                catalog_conflict, entry, imported_by_account_id=str(UUID(int=301))
            )
        )


def test_catalog_provisioning_requires_parent_and_unambiguous_aliases() -> None:
    """Missing hierarchy and colliding explicit alias rows fail closed."""
    missing_parent = _Connection()
    missing_parent.parent_row = None
    with pytest.raises(ProductCatalogParentMissing):
        asyncio.run(
            provision_product_catalog_entry(
                missing_parent, _entry(), imported_by_account_id=str(UUID(int=301))
            )
        )
    with pytest.raises(ValueError, match="normalize"):
        _entry(aliases=("Model  Q", "model q")).normalized_aliases()


def test_catalog_provenance_schema_is_replay_safe_normalized_and_indexed() -> None:
    """The migration preserves source aliases and both lookup directions."""
    sql = Path("migrations/0261_product_catalog_source_provenance.sql").read_text()
    assert "create table if not exists product_catalog_source_record" in sql
    assert "create table if not exists product_catalog_alias_source" in sql
    assert "source_alias_text text not null" in sql
    assert "source_payload_sha256" in sql
    assert "primary key (corporate_entity_id, source_system_code, source_record_key)" in sql
    assert "product_catalog_source_record_product_idx" in sql
    assert "product_catalog_alias_source_record_idx" in sql
