"""Executable contract for the product-owned UI translation ledger."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.translation_ledger import (
    SUPPORTED_UI_LOCALES,
    TranslationCoverageError,
    build_translation_cache_key,
    require_complete_translation_map,
)


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_LOCALES = {"ko", "en", "ja", "zh", "vi", "es", "de", "fr"}


def test_translation_ledger_supports_all_product_locales() -> None:
    """The product locale contract is the required eight-language set."""
    assert set(SUPPORTED_UI_LOCALES) == EXPECTED_LOCALES


def test_cache_identity_binds_product_screen_version_and_locale() -> None:
    """A cached screen can never alias another version or locale."""
    baseline = build_translation_cache_key("lineageweave", "customer-master", 17, "ko")
    assert baseline == "ui-translation:lineageweave:customer-master:v17:ko"
    assert baseline != build_translation_cache_key("lineageweave", "customer-master", 18, "ko")
    assert baseline != build_translation_cache_key("lineageweave", "customer-master", 17, "en")
    assert baseline != build_translation_cache_key("lineageweave", "lineage-dag", 17, "ko")


def test_cache_identity_rejects_padded_product_and_screen_segments() -> None:
    """Application identity must reject spellings that PostgreSQL cannot persist."""
    for product_key, screen_key in (
        ("lineageweave ", "customer-master"),
        (" lineageweave", "customer-master"),
        ("lineageweave", "customer-master "),
        ("lineageweave", " customer-master"),
        ("lineageweave\t", "customer-master"),
        ("lineageweave", "\ncustomer-master"),
    ):
        with pytest.raises(ValueError, match="leading or trailing whitespace"):
            build_translation_cache_key(product_key, screen_key, 17, "en")


def test_translation_postgres_verification_does_not_add_psycopg2_reachability() -> None:
    """New ledger verification uses the existing asyncpg runtime boundary."""
    source = (ROOT / "tests" / "test_translation_ledger_postgres.py").read_text(encoding="utf-8")
    assert "import psycopg2" not in source
    assert "import asyncpg" in source


def test_translation_completeness_fails_closed() -> None:
    """Missing or blank UI copy must not silently fall back to another locale."""
    with pytest.raises(TranslationCoverageError, match="body"):
        require_complete_translation_map(
            ("title", "body"),
            {"title": "고객 마스터"},
            locale="ko",
        )
    with pytest.raises(TranslationCoverageError, match="body"):
        require_complete_translation_map(
            ("title", "body"),
            {"title": "Customer master", "body": "  "},
            locale="en",
        )


def test_translation_completeness_returns_only_requested_screen_keys() -> None:
    """The read model returns an exact, complete screen-key projection."""
    assert require_complete_translation_map(
        ("title", "empty-state"),
        {"title": "Customer master", "empty-state": "No customers", "other": "ignore"},
        locale="en",
    ) == {"title": "Customer master", "empty-state": "No customers"}


def test_migration_normalizes_versioned_resources_and_expands_member_locale() -> None:
    """PostgreSQL owns versioned resources while member locale accepts all eight values."""
    sql = (ROOT / "migrations" / "0246_ui_translation_ledger.sql").read_text(encoding="utf-8").lower()
    for table in ("ui_translation_resource", "ui_translation_key", "ui_translation_text"):
        assert f"create table {table}" in sql or f"create table if not exists {table}" in sql
    assert "unique (product_key, screen_key, resource_version)" in sql
    assert "unique (resource_id, translation_key, locale)" in sql
    assert "btrim(product_key) = product_key" in sql
    assert "btrim(screen_key) = screen_key" in sql
    assert "btrim(translation_key) = translation_key" in sql
    assert r"product_key !~ e'^\\s|\\s$'" in sql
    assert r"screen_key !~ e'^\\s|\\s$'" in sql
    assert r"translation_key !~ e'^\\s|\\s$'" in sql
    assert "drop constraint if exists user_account_preferred_locale_ck" in sql
    for locale in EXPECTED_LOCALES:
        assert f"'{locale}'" in sql


def test_database_rejects_whitespace_only_translation_copy() -> None:
    """A published immutable version cannot contain copy the read model treats as blank."""
    sql = (ROOT / "migrations" / "0246_ui_translation_ledger.sql").read_text(encoding="utf-8").lower()
    text_table = sql.split("create table if not exists ui_translation_text", 1)[1]
    text_table = text_table.split("create index if not exists", 1)[0]
    assert r"translated_text !~ e'^\\s*$'" in text_table


def test_translation_resource_aggregate_identity_is_immutable_after_insert() -> None:
    """Hosted contract preserves product/screen/version identity even when PostgreSQL is unavailable."""
    sql = (ROOT / "migrations" / "0246_ui_translation_ledger.sql").read_text(encoding="utf-8").lower()
    resource_guard = sql.split("create or replace function guard_ui_translation_resource_mutation()", 1)[1]
    resource_guard = resource_guard.split("$$;", 1)[0]
    for field in ("product_key", "screen_key", "resource_version"):
        assert f"old.{field} is distinct from new.{field}" in resource_guard
    assert "identity is immutable after creation" in resource_guard


def test_child_mutations_serialize_with_publication() -> None:
    """Child writes lock the parent so completeness cannot race publication."""
    sql = (ROOT / "migrations" / "0246_ui_translation_ledger.sql").read_text(encoding="utf-8").lower()
    child_guard = sql.split("create or replace function guard_ui_translation_child_mutation()", 1)[1]
    child_guard = child_guard.split("$$;", 1)[0]
    assert "for update" in child_guard


def test_publication_timestamp_is_database_owned_and_transition_scoped() -> None:
    """Publication receipt uses statement time, never caller or transaction-start time."""
    sql = (ROOT / "migrations" / "0246_ui_translation_ledger.sql").read_text(encoding="utf-8").lower()
    resource_guard = sql.split("create or replace function guard_ui_translation_resource_mutation()", 1)[1]
    resource_guard = resource_guard.split("$$;", 1)[0]
    assert "new.published_at := statement_timestamp();" in resource_guard
    assert "coalesce(new.published_at" not in resource_guard
    assert "new.published_at := now();" not in resource_guard
