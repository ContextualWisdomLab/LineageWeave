"""Real-PostgreSQL contract tests for the PROV-O migration.

The module applies the actual base and PROV-O migration files to a throwaway
database.  It self-skips when no local PostgreSQL is reachable, matching the
repository's existing real-database schema tests.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2")

_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_ROOT = Path(__file__).resolve().parents[1]
_MIGRATION_PATHS = (
    _ROOT / "migrations" / "0001_initial_schema.sql",
    _ROOT / "migrations" / "0017_prov_o_standard_relations.sql",
)


def _postgres_available() -> bool:
    """Return whether the configured PostgreSQL admin database is reachable."""
    try:
        connection = psycopg2.connect(_ADMIN_DSN, connect_timeout=2)
        connection.close()
        return True
    except psycopg2.OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=f"no reachable PostgreSQL server at {_ADMIN_DSN}",
)


@pytest.fixture
def prov_schema_db():
    """Yield a freshly migrated database and drop it after the test."""
    database_name = f"lineageweave_prov_{uuid.uuid4().hex[:12]}"
    admin_connection = psycopg2.connect(_ADMIN_DSN)
    admin_connection.autocommit = True
    with admin_connection.cursor() as cursor:
        cursor.execute(f'create database "{database_name}"')
    try:
        database_dsn = _ADMIN_DSN.rsplit("/", 1)[0] + f"/{database_name}"
        connection = psycopg2.connect(database_dsn)
        try:
            with connection.cursor() as cursor:
                for migration_path in _MIGRATION_PATHS:
                    cursor.execute(migration_path.read_text())
            connection.commit()
            yield connection
        finally:
            connection.close()
    finally:
        with admin_connection.cursor() as cursor:
            cursor.execute(f'drop database "{database_name}"')
        admin_connection.close()


def _resource(cursor, iri: str, class_code: str) -> str:
    """Insert one typed provenance resource and return its UUID."""
    cursor.execute(
        "insert into provenance_resource (resource_iri) values (%s) returning resource_id",
        (iri,),
    )
    resource_id = cursor.fetchone()[0]
    cursor.execute(
        "insert into provenance_resource_type (resource_id, class_code) values (%s, %s)",
        (resource_id, class_code),
    )
    return str(resource_id)


def test_catalog_has_every_normative_term(prov_schema_db) -> None:
    """The database catalog exactly matches the Recommendation inventory."""
    with prov_schema_db.cursor() as cursor:
        cursor.execute("select count(*) from provenance_class_definition")
        assert cursor.fetchone()[0] == 30
        cursor.execute("select count(*) from provenance_relation_definition")
        assert cursor.fetchone()[0] == 50
        cursor.execute("select count(*) from provenance_qualification_definition")
        assert cursor.fetchone()[0] == 14
        cursor.execute("select count(*) from provenance_inverse_definition")
        assert cursor.fetchone()[0] == 44


def test_database_accepts_valid_generation_and_rejects_wrong_domain(prov_schema_db) -> None:
    """Recursive class-domain checks are enforced by PostgreSQL itself."""
    with prov_schema_db.cursor() as cursor:
        entity_id = _resource(cursor, "urn:test:entity", "prov_entity")
        activity_id = _resource(cursor, "urn:test:activity", "prov_activity")
        agent_id = _resource(cursor, "urn:test:agent", "prov_person")
        cursor.execute(
            "insert into provenance_assertion "
            "(subject_resource_id, relation_code, object_resource_id) "
            "values (%s, 'prov_was_generated_by', %s)",
            (entity_id, activity_id),
        )
        with pytest.raises(psycopg2.errors.RaiseException, match="violates PROV-O domain"):
            cursor.execute(
                "insert into provenance_assertion "
                "(subject_resource_id, relation_code, object_resource_id) "
                "values (%s, 'prov_was_derived_from', %s)",
                (agent_id, entity_id),
            )
    prov_schema_db.rollback()


def test_database_rejects_literal_for_object_property(prov_schema_db) -> None:
    """Object/datatype shape cannot be bypassed by direct SQL writes."""
    with prov_schema_db.cursor() as cursor:
        entity_id = _resource(cursor, "urn:test:shape-entity", "prov_entity")
        cursor.execute(
            "insert into provenance_literal_value (lexical_value) values ('bad') returning literal_id"
        )
        literal_id = cursor.fetchone()[0]
        with pytest.raises(psycopg2.errors.RaiseException, match="requires object_resource_id"):
            cursor.execute(
                "insert into provenance_assertion "
                "(subject_resource_id, relation_code, object_literal_id) "
                "values (%s, 'prov_was_derived_from', %s)",
                (entity_id, literal_id),
            )
    prov_schema_db.rollback()


def test_database_requires_xsd_datetime_for_event_time(prov_schema_db) -> None:
    """Date properties reject untyped lexical strings at the storage boundary."""
    with prov_schema_db.cursor() as cursor:
        activity_id = _resource(cursor, "urn:test:time-activity", "prov_activity")
        cursor.execute(
            "insert into provenance_literal_value (lexical_value) "
            "values ('2026-08-14T04:00:00Z') returning literal_id"
        )
        literal_id = cursor.fetchone()[0]
        with pytest.raises(psycopg2.errors.RaiseException, match="violates datatype"):
            cursor.execute(
                "insert into provenance_assertion "
                "(subject_resource_id, relation_code, object_literal_id) "
                "values (%s, 'prov_started_at_time', %s)",
                (activity_id, literal_id),
            )
    prov_schema_db.rollback()
