"""Live PostgreSQL proof for Customer Master hint-resolution ownership separation.

Synthetic fixtures only. Skips when LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN is
unreachable, matching the repository's other live PostgreSQL contracts.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import uuid
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import psycopg2
import pytest

import backend.app.customer_hint_ingestion as ingestion
from lineageweave.relation_verification import STATUS_CORROBORATED

_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_ROOT = Path(__file__).resolve().parents[1]
_MIGRATIONS_DIR = _ROOT / "migrations"


def _postgres_available() -> bool:
    try:
        connection = psycopg2.connect(_ADMIN_DSN, connect_timeout=2)
        connection.close()
        return True
    except psycopg2.OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=(
        "no reachable PostgreSQL server at "
        f"{_ADMIN_DSN} (set LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN)"
    ),
)


def _database_dsn(database_name: str) -> str:
    parsed = urlsplit(_ADMIN_DSN)
    return urlunsplit(parsed._replace(path=f"/{database_name}"))


def _apply_migrations(database_dsn: str) -> None:
    for migration in sorted(_MIGRATIONS_DIR.glob("*.sql")):
        subprocess.run(
            ["psql", "-X", "-v", "ON_ERROR_STOP=1", database_dsn, "-f", str(migration)],
            check=True,
            capture_output=True,
            text=True,
        )


@pytest.fixture(scope="module")
def customer_resolution_dsn():
    database_name = f"lineageweave_customer_resolution_{uuid.uuid4().hex[:10]}"
    admin_connection = psycopg2.connect(_ADMIN_DSN)
    admin_connection.autocommit = True
    with admin_connection.cursor() as cursor:
        cursor.execute(f'create database "{database_name}"')
    admin_connection.close()
    database_dsn = _database_dsn(database_name)
    try:
        _apply_migrations(database_dsn)
        yield database_dsn
    finally:
        admin_connection = psycopg2.connect(_ADMIN_DSN)
        admin_connection.autocommit = True
        with admin_connection.cursor() as cursor:
            cursor.execute(
                "select pg_terminate_backend(pid) from pg_stat_activity "
                "where datname = %s and pid <> pg_backend_pid()",
                (database_name,),
            )
            cursor.execute(f'drop database "{database_name}"')
        admin_connection.close()


def _seed_cross_tenant_hint(database_dsn: str) -> dict[str, str]:
    connection = psycopg2.connect(database_dsn)
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into common_lookup_value (lookup_category, lookup_code, lookup_label)
            values
                ('corporate_entity_level', 'customer_test_company', 'Synthetic company'),
                ('voc_type', 'customer_test_voc', 'Synthetic VOC'),
                ('post_visibility', 'customer_test_private', 'Synthetic private')
            on conflict (lookup_code) do nothing
            """
        )
        cursor.execute(
            """
            insert into corporate_entity (corporate_entity_code, entity_name, entity_level_code)
            values
                (%s, 'Tenant A', 'customer_test_company'),
                (%s, 'Tenant B', 'customer_test_company'),
                (%s, 'Resolved Customer', 'customer_test_company')
            returning corporate_entity_id, corporate_entity_code
            """,
            (
                f"TENANT-A-{uuid.uuid4().hex[:8]}",
                f"TENANT-B-{uuid.uuid4().hex[:8]}",
                f"RESOLVED-{uuid.uuid4().hex[:8]}",
            ),
        )
        entity_by_code = {code: str(entity_id) for entity_id, code in cursor.fetchall()}
        tenant_codes = sorted(code for code in entity_by_code if code.startswith("TENANT-"))
        resolved_code = next(code for code in entity_by_code if code.startswith("RESOLVED-"))
        tenant_a_id = entity_by_code[next(code for code in tenant_codes if code.startswith("TENANT-A-"))]
        tenant_b_id = entity_by_code[next(code for code in tenant_codes if code.startswith("TENANT-B-"))]
        resolved_id = entity_by_code[resolved_code]

        cursor.execute(
            """
            insert into process_unit (corporate_entity_id, process_unit_code, process_unit_name)
            values (%s, %s, 'Tenant A PU'), (%s, %s, 'Tenant B PU')
            returning process_unit_id, corporate_entity_id
            """,
            (
                tenant_a_id,
                f"PU-A-{uuid.uuid4().hex[:8]}",
                tenant_b_id,
                f"PU-B-{uuid.uuid4().hex[:8]}",
            ),
        )
        process_by_entity = {str(entity_id): str(process_id) for process_id, entity_id in cursor.fetchall()}
        cursor.execute(
            """
            insert into user_account (external_subject_id, display_name, email_address)
            values (%s, 'Synthetic resolver', %s)
            returning user_account_id
            """,
            (f"resolver-{uuid.uuid4().hex}", f"resolver-{uuid.uuid4().hex}@example.test"),
        )
        author_id = str(cursor.fetchone()[0])
        hint_code = "SYNTH-CUSTOMER-001"
        stored_hint_code = f"  {hint_code}  "
        posts: dict[str, str] = {}
        for tenant_name, entity_id in (("a", tenant_a_id), ("b", tenant_b_id)):
            cursor.execute(
                """
                insert into source_post (
                    author_account_id, corporate_entity_id, process_unit_id,
                    post_title, post_body, voc_type_code, visibility_code,
                    source_customer_code, source_customer_name
                )
                values (%s, %s, %s, %s, %s, 'customer_test_voc',
                        'customer_test_private', %s, 'Resolved Customer')
                returning post_id
                """,
                (
                    author_id,
                    entity_id,
                    process_by_entity[entity_id],
                    f"Tenant {tenant_name.upper()} evidence",
                    f"Synthetic {tenant_name} body",
                    stored_hint_code,
                ),
            )
            posts[tenant_name] = str(cursor.fetchone()[0])
    connection.close()
    return {
        "tenant_a_id": tenant_a_id,
        "tenant_b_id": tenant_b_id,
        "tenant_a_pu": process_by_entity[tenant_a_id],
        "resolved_id": resolved_id,
        "post_a": posts["a"],
        "post_b": posts["b"],
        "hint_code": hint_code,
        "stored_hint_code": stored_hint_code,
    }


