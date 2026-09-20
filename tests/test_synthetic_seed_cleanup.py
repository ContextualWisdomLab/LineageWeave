"""Real-database test for lineageweave/synthetic_seed_cleanup.py.

Applies every migration to a throwaway PostgreSQL database, seeds a demo
scope entangled with real source-import evidence (same shape a real
customer's first import produces against this repo's `make seed` output),
then proves the cleanup deletes only the synthetic row, leaves an
analysis-run-referenced synthetic row alone, and nulls (never drops) a real
post's optional internal-evidence citation to a removed synthetic post.

Skipped unless a local PostgreSQL server is reachable, same convention as
tests/test_schema.py and backend/tests/test_api.py.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import pytest

from lineageweave import postgres_sync as sync_postgres
from lineageweave.postgres_sync import sql
from lineageweave.synthetic_seed_cleanup import cleanup_synthetic_seed

_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def _postgres_available() -> bool:
    try:
        conn = sync_postgres.connect(_ADMIN_DSN, connect_timeout=2)
        conn.close()
        return True
    except sync_postgres.OperationalError:
        return False


def _database_dsn(database_name: str) -> str:
    """Replace only the database path while retaining query options."""
    parsed = urlsplit(_ADMIN_DSN)
    return urlunsplit(parsed._replace(path=f"/{database_name}"))


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=f"no reachable PostgreSQL server at {_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)",
)


@pytest.fixture
def migrated_db():
    """A freshly migrated, throwaway database, dropped afterward."""
    db_name = f"lineageweave_cleanup_test_{uuid.uuid4().hex[:12]}"
    admin_conn = sync_postgres.connect(_ADMIN_DSN)
    admin_conn.autocommit = True
    with admin_conn.cursor() as cur:
        cur.execute(sql.SQL("create database {}").format(sql.Identifier(db_name)))
    admin_conn.close()

    db_dsn = _database_dsn(db_name)
    # psql, not one DB-API execute(), matches docker/postgres-init/migrate.sh:
    # a few migrations use CREATE INDEX CONCURRENTLY, which must run outside
    # an implicit multi-statement transaction.
    for migration in sorted(_MIGRATIONS_DIR.glob("*.sql")):
        subprocess.run(
            ["psql", "-X", "-v", "ON_ERROR_STOP=1", db_dsn, "-f", str(migration)],
            check=True,
        )

    yield db_dsn

    admin_conn = sync_postgres.connect(_ADMIN_DSN)
    admin_conn.autocommit = True
    with admin_conn.cursor() as cur:
        cur.execute(
            "select pg_terminate_backend(pid) from pg_stat_activity where datname = %s",
            (db_name,),
        )
        cur.execute(sql.SQL("drop database {}").format(sql.Identifier(db_name)))
    admin_conn.close()


def test_cleanup_deletes_only_entangled_synthetic_rows(migrated_db: str) -> None:
    async def run() -> dict[str, int]:
        conn = await asyncpg.connect(migrated_db)
        try:
            empty_result = await cleanup_synthetic_seed(conn, apply=True)
            assert empty_result == {
                "candidate_posts": 0,
                "blocked_posts": 0,
                "deletable_posts": 0,
                "deleted_posts": 0,
            }

            # 'corporate_entity_level'/'company' and 'voc_type'/'voc' are already
            # seeded by migrations 0016 and 0042 respectively; inserting them again
            # here would violate common_lookup_value's primary key.
            await conn.execute(
                "insert into common_lookup_value (lookup_category, lookup_code, lookup_label) values "
                "('post_visibility', 'public', 'Public'), "
                "('entity_relationship_type', 'rel_voc', 'Voice of Customer')"
            )
            demo_entity = await conn.fetchval(
                "insert into corporate_entity (corporate_entity_code, entity_name, entity_level_code) "
                "values ('DEMO-CORP-01', 'Demo Corp', 'company') returning corporate_entity_id"
            )
            demo_pu = await conn.fetchval(
                "insert into process_unit (corporate_entity_id, process_unit_code, process_unit_name) "
                "values ($1, 'DEMO-PU-A', 'Demo Unit') returning process_unit_id",
                demo_entity,
            )
            account = await conn.fetchval(
                "insert into user_account (external_subject_id, display_name, email_address) "
                "values ('demo.analyst', 'Demo Analyst', 'demo.analyst@example.test') "
                "returning user_account_id"
            )
            await conn.execute(
                "insert into account_affiliation (user_account_id, corporate_entity_id, process_unit_id) "
                "values ($1, $2, $3)",
                account,
                demo_entity,
                demo_pu,
            )

            synthetic_post = await conn.fetchval(
                "insert into source_post "
                "(author_account_id, corporate_entity_id, process_unit_id, post_title, post_body, "
                " voc_type_code, visibility_code, created_at, updated_at) "
                "values ($1, $2, $3, 'Synthetic seed post', 'synthetic body', 'voc', 'public', now(), now()) "
                "returning post_id",
                account,
                demo_entity,
                demo_pu,
            )
            real_post = await conn.fetchval(
                "insert into source_post "
                "(author_account_id, corporate_entity_id, process_unit_id, post_title, post_body, "
                " voc_type_code, visibility_code, source_author_code, created_at, updated_at) "
                "values ($1, $2, $3, 'Real imported post', 'real body', 'voc', 'public', 'REAL-AUTHOR-1', now(), now()) "
                "returning post_id",
                account,
                demo_entity,
                demo_pu,
            )
            blocked_synthetic_post = await conn.fetchval(
                "insert into source_post "
                "(author_account_id, corporate_entity_id, process_unit_id, post_title, post_body, "
                " voc_type_code, visibility_code, created_at, updated_at) "
                "values ($1, $2, $3, 'Synthetic post in a run snapshot', 'synthetic body 2', 'voc', 'public', now(), now()) "
                "returning post_id",
                account,
                demo_entity,
                demo_pu,
            )
            imported_entity = await conn.fetchval(
                "insert into corporate_entity (corporate_entity_code, entity_name, entity_level_code) "
                "values ('IMPORTED-CORP-01', 'Imported Corp', 'company') returning corporate_entity_id"
            )
            imported_pu = await conn.fetchval(
                "insert into process_unit (corporate_entity_id, process_unit_code, process_unit_name) "
                "values ($1, 'IMPORTED-PU-A', 'Imported Unit') returning process_unit_id",
                imported_entity,
            )
            non_demo_synthetic_post = await conn.fetchval(
                "insert into source_post "
                "(author_account_id, corporate_entity_id, process_unit_id, post_title, post_body, "
                " voc_type_code, visibility_code, created_at, updated_at) "
                "values ($1, $2, $3, 'Synthetic row outside Demo code', 'synthetic body 3', 'voc', 'public', now(), now()) "
                "returning post_id",
                account,
                imported_entity,
                imported_pu,
            )
            await conn.execute(
                "insert into source_post "
                "(author_account_id, corporate_entity_id, process_unit_id, post_title, post_body, "
                " voc_type_code, visibility_code, source_author_code, created_at, updated_at) "
                "values ($1, $2, $3, 'Real row outside Demo code', 'real body 2', 'voc', 'public', 'REAL-AUTHOR-2', now(), now())",
                account,
                imported_entity,
                imported_pu,
            )
            snapshot = await conn.fetchval(
                "insert into analysis_source_snapshot "
                "(snapshot_sha256, source_contract_version, maximum_available_time, captured_at) "
                "values (repeat('0', 64), 'test-v1', now() - interval '1 minute', now()) "
                "returning analysis_source_snapshot_id"
            )
            analysis_run = await conn.fetchval(
                "insert into analysis_run "
                "(analysis_source_snapshot_id, run_kind_code, requested_by_account_id, "
                " idempotency_key, knowledge_cutoff, configuration_schema_version, "
                " configuration_sha256, code_revision_sha) "
                "values ($1, 'analysis_run_lineage', $2, 'test-idem-1', now(), "
                "        'lineage-run-v1', repeat('0', 64), repeat('0', 40)) "
                "returning analysis_run_id",
                snapshot,
                account,
            )
            await conn.execute(
                "insert into analysis_source_snapshot_member (analysis_source_snapshot_id, source_post_id) "
                "values ($1, $2)",
                snapshot,
                blocked_synthetic_post,
            )

            counterparty_relationship_type = await conn.fetchval(
                "select lookup_code from common_lookup_value "
                "where lookup_category = 'entity_relationship_type' limit 1"
            )
            await conn.execute(
                "insert into post_counterparty_entity "
                "(post_id, counterparty_entity_name, relationship_type_code, "
                " verification_status_code, verification_evidence_post_id) "
                "values ($1, 'Some Counterparty', $2, 'verify_pending', $3)",
                real_post,
                counterparty_relationship_type,
                synthetic_post,
            )

            dry_run_result = await cleanup_synthetic_seed(conn, apply=False)
            assert dry_run_result["deleted_posts"] == 0
            assert await conn.fetchval(
                "select count(*) from source_post where post_id = $1", synthetic_post
            ) == 1

            result = await cleanup_synthetic_seed(conn, apply=True)

            assert (
                await conn.fetchval("select count(*) from source_post where post_id = $1", synthetic_post)
                == 0
            ), "the entangled synthetic post must be deleted"
            assert (
                await conn.fetchval("select count(*) from source_post where post_id = $1", real_post) == 1
            ), "the real post must survive"
            assert (
                await conn.fetchval(
                    "select count(*) from source_post where post_id = $1", blocked_synthetic_post
                )
                == 1
            ), "a synthetic post referenced by an analysis-run snapshot must never be deleted"
            assert (
                await conn.fetchval(
                    "select count(*) from source_post where post_id = $1", non_demo_synthetic_post
                )
                == 1
            ), "non-Demo corporate entities must never be synthetic cleanup candidates"

            counterparty_row = await conn.fetchrow(
                "select verification_evidence_post_id from post_counterparty_entity where post_id = $1",
                real_post,
            )
            assert counterparty_row is not None, (
                "the real post's counterparty row must survive -- only the citation is removed"
            )
            assert counterparty_row["verification_evidence_post_id"] is None, (
                "the citation to the deleted synthetic post must be nulled, not left dangling"
            )

            assert (
                await conn.fetchval(
                    "select count(*) from analysis_run where analysis_run_id = $1", analysis_run
                )
                == 1
            ), "cleanup must never touch the immutable analysis_run family"

            return result

        finally:
            await conn.close()

    result = asyncio.run(run())
    assert result["candidate_posts"] == 2
    assert result["blocked_posts"] == 1
    assert result["deletable_posts"] == 1
    assert result["deleted_posts"] == 1
