"""Regression contracts for customer identity versus source-post ownership."""

from __future__ import annotations

from pathlib import Path

import backend.app.customer_hint_ingestion as ingestion
import backend.app.post_eligibility as eligibility


def test_resolution_contract_keeps_source_ownership_separate() -> None:
    """Customer corroboration persists an association and never rebinds tenant fields."""
    source = Path(ingestion.__file__).read_text(encoding="utf-8")
    assert "update source_post" not in source.lower()
    assert "source_post_customer_resolution" in source
    assert "corporate_entity_ids" in source
    assert "process_unit_ids" in source
    assert "async with pool.acquire()" in source
    assert "asyncio.to_thread" in source


def test_customer_resolution_uses_canonical_corporate_catalog_owner() -> None:
    """Customer Master must not invent a third corporate-entity binding algorithm."""
    source = Path(ingestion.__file__).read_text(encoding="utf-8").lower()
    assert "get_or_create_corporate_entity" in source
    assert "where lower(entity_name)" not in source
    assert "insert into corporate_entity" not in source


def test_authorization_owner_exposes_scoped_capture_and_revalidation() -> None:
    """The source-post authorization owner, not Customer Master, owns scoped SQL."""
    source = Path(eligibility.__file__).read_text(encoding="utf-8")
    assert "fetch_visible_customer_hint_evidence" in source
    assert "lock_visible_customer_hint_sources" in source
    assert "corporate_entity_id::text = any($1::text[])" in source
    assert "process_unit_id::text = any($2::text[])" in source
    assert "for share" in source.lower()


def test_http_boundary_passes_explicit_account_scope() -> None:
    """The API must pass CurrentAccount scope and must not pin a DB connection itself."""
    source = (Path(__file__).resolve().parents[1] / "backend" / "app" / "main.py").read_text(
        encoding="utf-8"
    )
    start = source.index('async def resolve_customer_master_hint(')
    end = source.index('@app.get("/api/lineage")', start)
    endpoint = source[start:end]
    assert "list(account.corporate_entity_ids)" in endpoint
    assert "list(account.process_unit_ids)" in endpoint
    assert "async with pool.acquire()" not in endpoint
