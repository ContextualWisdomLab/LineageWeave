"""SQL authorization for the Milestone 2 analysis-run read projection."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg2
import pytest
from psycopg2 import sql

from backend.app.analysis_run_ingestion import _VISIBLE_RUN_SQL

_ROOT = Path(__file__).resolve().parents[1]
_INITIAL_MIGRATION = _ROOT / "migrations" / "0001_initial_schema.sql"
_REGISTRY_MIGRATION = _ROOT / "migrations" / "0018_analysis_run_registry.sql"
_RETENTION_MIGRATION = _ROOT / "migrations" / "0020_analysis_run_retention_purge.sql"
_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)


def _postgres_available() -> bool:
    """Return whether the configured administrator DSN is reachable."""
    try:
        psycopg2.connect(_ADMIN_DSN, connect_timeout=2).close()
        return True
    except psycopg2.OperationalError:
        return False


def _database_dsn(database_name: str) -> str:
    """Replace only the database path while preserving DSN query options."""
    parsed = urlsplit(_ADMIN_DSN)
    return urlunsplit(parsed._replace(path=f"/{database_name}"))


@pytest.fixture
def authz_db():
    """Yield a throwaway database migrated through the registry schema."""
    if not _postgres_available():
        pytest.skip("a reachable PostgreSQL administrator DSN is required")
    database_name = f"lineageweave_authz_{uuid.uuid4().hex[:12]}"
    admin_connection = psycopg2.connect(_ADMIN_DSN)
    admin_connection.autocommit = True
    with admin_connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("create database {}").format(sql.Identifier(database_name))
        )
    try:
        connection = psycopg2.connect(_database_dsn(database_name))
        try:
            connection.autocommit = True
            with connection.cursor() as cursor:
                cursor.execute(_INITIAL_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_REGISTRY_MIGRATION.read_text(encoding="utf-8"))
                cursor.execute(_RETENTION_MIGRATION.read_text(encoding="utf-8"))
            yield connection
        finally:
            connection.close()
    finally:
        with admin_connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("drop database {}").format(sql.Identifier(database_name))
            )
        admin_connection.close()


def _insert_account(cursor, label: str) -> str:
    """Insert one synthetic authenticated account and return its UUID."""
    suffix = uuid.uuid4().hex
    cursor.execute(
        """
        insert into user_account
            (external_subject_id, display_name, email_address)
        values (%s, %s, %s)
        returning user_account_id
        """,
        (f"{label}-{suffix}", f"{label.title()} User", f"{label}-{suffix}@example.test"),
    )
    return str(cursor.fetchone()[0])


def _insert_corp(cursor, code: str, name: str) -> str:
    """Insert one synthetic corporate entity."""
    cursor.execute(
        """
        insert into common_lookup_value (lookup_category, lookup_code, lookup_label)
        values ('corporate_entity_level', 'company', 'Company')
        on conflict (lookup_code) do nothing
        """
    )
    cursor.execute(
        """
        insert into corporate_entity (corporate_entity_code, entity_name, entity_level_code)
        values (%s, %s, 'company')
        returning corporate_entity_id
        """,
        (code, name),
    )
    return str(cursor.fetchone()[0])


def _insert_process_unit(
    cursor, corporate_entity_id: str, code: str, name: str
) -> str:
    """Insert one synthetic process unit under a corporate entity."""
    cursor.execute(
        """
        insert into process_unit
            (corporate_entity_id, process_unit_code, process_unit_name)
        values (%s, %s, %s)
        returning process_unit_id
        """,
        (corporate_entity_id, code, name),
    )
    return str(cursor.fetchone()[0])


def _ensure_post_lookups(cursor) -> None:
    """Insert the visibility and VOC codes the cutoff fixtures need."""
    cursor.execute(
        """
        insert into common_lookup_value
            (lookup_category, lookup_code, lookup_label)
        values
            ('post_visibility', 'public', 'Public'),
            ('post_visibility', 'private', 'Private'),
            ('voc_type', 'voc', 'Voice of Customer')
        on conflict (lookup_code) do nothing
        """
    )


def _complete_run(
    cursor,
    *,
    account_id: str,
    digest: str,
    idempotency_key: str,
    scope_kind: str,
    corporate_entity_id: str | None = None,
    process_unit_id: str | None = None,
    scope_key: str | None = None,
    knowledge_cutoff: str = "2026-01-12T12:00:00Z",
) -> str:
    """Insert one succeeded run with one document-count aggregate."""
    cursor.execute(
        """
        insert into analysis_source_snapshot
            (snapshot_sha256, source_contract_version,
             maximum_available_time, captured_at)
        values (%s, 'source-contract-v1',
                '2026-01-12T00:00:00Z', '2026-01-12T00:05:00Z')
        returning analysis_source_snapshot_id
        """,
        (digest,),
    )
    snapshot_id = cursor.fetchone()[0]
    cursor.execute(
        """
        insert into analysis_source_count
            (analysis_source_snapshot_id, count_type_code, count_value)
        values (%s, 'analysis_count_document', 3)
        """,
        (snapshot_id,),
    )
    cursor.execute(
        """
        insert into analysis_run
            (analysis_source_snapshot_id, run_kind_code, idempotency_key,
             requested_by_account_id, knowledge_cutoff,
             configuration_schema_version, configuration_sha256,
             code_revision_sha, requested_at)
        values (%s, 'analysis_run_lineage', %s, %s,
                %s, 'lineage-run-v1', %s, %s,
                '2026-01-12T12:30:00Z')
        returning analysis_run_id
        """,
        (
            snapshot_id,
            idempotency_key,
            account_id,
            knowledge_cutoff,
            "b" * 64,
            "c" * 40,
        ),
    )
    run_id = str(cursor.fetchone()[0])
    if scope_kind == "analysis_scope_corporate_entity":
        cursor.execute(
            """
            insert into analysis_run_scope
                (analysis_run_id, scope_kind_code, corporate_entity_id)
            values (%s, %s, %s)
            """,
            (run_id, scope_kind, corporate_entity_id),
        )
    elif scope_kind == "analysis_scope_thread_group":
        cursor.execute(
            """
            insert into analysis_run_scope
                (analysis_run_id, scope_kind_code, scope_key)
            values (%s, %s, %s)
            """,
            (run_id, scope_kind, scope_key),
        )
    elif scope_kind == "analysis_scope_process_unit":
        cursor.execute(
            """
            insert into analysis_run_scope
                (analysis_run_id, scope_kind_code, process_unit_id)
            values (%s, %s, %s)
            """,
            (run_id, scope_kind, process_unit_id),
        )
    else:
        cursor.execute(
            """
            insert into analysis_run_scope
                (analysis_run_id, scope_kind_code)
            values (%s, %s)
            """,
            (run_id, scope_kind),
        )
    for ordinal, status, occurred in (
        (1, "analysis_status_pending", "2026-01-12T12:31:00Z"),
        (2, "analysis_status_running", "2026-01-12T12:32:00Z"),
        (3, "analysis_status_succeeded", "2026-01-12T12:33:00Z"),
    ):
        cursor.execute(
            """
            insert into analysis_run_status_event
                (analysis_run_id, status_ordinal, status_code, occurred_at)
            values (%s, %s, %s, %s)
            """,
            (run_id, ordinal, status, occurred),
        )
    return run_id


def _product_visibility_predicate() -> str:
    """Translate asyncpg ``$1``/``$2`` reuse into psycopg2 named placeholders.

    The product SQL binds the account once as ``$1`` and affiliated
    entity ids once as ``$2``, then reuses both. Positional ``%s``
    cannot do that: interpolating the cutoff fragment twice yields
    five placeholders and only two arguments.
    """
    return (
        _VISIBLE_RUN_SQL.replace("$2::uuid[]", "%(entity_ids)s::uuid[]").replace(
            "$1", "%(account_id)s"
        )
    )


def _visible_ids(cursor, account_id: str, entity_ids: list[str]) -> set[str]:
    """Apply the same visibility predicate the product API uses."""
    cursor.execute(
        f"""
        select run.analysis_run_id
        from analysis_run run
        join analysis_run_scope scope on scope.analysis_run_id = run.analysis_run_id
        where {_product_visibility_predicate()}
        """,
        {"account_id": account_id, "entity_ids": entity_ids},
    )
    return {str(row[0]) for row in cursor.fetchall()}


def test_visible_ids_helper_reuses_named_account_and_entity_binds() -> None:
    """asyncpg $1/$2 reuse must not become positional %s."""

    predicate = _product_visibility_predicate()
    leftover = (
        predicate.replace("%(account_id)s", "").replace("%(entity_ids)s", "")
    )
    assert "%(account_id)s" in predicate
    assert "%(entity_ids)s::uuid[]" in predicate
    assert "%s" not in leftover
    assert predicate.count("%(account_id)s") == 2
    assert predicate.count("%(entity_ids)s") == 3


def test_requester_ownership_cannot_bypass_thread_group_cutoff() -> None:
    """ADR 0018: requester ownership stays inside the first conjunct."""

    sql = " ".join(_VISIBLE_RUN_SQL.split())
    ownership = "run.requested_by_account_id = $1"
    first, separator, second = sql.partition(") and (")
    assert ownership in sql
    assert "p.created_at <= run.knowledge_cutoff" in sql
    assert separator
    assert ownership in first
    assert ownership not in second
    assert "scope.scope_kind_code <> 'analysis_scope_thread_group'" in second
    assert "p.created_at <= run.knowledge_cutoff" in second


def test_hidden_scope_does_not_leak_through_all_visible_or_other_corp(authz_db) -> None:
    """A Demo-Corp viewer never sees another tenant's run or its aggregates."""
    with authz_db.cursor() as cursor:
        viewer = _insert_account(cursor, "viewer")
        outsider = _insert_account(cursor, "outsider")
        own_corp = _insert_corp(cursor, "DEMO-CORP-AUTHZ", "Demo Corp")
        other_corp = _insert_corp(cursor, "OTHER-CORP-AUTHZ", "Other Corp")
        cursor.execute(
            """
            insert into account_affiliation (user_account_id, corporate_entity_id)
            values (%s, %s)
            """,
            (viewer, own_corp),
        )
        own_run = _complete_run(
            cursor,
            account_id=viewer,
            digest="a" * 64,
            idempotency_key="own-corp",
            scope_kind="analysis_scope_corporate_entity",
            corporate_entity_id=own_corp,
        )
        hidden_all_visible = _complete_run(
            cursor,
            account_id=outsider,
            digest="d" * 64,
            idempotency_key="hidden-all",
            scope_kind="analysis_scope_all_visible",
        )
        hidden_other_corp = _complete_run(
            cursor,
            account_id=outsider,
            digest="e" * 64,
            idempotency_key="hidden-other",
            scope_kind="analysis_scope_corporate_entity",
            corporate_entity_id=other_corp,
        )

        visible = _visible_ids(cursor, viewer, [own_corp])
        assert own_run in visible
        assert hidden_all_visible not in visible
        assert hidden_other_corp not in visible

        outsider_visible = _visible_ids(cursor, outsider, [other_corp])
        assert hidden_all_visible in outsider_visible
        assert hidden_other_corp in outsider_visible
        assert own_run not in outsider_visible


