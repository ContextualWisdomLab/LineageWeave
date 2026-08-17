"""Real-database contract for migrations/0013_activity_outbox.sql.

Applies 0001 then 0013 on a throwaway database. Self-skips without
PostgreSQL. Proves the outbox table, lookup codes, and the delivered
row's required stream id -- never a fabricated theta.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import psycopg2
import pytest

_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_ROOT = Path(__file__).resolve().parents[1]
_MIGRATION_0001 = _ROOT / "migrations" / "0001_initial_schema.sql"
_MIGRATION_0013 = _ROOT / "migrations" / "0013_activity_outbox.sql"


def _postgres_available() -> bool:
    try:
        conn = psycopg2.connect(_ADMIN_DSN, connect_timeout=2)
        conn.close()
        return True
    except psycopg2.OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=f"no reachable PostgreSQL server at {_ADMIN_DSN}",
)


@pytest.fixture
def outbox_schema_db():
    db_name = f"lineageweave_outbox_{uuid.uuid4().hex[:12]}"
    admin_conn = psycopg2.connect(_ADMIN_DSN)
    admin_conn.autocommit = True
    with admin_conn.cursor() as cur:
        cur.execute(f'create database "{db_name}"')
    try:
        db_dsn = _ADMIN_DSN.rsplit("/", 1)[0] + f"/{db_name}"
        conn = psycopg2.connect(db_dsn)
        try:
            with conn.cursor() as cur:
                cur.execute(_MIGRATION_0001.read_text())
                cur.execute(_MIGRATION_0013.read_text())
            conn.commit()
            yield conn
        finally:
            conn.close()
    finally:
        with admin_conn.cursor() as cur:
            cur.execute(f'drop database "{db_name}"')
        admin_conn.close()


def test_activity_outbox_table_and_lookups_exist(outbox_schema_db) -> None:
    with outbox_schema_db.cursor() as cur:
        cur.execute(
            "select 1 from information_schema.tables "
            "where table_schema = 'public' and table_name = 'activity_outbox_event'"
        )
        assert cur.fetchone() is not None
        cur.execute(
            "select lookup_code from common_lookup_value "
            "where lookup_category in ('activity_event_type', 'outbox_delivery_status') "
            "order by lookup_code"
        )
        codes = {row[0] for row in cur.fetchall()}
    assert {
        "ticket_created",
        "ticket_status_changed",
        "commitment_derived",
        "outbox_pending",
        "outbox_delivered",
        "outbox_failed",
    } <= codes


def test_delivered_row_requires_a_stream_id(outbox_schema_db) -> None:
    with outbox_schema_db.cursor() as cur:
        cur.execute(
            """
            select pg_get_constraintdef(oid)
              from pg_constraint
             where conrelid = 'activity_outbox_event'::regclass
               and contype = 'c'
            """
        )
        checks = " ".join(row[0] for row in cur.fetchall())
    assert "outbox_delivered" in checks
    assert "valkey_entry_id" in checks
