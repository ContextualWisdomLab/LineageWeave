"""SQL authorization for the Milestone 2 analysis-run read projection."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg2
import pytest
from psycopg2 import sql

_ROOT = Path(__file__).resolve().parents[1]
_INITIAL_MIGRATION = _ROOT / "migrations" / "0001_initial_schema.sql"
_REGISTRY_MIGRATION = _ROOT / "migrations" / "0018_analysis_run_registry.sql"
_SEED_SCRIPT = _ROOT / "scripts" / "seed_demo_data.py"
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
                '2026-01-12T12:00:00Z', 'lineage-run-v1', %s, %s,
                '2026-01-12T12:30:00Z')
        returning analysis_run_id
        """,
        (snapshot_id, idempotency_key, account_id, "b" * 64, "c" * 40),
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
    elif scope_kind == "analysis_scope_process_unit":
        cursor.execute(
            """
            insert into analysis_run_scope
                (analysis_run_id, scope_kind_code, process_unit_id)
            values (%s, %s, %s)
            """,
            (run_id, scope_kind, process_unit_id),
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


def _visible_ids(cursor, account_id: str, entity_ids: list[str]) -> set[str]:
    """Apply the same visibility predicate the product API uses."""
    cursor.execute(
        """
        select run.analysis_run_id
        from analysis_run run
        join analysis_run_scope scope on scope.analysis_run_id = run.analysis_run_id
        where
          run.requested_by_account_id = %s
          or (
            scope.scope_kind_code = 'analysis_scope_corporate_entity'
            and scope.corporate_entity_id = any(%s::uuid[])
          )
          or (
            scope.scope_kind_code = 'analysis_scope_process_unit'
            and exists (
              select 1 from account_affiliation aff
              where aff.user_account_id = %s
                and aff.process_unit_id = scope.process_unit_id
            )
          )
          or (
            scope.scope_kind_code = 'analysis_scope_thread_group'
            and exists (
              select 1 from source_post p
              where p.thread_group_key = scope.scope_key
                and (
                  p.visibility_code = 'public'
                  or p.corporate_entity_id = any(%s::uuid[])
                )
            )
          )
        """,
        (account_id, entity_ids, account_id, entity_ids),
    )
    return {str(row[0]) for row in cursor.fetchall()}


def _ensure_post_lookups(cursor) -> None:
    """Insert the lookup codes source_post requires."""
    cursor.execute(
        """
        insert into common_lookup_value (lookup_category, lookup_code, lookup_label)
        values
            ('voc_type', 'voc', 'Voice of Customer'),
            ('post_visibility', 'public', 'Public'),
            ('post_visibility', 'private', 'Private')
        on conflict (lookup_code) do nothing
        """
    )


def _insert_post(
    cursor,
    *,
    account_id: str,
    corporate_entity_id: str,
    title: str,
    visibility_code: str,
    created_at: str,
    process_unit_id: str | None = None,
    thread_group_key: str = "",
) -> str:
    """Insert one synthetic post used to falsify the cutoff predicate."""
    cursor.execute(
        """
        insert into source_post (
            author_account_id, corporate_entity_id, process_unit_id,
            post_title, post_body, voc_type_code, visibility_code,
            thread_group_key, created_at
        )
        values (%s, %s, %s, %s, 'synthetic cutoff body', 'voc', %s, %s, %s)
        returning post_id
        """,
        (
            account_id,
            corporate_entity_id,
            process_unit_id,
            title,
            visibility_code,
            thread_group_key,
            created_at,
        ),
    )
    return str(cursor.fetchone()[0])


def _cutoff_visible_titles(
    cursor,
    *,
    scope_kind_code: str,
    corporate_entity_id: str | None,
    process_unit_id: str | None,
    scope_key: str | None,
    affiliated_entity_ids: list[str],
    knowledge_cutoff: str,
) -> set[str]:
    """Execute the same cutoff + ABAC filter fetch_visible_scope_posts uses."""
    if scope_kind_code == "analysis_scope_corporate_entity" and corporate_entity_id:
        cursor.execute(
            """
            select post_title, visibility_code, corporate_entity_id
            from source_post
            where corporate_entity_id = %s and created_at <= %s
            """,
            (corporate_entity_id, knowledge_cutoff),
        )
    elif scope_kind_code == "analysis_scope_process_unit" and process_unit_id:
        cursor.execute(
            """
            select post_title, visibility_code, corporate_entity_id
            from source_post
            where process_unit_id = %s and created_at <= %s
            """,
            (process_unit_id, knowledge_cutoff),
        )
    elif scope_kind_code == "analysis_scope_thread_group" and scope_key:
        cursor.execute(
            """
            select post_title, visibility_code, corporate_entity_id
            from source_post
            where thread_group_key = %s and created_at <= %s
            """,
            (scope_key, knowledge_cutoff),
        )
    elif scope_kind_code == "analysis_scope_all_visible":
        cursor.execute(
            """
            select post_title, visibility_code, corporate_entity_id
            from source_post
            where created_at <= %s
            """,
            (knowledge_cutoff,),
        )
    else:
        return set()
    affiliated = {str(entity_id) for entity_id in affiliated_entity_ids}
    titles: set[str] = set()
    for title, visibility_code, entity_id in cursor.fetchall():
        if visibility_code == "public" or str(entity_id) in affiliated:
            titles.add(title)
    return titles


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


def test_seed_stamps_demo_posts_relative_to_run_cutoff() -> None:
    """make seed must not hide Demo public post behind default created_at=now()."""
    seed = _SEED_SCRIPT.read_text(encoding="utf-8")
    assert "2026-01-12T12:00:00Z" in seed
    assert "demo_post_created_at = \"2026-01-10T09:00:00Z\"" in seed
    assert "late_demo_post_created_at = \"2026-01-13T09:00:00Z\"" in seed
    assert "Late Demo public post" in seed
    assert "select 1 from analysis_source_count" in seed
    assert "if cur.fetchone() is None:" in seed


def test_cutoff_hides_later_posts_on_every_scope(authz_db) -> None:
    """A post after knowledge_cutoff is absent; equal-to-cutoff remains."""
    cutoff = "2026-01-12T12:00:00Z"
    with authz_db.cursor() as cursor:
        _ensure_post_lookups(cursor)
        author = _insert_account(cursor, "author")
        own_corp = _insert_corp(cursor, "DEMO-CORP-CUTOFF", "Demo Corp")
        other_corp = _insert_corp(cursor, "OTHER-CORP-CUTOFF", "Other Corp")
        cursor.execute(
            """
            insert into process_unit
                (corporate_entity_id, process_unit_code, process_unit_name)
            values (%s, 'DEMO-PU-CUTOFF', 'Demo cutoff unit')
            returning process_unit_id
            """,
            (own_corp,),
        )
        process_unit_id = str(cursor.fetchone()[0])
        _insert_post(
            cursor,
            account_id=author,
            corporate_entity_id=own_corp,
            title="In-cutoff own-corp",
            visibility_code="private",
            created_at="2026-01-10T09:00:00Z",
            process_unit_id=process_unit_id,
            thread_group_key="cutoff-thread",
        )
        _insert_post(
            cursor,
            account_id=author,
            corporate_entity_id=own_corp,
            title="Equal-to-cutoff own-corp",
            visibility_code="private",
            created_at=cutoff,
            process_unit_id=process_unit_id,
            thread_group_key="cutoff-thread",
        )
        _insert_post(
            cursor,
            account_id=author,
            corporate_entity_id=own_corp,
            title="Late own-corp",
            visibility_code="private",
            created_at="2026-01-12T12:00:01Z",
            process_unit_id=process_unit_id,
            thread_group_key="cutoff-thread",
        )
        _insert_post(
            cursor,
            account_id=author,
            corporate_entity_id=other_corp,
            title="Other-corp private",
            visibility_code="private",
            created_at="2026-01-10T09:00:00Z",
            thread_group_key="cutoff-thread",
        )
        _insert_post(
            cursor,
            account_id=author,
            corporate_entity_id=other_corp,
            title="Other-corp public",
            visibility_code="public",
            created_at="2026-01-10T09:00:00Z",
            thread_group_key="other-thread",
        )

        expected_own = {"In-cutoff own-corp", "Equal-to-cutoff own-corp"}
        for scope_kind, corp_id, unit_id, scope_key in (
            ("analysis_scope_corporate_entity", own_corp, None, None),
            ("analysis_scope_process_unit", None, process_unit_id, None),
            ("analysis_scope_thread_group", None, None, "cutoff-thread"),
        ):
            titles = _cutoff_visible_titles(
                cursor,
                scope_kind_code=scope_kind,
                corporate_entity_id=corp_id,
                process_unit_id=unit_id,
                scope_key=scope_key,
                affiliated_entity_ids=[own_corp],
                knowledge_cutoff=cutoff,
            )
            assert titles == expected_own, scope_kind
            assert "Late own-corp" not in titles
            assert "Other-corp private" not in titles

        all_visible = _cutoff_visible_titles(
            cursor,
            scope_kind_code="analysis_scope_all_visible",
            corporate_entity_id=None,
            process_unit_id=None,
            scope_key=None,
            affiliated_entity_ids=[own_corp],
            knowledge_cutoff=cutoff,
        )
        assert all_visible == expected_own | {"Other-corp public"}
        assert "Late own-corp" not in all_visible
        assert "Other-corp private" not in all_visible


def test_thread_group_run_is_visible_only_when_a_post_is_already_visible(
    authz_db,
) -> None:
    """A thread-group run follows the same ABAC gate as a post in that group."""
    with authz_db.cursor() as cursor:
        _ensure_post_lookups(cursor)
        viewer = _insert_account(cursor, "thread-viewer")
        outsider = _insert_account(cursor, "thread-outsider")
        own_corp = _insert_corp(cursor, "DEMO-CORP-THREAD", "Demo Corp")
        other_corp = _insert_corp(cursor, "OTHER-CORP-THREAD", "Other Corp")
        cursor.execute(
            """
            insert into account_affiliation (user_account_id, corporate_entity_id)
            values (%s, %s)
            """,
            (viewer, own_corp),
        )
        _insert_post(
            cursor,
            account_id=outsider,
            corporate_entity_id=other_corp,
            title="Public thread post",
            visibility_code="public",
            created_at="2026-01-10T09:00:00Z",
            thread_group_key="shared-thread",
        )
        _insert_post(
            cursor,
            account_id=outsider,
            corporate_entity_id=other_corp,
            title="Private other-corp thread post",
            visibility_code="private",
            created_at="2026-01-10T09:00:00Z",
            thread_group_key="hidden-thread",
        )
        shared_run = _complete_run(
            cursor,
            account_id=outsider,
            digest="1" * 64,
            idempotency_key="shared-thread-run",
            scope_kind="analysis_scope_thread_group",
            scope_key="shared-thread",
        )
        hidden_run = _complete_run(
            cursor,
            account_id=outsider,
            digest="2" * 64,
            idempotency_key="hidden-thread-run",
            scope_kind="analysis_scope_thread_group",
            scope_key="hidden-thread",
        )
        visible = _visible_ids(cursor, viewer, [own_corp])
        assert shared_run in visible
        assert hidden_run not in visible