def test_requester_owned_thread_group_run_needs_in_cutoff_post(authz_db) -> None:
    """A January thread-group run you requested stays hidden without an in-cutoff post."""

    with authz_db.cursor() as cursor:
        viewer = _insert_account(cursor, "requester")
        own_corp = _insert_corp(cursor, "DEMO-CORP-CUTOFF", "Demo Corp")
        _ensure_post_lookups(cursor)
        cursor.execute(
            """
            insert into account_affiliation (user_account_id, corporate_entity_id)
            values (%s, %s)
            """,
            (viewer, own_corp),
        )
        cursor.execute(
            """
            insert into source_post
                (author_account_id, corporate_entity_id, post_title, post_body,
                 voc_type_code, visibility_code, thread_group_key, created_at)
            values
                (%s, %s, 'Late own thread', 'Written after the January cutoff.',
                 'voc', 'public', 'late-own-thread', '2026-01-20T12:00:00Z'),
                (%s, %s, 'In-cutoff own thread', 'Visible at the January cutoff.',
                 'voc', 'public', 'in-cutoff-own-thread', '2026-01-10T12:00:00Z')
            """,
            (viewer, own_corp, viewer, own_corp),
        )
        hidden_own = _complete_run(
            cursor,
            account_id=viewer,
            digest="1" * 64,
            idempotency_key="own-late-thread",
            scope_kind="analysis_scope_thread_group",
            scope_key="late-own-thread",
        )
        visible_own = _complete_run(
            cursor,
            account_id=viewer,
            digest="2" * 64,
            idempotency_key="own-in-cutoff-thread",
            scope_kind="analysis_scope_thread_group",
            scope_key="in-cutoff-own-thread",
        )
        visible = _visible_ids(cursor, viewer, [own_corp])
        assert hidden_own not in visible
        assert visible_own in visible


