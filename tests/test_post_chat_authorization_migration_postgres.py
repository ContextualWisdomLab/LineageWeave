"""PostgreSQL evidence for Post Chat replay authorization migration 0249."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2")

_POSTGRES_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN",
    "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave",
)
_FORWARD_MIGRATION = Path("migrations/0249_post_chat_authorization_scope.sql")
_ROLLBACK_MIGRATION = Path("migrations/rollback/0249_post_chat_authorization_scope.sql")


@pytest.fixture
def isolated_postgres_schema():
    """Yield a disposable schema or skip when the repository PostgreSQL service is absent."""
    try:
        conn = psycopg2.connect(_POSTGRES_DSN)
    except psycopg2.OperationalError:
        pytest.skip("repository PostgreSQL service is not reachable")

    conn.autocommit = True
    schema_name = f"post_chat_replay_{uuid.uuid4().hex}"
    with conn.cursor() as cursor:
        cursor.execute(f'create schema "{schema_name}"')
        cursor.execute(f'set search_path to "{schema_name}"')
    try:
        yield conn
    finally:
        with conn.cursor() as cursor:
            cursor.execute("set search_path to public")
            cursor.execute(f'drop schema if exists "{schema_name}" cascade')
        conn.close()


def _create_minimal_parent_schema(conn) -> None:
    """Create only the parent relations migration 0249 requires for lifecycle proof."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            create table corporate_entity (
                corporate_entity_id uuid primary key
            );
            create table process_unit (
                process_unit_id uuid primary key
            );
            create table source_post (
                post_id uuid primary key
            );
            create table post_chat_result (
                post_id uuid not null references source_post(post_id) on delete cascade,
                question_norm text not null,
                question_text text not null,
                answer_text text not null,
                primary key (post_id, question_norm)
            );
            """
        )


def test_deleting_contributing_source_atomically_invalidates_parent_answer(
    isolated_postgres_schema,
) -> None:
    """A non-focal source deletion must remove the derived answer and its receipt."""
    conn = isolated_postgres_schema
    _create_minimal_parent_schema(conn)
    with conn.cursor() as cursor:
        cursor.execute(_FORWARD_MIGRATION.read_text())
        focal_post_id = str(uuid.uuid4())
        contributing_post_id = str(uuid.uuid4())
        cursor.execute(
            "insert into source_post (post_id) values (%s), (%s)",
            (str(focal_post_id), str(contributing_post_id)),
        )
        cursor.execute(
            "insert into post_chat_result "
            "(post_id, question_norm, question_text, answer_text) values (%s, %s, %s, %s)",
            (str(focal_post_id), "what happened?", "What happened?", "Derived answer"),
        )
        cursor.execute(
            "insert into post_chat_authorization_receipt "
            "(post_id, question_norm, process_scope_limited) values (%s, %s, false)",
            (str(focal_post_id), "what happened?"),
        )
        cursor.execute(
            "insert into post_chat_source "
            "(post_id, question_norm, source_ordinal, source_post_id) values (%s, %s, 0, %s)",
            (str(focal_post_id), "what happened?", str(contributing_post_id)),
        )

        cursor.execute("delete from source_post where post_id = %s", (str(contributing_post_id),))
        cursor.execute(
            "select count(*) from post_chat_result where post_id = %s and question_norm = %s",
            (str(focal_post_id), "what happened?"),
        )
        assert cursor.fetchone()[0] == 0
        cursor.execute(
            "select count(*) from post_chat_authorization_receipt "
            "where post_id = %s and question_norm = %s",
            (str(focal_post_id), "what happened?"),
        )
        assert cursor.fetchone()[0] == 0
        cursor.execute(
            "select count(*) from post_chat_source "
            "where post_id = %s and question_norm = %s",
            (str(focal_post_id), "what happened?"),
        )
        assert cursor.fetchone()[0] == 0


def test_rollback_removes_source_delete_trigger_and_function(isolated_postgres_schema) -> None:
    """Rollback must restore the parent source table without replay invalidation hooks."""
    conn = isolated_postgres_schema
    _create_minimal_parent_schema(conn)
    with conn.cursor() as cursor:
        cursor.execute(_FORWARD_MIGRATION.read_text())
        cursor.execute(_ROLLBACK_MIGRATION.read_text())
        cursor.execute(
            "select count(*) from pg_trigger "
            "where tgname = 'invalidate_post_chat_replay_on_source_delete' and not tgisinternal"
        )
        assert cursor.fetchone()[0] == 0
        cursor.execute(
            "select to_regprocedure('invalidate_post_chat_replay_on_source_post_delete()')"
        )
        assert cursor.fetchone()[0] is None


def test_replay_parent_key_share_blocks_concurrent_answer_replacement(
    isolated_postgres_schema,
) -> None:
    """Receipt validation holds derived-answer identity stable until replay finishes."""
    conn = isolated_postgres_schema
    _create_minimal_parent_schema(conn)
    focal_post_id = str(uuid.uuid4())
    with conn.cursor() as cursor:
        cursor.execute(_FORWARD_MIGRATION.read_text())
        cursor.execute("select current_schema()")
        schema_name = cursor.fetchone()[0]
        cursor.execute("insert into source_post (post_id) values (%s)", (focal_post_id,))
        cursor.execute(
            "insert into post_chat_result "
            "(post_id, question_norm, question_text, answer_text) values (%s, %s, %s, %s)",
            (focal_post_id, "what happened?", "What happened?", "Original answer"),
        )
        cursor.execute(
            "insert into post_chat_authorization_receipt "
            "(post_id, question_norm, process_scope_limited) values (%s, %s, false)",
            (focal_post_id, "what happened?"),
        )

    conn.autocommit = False
    writer = psycopg2.connect(_POSTGRES_DSN)
    writer.autocommit = False
    try:
        with conn.cursor() as reader_cursor:
            reader_cursor.execute(
                "select receipt.process_scope_limited "
                "from post_chat_authorization_receipt receipt "
                "join post_chat_result result "
                "on result.post_id = receipt.post_id "
                "and result.question_norm = receipt.question_norm "
                "where receipt.post_id = %s and receipt.question_norm = %s "
                "for key share of result",
                (focal_post_id, "what happened?"),
            )
            assert reader_cursor.fetchone()[0] is False

        with writer.cursor() as writer_cursor:
            writer_cursor.execute(f'set search_path to "{schema_name}"')
            writer_cursor.execute("set local lock_timeout = '250ms'")
            with pytest.raises(psycopg2.errors.LockNotAvailable):
                writer_cursor.execute(
                    "delete from post_chat_result where post_id = %s and question_norm = %s",
                    (focal_post_id, "what happened?"),
                )
        writer.rollback()
    finally:
        conn.rollback()
        conn.autocommit = True
        writer.close()