class _ResolutionClient:
    available = True


class _VerificationClient:
    pass


def _corroborated_resolution():
    return SimpleNamespace(
        raw_organization_name="SYNTH-CUSTOMER-001",
        resolved_organization_name="Resolved Customer",
        verification_status_code=STATUS_CORROBORATED,
        verification_evidence_url="https://evidence.example/customer-resolution",
    )


def test_live_resolution_uses_only_visible_sources_and_preserves_tenant_ownership(
    customer_resolution_dsn: str, monkeypatch
) -> None:
    seeded = _seed_cross_tenant_hint(customer_resolution_dsn)
    monkeypatch.setattr(
        ingestion,
        "resolve_and_verify_organization_name",
        lambda *_args: _corroborated_resolution(),
    )

    async def exercise() -> dict:
        pool = await asyncpg.create_pool(customer_resolution_dsn, min_size=1, max_size=2)
        try:
            return await ingestion.resolve_customer_hint(
                pool,
                _ResolutionClient(),
                _VerificationClient(),
                seeded["hint_code"],
                [seeded["tenant_a_id"]],
                [seeded["tenant_a_pu"]],
            )
        finally:
            await pool.close()

    result = asyncio.run(exercise())
    assert result is not None
    assert result["corporate_entity_id"] == seeded["resolved_id"]
    assert result["linked_post_count"] == 1

    connection = psycopg2.connect(customer_resolution_dsn)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select post_id::text, corporate_entity_id::text, process_unit_id::text
              from source_post
             where post_id in (%s::uuid, %s::uuid)
             order by post_id
            """,
            (seeded["post_a"], seeded["post_b"]),
        )
        ownership = {post_id: (entity_id, process_id) for post_id, entity_id, process_id in cursor.fetchall()}
        assert ownership[seeded["post_a"]] == (seeded["tenant_a_id"], seeded["tenant_a_pu"])
        assert ownership[seeded["post_b"]][0] == seeded["tenant_b_id"]

        cursor.execute(
            """
            select post_id::text, resolved_corporate_entity_id::text, source_customer_code
              from source_post_customer_resolution
             order by post_id
            """
        )
        associations = cursor.fetchall()
    connection.close()

    assert associations == [
        (seeded["post_a"], seeded["resolved_id"], seeded["stored_hint_code"])
    ]
