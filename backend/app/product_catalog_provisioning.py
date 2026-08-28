"""Provision product identities only from explicit governed source records."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

from lineageweave.product_semantics import normalize_product_alias


_PRODUCT_LEVEL_CODES = frozenset(
    {"product_group", "product_model", "variant", "trade_item"}
)


class ProductCatalogProvisioningConflict(ValueError):
    """An existing source or product identity contradicts the import row."""


class ProductCatalogParentMissing(ValueError):
    """The explicitly named parent product does not exist."""


@dataclass(frozen=True)
class ProductCatalogImport:
    """One explicit product-master row and its source provenance."""

    product_code: str
    preferred_label: str
    product_level_code: str
    parent_product_code: str | None
    aliases: tuple[str, ...]
    corporate_entity_id: str
    source_system_code: str
    source_record_key: str

    def normalized_aliases(self) -> tuple[tuple[str, str], ...]:
        """Return unique explicit aliases, including the preferred label."""
        values: dict[str, str] = {}
        for alias in (self.preferred_label, *self.aliases):
            if "\x00" in alias:
                raise ValueError("product aliases must be valid PostgreSQL text")
            normalized = normalize_product_alias(alias)
            if not normalized:
                raise ValueError("product aliases must not be blank")
            prior = values.get(normalized)
            if prior is not None and prior != alias.strip():
                raise ValueError("two aliases normalize to the same catalog key")
            values[normalized] = alias.strip()
        return tuple(sorted(values.items()))

    def source_payload_sha256(self) -> str:
        """Digest the canonical row persisted by the import contract."""
        payload = {
            "aliases": self.normalized_aliases(),
            "corporate_entity_id": self.corporate_entity_id,
            "parent_product_code": (
                self.parent_product_code.strip()
                if self.parent_product_code is not None
                else None
            ),
            "preferred_label": self.preferred_label.strip(),
            "product_code": self.product_code.strip(),
            "product_level_code": self.product_level_code,
            "source_record_key": self.source_record_key.strip(),
            "source_system_code": self.source_system_code,
        }
        encoded = json.dumps(
            payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class _Connection(Protocol):
    def transaction(self) -> Any:
        """Open an atomic database transaction."""
        ...

    async def fetchrow(self, query: str, *args: object) -> Any:
        """Fetch one row."""
        ...

    async def execute(self, query: str, *args: object) -> Any:
        """Execute one parameterized statement."""
        ...


async def provision_product_catalog_entry(
    conn: _Connection,
    entry: ProductCatalogImport,
    *,
    imported_by_account_id: str,
) -> dict[str, object]:
    """Add one immutable source-bound product definition idempotently."""
    for name, value in (
        ("product code", entry.product_code),
        ("preferred label", entry.preferred_label),
        ("source record key", entry.source_record_key),
    ):
        if not value.strip() or "\x00" in value:
            raise ValueError(f"{name} must be nonblank PostgreSQL text")
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", entry.source_system_code):
        raise ValueError("source system code is outside the governed vocabulary")
    if entry.product_level_code not in _PRODUCT_LEVEL_CODES:
        raise ValueError("product level code is outside the governed vocabulary")
    if entry.parent_product_code is not None:
        if not entry.parent_product_code.strip() or "\x00" in entry.parent_product_code:
            raise ValueError("parent product code must be valid nonblank PostgreSQL text")
    aliases = entry.normalized_aliases()
    digest = entry.source_payload_sha256()
    async with conn.transaction():
        # Serialize this composite source key before reading it. PostgreSQL's
        # 64-bit hash can only add harmless contention on a collision; the
        # three-column primary key remains the identity and integrity owner.
        await conn.execute(
            "select pg_advisory_xact_lock(hashtextextended("
            "jsonb_build_array($1::text, $2::text, $3::text)::text, 0))",
            entry.corporate_entity_id,
            entry.source_system_code,
            entry.source_record_key.strip(),
        )
        source_row = await conn.fetchrow(
            "select source.product_catalog_id, source.source_payload_sha256, "
            "catalog.product_catalog_code from product_catalog_source_record source "
            "join product_catalog catalog on catalog.product_catalog_id = source.product_catalog_id "
            "where source.corporate_entity_id = $1::uuid and source.source_system_code = $2 "
            "and source.source_record_key = $3 for update of source",
            entry.corporate_entity_id,
            entry.source_system_code,
            entry.source_record_key.strip(),
        )
        if source_row is not None:
            if (
                source_row["product_catalog_code"] != entry.product_code.strip()
                or source_row["source_payload_sha256"] != digest
            ):
                raise ProductCatalogProvisioningConflict(
                    "the governed source record already has a different product definition"
                )
            return {
                "product_catalog_id": str(source_row["product_catalog_id"]),
                "source_payload_sha256": digest,
                "created": False,
            }

        # Serialize first-time definitions of the same explicit product code.
        # The source lock above protects replay, while this lock prevents two
        # different source records from racing the catalog's unique code.
        await conn.execute(
            "select pg_advisory_xact_lock(hashtextextended($1, 0))",
            entry.product_code.strip(),
        )

        parent_id = None
        if entry.parent_product_code is not None:
            parent = await conn.fetchrow(
                "select product_catalog_id from product_catalog "
                "where product_catalog_code = $1",
                entry.parent_product_code.strip(),
            )
            if parent is None:
                raise ProductCatalogParentMissing("parent product code is not provisioned")
            parent_id = parent["product_catalog_id"]

        catalog = await conn.fetchrow(
            "select product_catalog_id, canonical_product_name, product_level_code, "
            "parent_product_catalog_id from product_catalog "
            "where product_catalog_code = $1 for update",
            entry.product_code.strip(),
        )
        if catalog is None:
            catalog = await conn.fetchrow(
                "insert into product_catalog "
                "(canonical_product_name, product_level_code, parent_product_catalog_id, product_catalog_code) "
                "values ($1, $2, $3, $4) returning product_catalog_id, "
                "canonical_product_name, product_level_code, parent_product_catalog_id",
                entry.preferred_label.strip(),
                entry.product_level_code,
                parent_id,
                entry.product_code.strip(),
            )
        elif (
            catalog["canonical_product_name"] != entry.preferred_label.strip()
            or catalog["product_level_code"] != entry.product_level_code
            or catalog["parent_product_catalog_id"] != parent_id
        ):
            raise ProductCatalogProvisioningConflict(
                "the product code already has a different governed definition"
            )
        product_id = catalog["product_catalog_id"]
        await conn.execute(
            "insert into product_catalog_source_record "
            "(corporate_entity_id, source_system_code, source_record_key, "
            "product_catalog_id, source_payload_sha256, preferred_label_text, "
            "imported_by_account_id) values ($1::uuid, $2, $3, $4, $5, $6, $7::uuid)",
            entry.corporate_entity_id,
            entry.source_system_code,
            entry.source_record_key.strip(),
            product_id,
            digest,
            entry.preferred_label.strip(),
            imported_by_account_id,
        )
        for normalized, alias in aliases:
            await conn.execute(
                "insert into product_catalog_alias "
                "(product_catalog_id, normalized_alias_text, alias_text) "
                "values ($1, $2, $3) on conflict (product_catalog_id, normalized_alias_text) "
                "do nothing",
                product_id,
                normalized,
                alias,
            )
            await conn.execute(
                "insert into product_catalog_alias_source "
                "(product_catalog_id, normalized_alias_text, source_alias_text, "
                "corporate_entity_id, source_system_code, source_record_key) "
                "values ($1, $2, $3, $4::uuid, $5, $6) "
                "on conflict do nothing",
                product_id,
                normalized,
                alias,
                entry.corporate_entity_id,
                entry.source_system_code,
                entry.source_record_key.strip(),
            )
    return {
        "product_catalog_id": str(product_id),
        "source_payload_sha256": digest,
        "created": True,
    }