def test_thread_group_cutoff_honors_private_and_empty_affiliation(authz_db) -> None:
    """Private own-corp in-cutoff lists; other-corp private and empty $2 do not."""

    with authz_db.cursor() as cursor:
        viewer = _insert_account(cursor, "private-viewer")
        other = _insert_account(cursor, "other-author")
        own_corp = _insert_corp(cursor, "DEMO-CORP-PRIVATE", "Demo Corp")
        other_corp = _insert_corp(cursor, "OTHER-CORP-PRIVATE", "Other Corp")
        _ensure_post_lookups(cursor)
        cursor.execute(
            """
            insert into account_affiliation (user_account_id, corporate_entity_id)
            values (%s, %s)
            """,
            (viewer, own_corp),
        )
        cursor.execute(
            """
            insert into source_post
                (author_account_id, corporate_entity_id, post_title, post_body,
                 voc_type_code, visibility_code, thread_group_key, created_at)
            values
                (%s, %s, 'Private own thread', 'Visible only to Demo Corp.',
                 'voc', 'private', 'private-own-thread', '2026-01-10T12:00:00Z'),
                (%s, %s, 'Private other thread', 'Other corp only.',
                 'voc', 'private', 'private-other-thread', '2026-01-10T12:00:00Z'),
                (%s, %s, 'Public empty-aff thread', 'Public in-cutoff post.',
                 'voc', 'public', 'public-empty-aff-thread', '2026-01-10T12:00:00Z')
            """,
            (viewer, own_corp, other, other_corp, viewer, own_corp),
        )
        private_own = _complete_run(
            cursor,
            account_id=viewer,
            digest="3" * 64,
            idempotency_key="private-own-thread",
            scope_kind="analysis_scope_thread_group",
            scope_key="private-own-thread",
        )
        private_other = _complete_run(
            cursor,
            account_id=viewer,
            digest="4" * 64,
            idempotency_key="private-other-thread",
            scope_kind="analysis_scope_thread_group",
            scope_key="private-other-thread",
        )
        public_empty = _complete_run(
            cursor,
            account_id=viewer,
            digest="5" * 64,
            idempotency_key="public-empty-aff-thread",
            scope_kind="analysis_scope_thread_group",
            scope_key="public-empty-aff-thread",
        )
        affiliated = _visible_ids(cursor, viewer, [own_corp])
        assert private_own in affiliated
        assert private_other not in affiliated
        assert public_empty in affiliated

        unaffiliated = _visible_ids(cursor, viewer, [])
        assert private_own not in unaffiliated
        assert private_other not in unaffiliated
        assert public_empty in unaffiliated


def test_process_unit_run_lists_without_thread_group_cutoff(authz_db) -> None:
    """A process-unit run the caller already walks is not gated by cutoff."""

    with authz_db.cursor() as cursor:
        viewer = _insert_account(cursor, "unit-viewer")
        own_corp = _insert_corp(cursor, "DEMO-CORP-UNIT", "Demo Corp")
        process_unit_id = _insert_process_unit(
            cursor, own_corp, "DEMO-PU-CUTOFF", "Demo Process Unit"
        )
        cursor.execute(
            """
            insert into account_affiliation
                (user_account_id, corporate_entity_id, process_unit_id)
            values (%s, %s, %s)
            """,
            (viewer, own_corp, process_unit_id),
        )
        unit_run = _complete_run(
            cursor,
            account_id=viewer,
            digest="6" * 64,
            idempotency_key="own-process-unit",
            scope_kind="analysis_scope_process_unit",
            process_unit_id=process_unit_id,
        )
        visible = _visible_ids(cursor, viewer, [own_corp])
        assert unit_run in visible
