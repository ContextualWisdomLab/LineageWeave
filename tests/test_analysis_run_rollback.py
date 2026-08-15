"""Real-PostgreSQL rollback and reapply proof for migration 0018."""

from __future__ import annotations

import os
from pathlib import Path
import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg2
import pytest

_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_ROOT = Path(__file__).resolve().parents[1]
_INITIAL = _ROOT / "migrations" / "0001_initial_schema.sql"
_FORWARD = _ROOT / "migrations" / "0018_analysis_run_provenance.sql"
_ROLLBACK = _ROOT / "migrations" / "0018_analysis_run_provenance_down.sql"


def _postgres_available() -> bool:
    try:
        psycopg2.connect(_ADMIN_DSN, connect_timeout=2).close()
        return True
    except psycopg2.OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=f"no reachable PostgreSQL server at {_ADMIN_DSN}",
)


def test_analysis_run_migration_rolls_back_without_touching_product_and_reapplies() -> None:
    """Prove an operator can remove and reapply only the 0018 control plane."""

    database_name = f"lineageweave_rollback_{uuid.uuid4().hex[:12]}"
    admin = psycopg2.connect(_ADMIN_DSN)
    admin.autocommit = True
    with admin.cursor() as cursor:
        cursor.execute(f'create database "{database_name}"')
    try:
        parsed = urlsplit(_ADMIN_DSN)
        database_dsn = urlunsplit(parsed._replace(path=f"/{database_name}"))
        connection = psycopg2.connect(database_dsn)
        try:
            with connection.cursor() as cursor:
                cursor.execute(_INITIAL.read_text(encoding="utf-8"))
                cursor.execute(_FORWARD.read_text(encoding="utf-8"))
                cursor.execute(_ROLLBACK.read_text(encoding="utf-8"))
                cursor.execute(
                    "select to_regclass('public.source_post'), "
                    "to_regclass('public.analysis_run_record')"
                )
                source_post, analysis_run = cursor.fetchone()
                assert source_post == "source_post"
                assert analysis_run is None
                cursor.execute(
                    "select count(*) from common_lookup_value "
                    "where lookup_category like 'analysis_%'"
                )
                assert cursor.fetchone()[0] == 0
                cursor.execute(_FORWARD.read_text(encoding="utf-8"))
                cursor.execute(
                    "select to_regclass('public.analysis_run_record')"
                )
                assert cursor.fetchone()[0] == "analysis_run_record"
            connection.commit()
        finally:
            connection.close()
    finally:
        with admin.cursor() as cursor:
            cursor.execute(f'drop database "{database_name}"')
        admin.close()
