"""Real-PostgreSQL tests for the authoritative project-lifecycle writer.

The fixtures contain only synthetic source identities.  These tests exercise
the transaction, identity, evidence, replacement, relation, and withdrawal
boundaries against the same SQL migrations used by the product stack.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime, timezone
import os
from pathlib import Path
import uuid
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import psycopg2
from psycopg2 import sql
import pytest

from backend.app.project_lifecycle_ingestion import (
    ingest_project_lifecycle_event,
    register_project_event_mapping,
    withdraw_project_lifecycle_record,
)
from lineageweave.project_lifecycle import (
    ProjectLifecycleEventInput,
    ProjectLifecycleRelationInput,
    ProjectLifecycleResponsibilityInput,
    ProjectLifecycleValidationError,
    project_lifecycle_digest,
    validate_project_lifecycle_event,
)

_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_ROOT = Path(__file__).resolve().parents[1]
_INITIAL_MIGRATION = _ROOT / "migrations" / "0001_initial_schema.sql"
_SOURCE_IDENTITY_MIGRATION = _ROOT / "migrations" / "0037_source_record_identity.sql"
_LIFECYCLE_MIGRATION = _ROOT / "migrations" / "0054_project_lifecycle_ingestion.sql"


def _postgres_available() -> bool:
    """Return whether the real local PostgreSQL test service is reachable."""

    try:
        psycopg2.connect(_ADMIN_DSN, connect_timeout=2).close()
        return True
    except psycopg2.OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=f"no reachable PostgreSQL server at {_ADMIN_DSN}",
)


def _database_dsn(database_name: str) -> str:
    """Replace only the database path while preserving DSN parameters."""

    parsed = urlsplit(_ADMIN_DSN)
    return urlunsplit(parsed._replace(path=f"/{database_name}"))


@pytest.fixture
def lifecycle_database() -> tuple[str, dict[str, str]]:
    """Create a migrated database with two synthetic source evidence posts."""

    database_name = f"lineageweave_lifecycle_{uuid.uuid4().hex[:12]}"
    admin = psycopg2.connect(_ADMIN_DSN)
    admin.autocommit = True
    with admin.cursor() as cursor:
        cursor.execute(sql.SQL("create database {}").format(sql.Identifier(database_name)))
    admin.close()
    dsn = _database_dsn(database_name)
    connection = psycopg2.connect(dsn)
    post_ids = {"order": str(uuid.uuid4()), "other": str(uuid.uuid4()), "target": str(uuid.uuid4())}
    try:
        with connection.cursor() as cursor:
            cursor.execute(_INITIAL_MIGRATION.read_text(encoding="utf-8"))
            cursor.execute("create extension if not exists pg_trgm")
            cursor.execute(_SOURCE_IDENTITY_MIGRATION.read_text(encoding="utf-8"))
            cursor.execute(_LIFECYCLE_MIGRATION.read_text(encoding="utf-8"))
            cursor.execute(
                """
                insert into common_lookup_value
                    (lookup_category, lookup_code, lookup_label)
                values
                    ('voc_type', 'voc', 'Voice of Customer'),
                    ('post_visibility', 'public', 'Public'),
                    ('corporate_entity_level', 'company', 'Company')
                """
            )
            cursor.execute(
                """
                insert into corporate_entity
                    (corporate_entity_code, entity_name, entity_level_code)
                values ('SYNTH-CORP', 'Synthetic Corporation', 'company')
                returning corporate_entity_id
                """
            )
            corporate_id = cursor.fetchone()[0]
            cursor.execute(
                """
                insert into user_account (external_subject_id, display_name, email_address)
                values ('synthetic-subject', 'Synthetic Importer', 'synthetic@example.test')
                returning user_account_id
                """
            )
            account_id = cursor.fetchone()[0]
            for record_key, post_id in (
                ("order-1", post_ids["order"]),
                ("other-1", post_ids["other"]),
                ("target-1", post_ids["target"]),
            ):
                cursor.execute(
                    """
                    insert into source_post
                        (post_id, author_account_id, corporate_entity_id, post_title,
                         post_body, voc_type_code, visibility_code, source_system_code,
                         source_record_key)
                    values (%s, %s, %s, 'Synthetic evidence', 'Synthetic evidence body',
                            'voc', 'public', 'synthetic_source', %s)
                    """,
                    (post_id, account_id, corporate_id, record_key),
                )
        connection.commit()
        yield dsn, post_ids
    finally:
        connection.close()
        admin = psycopg2.connect(_ADMIN_DSN)
        admin.autocommit = True
        with admin.cursor() as cursor:
            cursor.execute(sql.SQL("drop database {}").format(sql.Identifier(database_name)))
        admin.close()


def _event(
    post_ids: dict[str, str],
    *,
    record_key: str = "order-1",
    project_key: str = "P-100",
    source_event_code: str = "ORDER_CREATED",
    started_at: datetime | None = None,
    relations: tuple[ProjectLifecycleRelationInput, ...] = (),
    responsibilities: tuple[ProjectLifecycleResponsibilityInput, ...] = (),
) -> ProjectLifecycleEventInput:
    """Build one synthetic explicit source event."""

    return ProjectLifecycleEventInput(
        project_key=project_key,
        project_name="Synthetic Project",
        source_system_code="synthetic_source",
        source_record_key=record_key,
        source_event_code=source_event_code,
        mapping_version="v1",
        event_started_at=started_at or datetime(2026, 1, 1, tzinfo=timezone.utc),
        event_ended_at=None,
        evidence_post_id=post_ids["order" if record_key == "order-1" else "target"],
        relations=relations,
        responsibilities=responsibilities,
    )


async def _register_mapping(connection: asyncpg.Connection, source_event_code: str = "ORDER_CREATED") -> None:
    """Register a deterministic synthetic mapping for a test."""

    await register_project_event_mapping(
        connection,
        source_system_code="synthetic_source",
        source_system_name="Synthetic Source",
        mapping_version="v1",
        source_event_code=source_event_code,
        project_event_type_code="project_event_order",
        administrator_key="synthetic-admin",
        permission_codes={"project_lifecycle_write"},
    )


def test_permission_is_separate_from_post_read() -> None:
    """The writer cannot be authorized by the buyer read permission alone."""

    from lineageweave.project_lifecycle import require_project_lifecycle_write_permission

    with pytest.raises(PermissionError, match="project_lifecycle_write"):
        require_project_lifecycle_write_permission({"post_read"})


def test_lifecycle_contract_rejects_invalid_time_uuid_project_and_relation_inputs() -> None:
    """Validation fails closed before a database UUID or timestamp cast."""

    post_ids = {"order": str(uuid.uuid4()), "target": str(uuid.uuid4())}
    valid = _event(post_ids)
    invalid_events = (
        (replace(valid, project_key=" "), "project_key"),
        (replace(valid, project_key="x" * 257), "project key"),
        (replace(valid, event_started_at="not a datetime"), "datetime"),
        (replace(valid, event_started_at=datetime(2026, 1, 1)), "timezone"),
        (
            replace(valid, event_ended_at=datetime(2025, 12, 31, tzinfo=timezone.utc)),
            "precede",
        ),
        (replace(valid, evidence_post_id="not-a-uuid"), "UUID"),
        (
            replace(
                valid,
                relations=(
                    ProjectLifecycleRelationInput(
                        "synthetic_source",
                        "order-1",
                        "unsupported_relation",
                        post_ids["order"],
                    ),
                ),
            ),
            "relation_type_code",
        ),
        (
            replace(
                valid,
                relations=(
                    ProjectLifecycleRelationInput(
                        "synthetic_source",
                        " order-1 ",
                        "project_relation_related",
                        post_ids["order"],
                    ),
                ),
            ),
            "itself",
        ),
        (
            replace(
                valid,
                responsibilities=(
                    ProjectLifecycleResponsibilityInput(
                        "unsupported_actor",
                        "actor-1",
                        "Synthetic Actor",
                        "process the order",
                        post_ids["order"],
                    ),
                ),
            ),
            "actor_type_code",
        ),
    )

    for invalid_event, message in invalid_events:
        with pytest.raises(ProjectLifecycleValidationError, match=message):
            validate_project_lifecycle_event(invalid_event)

    assert len(project_lifecycle_digest(valid)) == 64


def test_mapping_administration_rejects_unauthorized_or_invalid_requests(lifecycle_database) -> None:
    """Mapping registration has its own permission and explicit-code checks."""
    dsn, post_ids = lifecycle_database

    async def run() -> None:
        connection = await asyncpg.connect(dsn)
        try:
            with pytest.raises(PermissionError, match="project_lifecycle_write"):
                await register_project_event_mapping(
                    connection,
                    source_system_code="synthetic_source",
                    source_system_name="Synthetic Source",
                    mapping_version="v1",
                    source_event_code="ORDER_CREATED",
                    project_event_type_code="project_event_order",
                    administrator_key="synthetic-admin",
                    permission_codes={"post_read"},
                )
            with pytest.raises(PermissionError, match="administrator_key"):
                await register_project_event_mapping(
                    connection,
                    source_system_code="synthetic_source",
                    source_system_name="Synthetic Source",
                    mapping_version="v1",
                    source_event_code="ORDER_CREATED",
                    project_event_type_code="project_event_order",
                    administrator_key=" ",
                    permission_codes={"project_lifecycle_write"},
                )
            with pytest.raises(ProjectLifecycleValidationError, match="mapping fields"):
                await register_project_event_mapping(
                    connection,
                    source_system_code=" ",
                    source_system_name="Synthetic Source",
                    mapping_version="v1",
                    source_event_code="ORDER_CREATED",
                    project_event_type_code="project_event_order",
                    administrator_key="synthetic-admin",
                    permission_codes={"project_lifecycle_write"},
                )
            with pytest.raises(ProjectLifecycleValidationError, match="unsupported"):
                await register_project_event_mapping(
                    connection,
                    source_system_code="synthetic_source",
                    source_system_name="Synthetic Source",
                    mapping_version="v1",
                    source_event_code="ORDER_CREATED",
                    project_event_type_code="unsupported_event",
                    administrator_key="synthetic-admin",
                    permission_codes={"project_lifecycle_write"},
                )
            with pytest.raises(PermissionError, match="administrator_key"):
                await ingest_project_lifecycle_event(
                    connection,
                    _event(post_ids),
                    administrator_key=" ",
                    permission_codes={"project_lifecycle_write"},
                )
            with pytest.raises(PermissionError, match="administrator_key"):
                await withdraw_project_lifecycle_record(
                    connection,
                    source_system_code="synthetic_source",
                    source_record_key="order-1",
                    administrator_key=" ",
                    permission_codes={"project_lifecycle_write"},
                )
            with pytest.raises(ProjectLifecycleValidationError, match="source identity"):
                await withdraw_project_lifecycle_record(
                    connection,
                    source_system_code=" ",
                    source_record_key="order-1",
                    administrator_key="synthetic-admin",
                    permission_codes={"project_lifecycle_write"},
                )
        finally:
            await connection.close()

    asyncio.run(run())


def test_upsert_is_idempotent_and_replaces_source_owned_event(lifecycle_database) -> None:
    dsn, post_ids = lifecycle_database

    async def run() -> tuple[dict[str, object], dict[str, object], list[asyncpg.Record]]:
        connection = await asyncpg.connect(dsn)
        try:
            await _register_mapping(connection)
            responsibility = ProjectLifecycleResponsibilityInput(
                actor_type_code="prov_person",
                actor_key="actor-1",
                actor_name="Synthetic Actor",
                responsibility_text="process the order",
                evidence_post_id=post_ids["order"],
            )
            first = await ingest_project_lifecycle_event(
                connection,
                _event(post_ids, responsibilities=(responsibility,)),
                administrator_key="synthetic-admin",
                permission_codes={"project_lifecycle_write"},
            )
            second = await ingest_project_lifecycle_event(
                connection,
                _event(
                    post_ids,
                    started_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
                    responsibilities=(responsibility,),
                ),
                administrator_key="synthetic-admin",
                permission_codes={"project_lifecycle_write"},
            )
            rows = await connection.fetch(
                """
                select event.event_started_at, record.lifecycle_state_code
                  from project_lifecycle_event event
                  join project_source_record record
                    on record.project_source_record_id = event.project_source_record_id
                """
            )
            assert await connection.fetchval(
                "select count(*) from project_event_responsibility"
            ) == 1
            return first, second, rows
        finally:
            await connection.close()

    first, second, rows = asyncio.run(run())
    assert first["status_code"] == "inserted"
    assert second["status_code"] == "replaced"
    assert first["project_lifecycle_event_id"] == second["project_lifecycle_event_id"]
    assert len(rows) == 1
    assert rows[0]["event_started_at"].date().isoformat() == "2026-01-02"
    assert rows[0]["lifecycle_state_code"] == "project_record_active"


def test_concurrent_duplicate_imports_converge_on_one_event(lifecycle_database) -> None:
    """The source-identity advisory lock serializes duplicate imports."""

    dsn, post_ids = lifecycle_database

    async def run() -> tuple[list[dict[str, object]], int]:
        setup = await asyncpg.connect(dsn)
        await _register_mapping(setup)
        await setup.close()
        connections = [await asyncpg.connect(dsn) for _ in range(2)]
        try:
            results = await asyncio.gather(
                *(
                    ingest_project_lifecycle_event(
                        connection,
                        _event(post_ids),
                        administrator_key="synthetic-admin",
                        permission_codes={"project_lifecycle_write"},
                    )
                    for connection in connections
                )
            )
            count = await connections[0].fetchval("select count(*) from project_lifecycle_event")
            return results, count
        finally:
            await asyncio.gather(*(connection.close() for connection in connections))

    results, count = asyncio.run(run())
    assert {result["status_code"] for result in results} == {"inserted", "replaced"}
    assert count == 1


def test_unknown_mapping_and_mismatched_evidence_fail_without_mutation(lifecycle_database) -> None:
    dsn, post_ids = lifecycle_database

    async def run() -> int:
        connection = await asyncpg.connect(dsn)
        try:
            with pytest.raises(ProjectLifecycleValidationError, match="mapping"):
                await ingest_project_lifecycle_event(
                    connection,
                    _event(post_ids, source_event_code="UNREGISTERED"),
                    administrator_key="synthetic-admin",
                    permission_codes={"project_lifecycle_write"},
                )
            await _register_mapping(connection)
            mismatched = ProjectLifecycleEventInput(
                **{
                    **_event(post_ids).__dict__,
                    "evidence_post_id": post_ids["other"],
                }
            )
            with pytest.raises(ProjectLifecycleValidationError, match="belong"):
                await ingest_project_lifecycle_event(
                    connection,
                    mismatched,
                    administrator_key="synthetic-admin",
                    permission_codes={"project_lifecycle_write"},
                )
            return await connection.fetchval("select count(*) from project_lifecycle_event")
        finally:
            await connection.close()

    assert asyncio.run(run()) == 0


def test_registered_mapping_must_resolve_to_supported_event_type(lifecycle_database) -> None:
    """A direct catalog corruption cannot turn an unrelated lookup into an event."""
    dsn, post_ids = lifecycle_database

    async def run() -> None:
        connection = await asyncpg.connect(dsn)
        try:
            source_system_id = await connection.fetchval(
                """
                insert into project_source_system (source_system_code, source_system_name)
                values ('invalid_mapping_source', 'Invalid Mapping Source')
                returning project_source_system_id
                """
            )
            await connection.execute(
                """
                insert into project_event_mapping
                    (project_source_system_id, mapping_version, source_event_code,
                     project_event_type_code)
                values ($1, 'v1', 'INVALID_TYPE', 'public')
                """,
                source_system_id,
            )
            invalid_event = replace(
                _event(post_ids),
                source_system_code="invalid_mapping_source",
                source_event_code="INVALID_TYPE",
            )
            with pytest.raises(ProjectLifecycleValidationError, match="unregistered"):
                await ingest_project_lifecycle_event(
                    connection,
                    invalid_event,
                    administrator_key="synthetic-admin",
                    permission_codes={"project_lifecycle_write"},
                )
        finally:
            await connection.close()

    asyncio.run(run())


def test_cross_project_relation_is_rejected(lifecycle_database) -> None:
    dsn, post_ids = lifecycle_database

    async def run() -> int:
        connection = await asyncpg.connect(dsn)
        try:
            await _register_mapping(connection)
            await ingest_project_lifecycle_event(
                connection,
                _event(post_ids, record_key="target-1", project_key="P-200"),
                administrator_key="synthetic-admin",
                permission_codes={"project_lifecycle_write"},
            )
            relation = ProjectLifecycleRelationInput(
                target_source_system_code="synthetic_source",
                target_source_record_key="target-1",
                relation_type_code="project_relation_precedes",
                evidence_post_id=post_ids["order"],
            )
            with pytest.raises(ProjectLifecycleValidationError, match="same project"):
                await ingest_project_lifecycle_event(
                    connection,
                    _event(post_ids, relations=(relation,)),
                    administrator_key="synthetic-admin",
                    permission_codes={"project_lifecycle_write"},
                )
            return await connection.fetchval("select count(*) from project_lifecycle_event")
        finally:
            await connection.close()

    assert asyncio.run(run()) == 1


def test_withdrawal_removes_owned_projection_and_keeps_independent_event(lifecycle_database) -> None:
    dsn, post_ids = lifecycle_database

    async def run() -> tuple[dict[str, object], list[asyncpg.Record]]:
        connection = await asyncpg.connect(dsn)
        try:
            await _register_mapping(connection)
            await ingest_project_lifecycle_event(
                connection,
                _event(post_ids, record_key="target-1"),
                administrator_key="synthetic-admin",
                permission_codes={"project_lifecycle_write"},
            )
            relation = ProjectLifecycleRelationInput(
                target_source_system_code="synthetic_source",
                target_source_record_key="target-1",
                relation_type_code="project_relation_precedes",
                evidence_post_id=post_ids["order"],
            )
            await ingest_project_lifecycle_event(
                connection,
                _event(post_ids, relations=(relation,)),
                administrator_key="synthetic-admin",
                permission_codes={"project_lifecycle_write"},
            )
            result = await withdraw_project_lifecycle_record(
                connection,
                source_system_code="synthetic_source",
                source_record_key="order-1",
                administrator_key="synthetic-admin",
                permission_codes={"project_lifecycle_write"},
            )
            rows = await connection.fetch(
                "select source_record_key from project_source_record where lifecycle_state_code = 'project_record_active'"
            )
            return result, rows
        finally:
            await connection.close()

    result, active_rows = asyncio.run(run())
    assert result["status_code"] == "withdrawn"
    assert [row["source_record_key"] for row in active_rows] == ["target-1"]


def test_withdrawal_of_unknown_source_is_idempotent_not_found(lifecycle_database) -> None:
    """A repeated withdrawal returns a safe aggregate status without a write."""
    dsn, _ = lifecycle_database

    async def run() -> dict[str, object]:
        connection = await asyncpg.connect(dsn)
        try:
            return await withdraw_project_lifecycle_record(
                connection,
                source_system_code="synthetic_source",
                source_record_key="missing-record",
                administrator_key="synthetic-admin",
                permission_codes={"project_lifecycle_write"},
            )
        finally:
            await connection.close()

    assert asyncio.run(run()) == {"status_code": "not_found"}
