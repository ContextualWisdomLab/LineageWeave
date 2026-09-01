"""Real-PostgreSQL contract tests for the PROV-O migration.

The module applies the actual base and PROV-O migration files to a throwaway
database.  It self-skips when no local PostgreSQL is reachable, matching the
repository's existing real-database schema tests.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest

from lineageweave import postgres_sync as sync_postgres
from lineageweave.postgres_sync import sql

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
        connection = sync_postgres.connect(_ADMIN_DSN, connect_timeout=2)
        connection.close()
        return True
    except sync_postgres.OperationalError:
        return False


def _dsn_for_database(admin_dsn: str, database_name: str) -> str:
    """Replace only the database path while preserving DSN query options."""
    parsed_admin_dsn = urlsplit(admin_dsn)
    return urlunsplit(parsed_admin_dsn._replace(path=f"/{database_name}"))


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason=f"no reachable PostgreSQL server at {_ADMIN_DSN}",
)


@pytest.fixture
def prov_schema_db():
    """Yield a freshly migrated database and drop it after the test."""
    database_name = f"lineageweave_prov_{uuid.uuid4().hex[:12]}"
    admin_connection = sync_postgres.connect(_ADMIN_DSN)
    admin_connection.autocommit = True
    with admin_connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("create database {}").format(sql.Identifier(database_name))
        )
    try:
        database_dsn = _dsn_for_database(_ADMIN_DSN, database_name)
        connection = sync_postgres.connect(database_dsn)
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
            cursor.execute(
                sql.SQL("drop database {}").format(sql.Identifier(database_name))
            )
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
        with pytest.raises(sync_postgres.errors.RaiseException, match="violates PROV-O domain"):
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
        with pytest.raises(sync_postgres.errors.RaiseException, match="requires object_resource_id"):
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
        with pytest.raises(sync_postgres.errors.RaiseException, match="violates datatype"):
            cursor.execute(
                "insert into provenance_assertion "
                "(subject_resource_id, relation_code, object_literal_id) "
                "values (%s, 'prov_started_at_time', %s)",
                (activity_id, literal_id),
            )
    prov_schema_db.rollback()


def _literal(cursor, lexical_value: str, datatype_iri: str | None) -> str:
    """Insert one RDF literal and return its UUID."""
    cursor.execute(
        "insert into provenance_literal_value (lexical_value, datatype_iri) "
        "values (%s, %s) returning literal_id",
        (lexical_value, datatype_iri),
    )
    return str(cursor.fetchone()[0])


@pytest.mark.parametrize(
    "lexical_value",
    (
        "2026-08-14T04:00:00",
        "not-a-date",
        "2026-02-31T04:00:00Z",
        "2026-08-14T04:00:00+14:01",
    ),
)
def test_database_rejects_invalid_xsd_datetime(prov_schema_db, lexical_value: str) -> None:
    """Malformed and timezone-less xsd:dateTime values fail closed."""
    with prov_schema_db.cursor() as cursor:
        activity_id = _resource(cursor, "urn:test:strict-time", "prov_activity")
        literal_id = _literal(
            cursor,
            lexical_value,
            "http://www.w3.org/2001/XMLSchema#dateTime",
        )
        with pytest.raises(sync_postgres.errors.RaiseException, match="lexical xsd:dateTime"):
            cursor.execute(
                "insert into provenance_assertion "
                "(subject_resource_id, relation_code, object_literal_id) "
                "values (%s, 'prov_started_at_time', %s)",
                (activity_id, literal_id),
            )
    prov_schema_db.rollback()


def test_database_accepts_timezone_aware_xsd_datetime(prov_schema_db) -> None:
    """A valid timezone-aware dateTime reaches the assertion store."""
    with prov_schema_db.cursor() as cursor:
        activity_id = _resource(cursor, "urn:test:valid-time", "prov_activity")
        literal_id = _literal(
            cursor,
            "2026-08-14T04:00:00+09:00",
            "http://www.w3.org/2001/XMLSchema#dateTime",
        )
        cursor.execute(
            "insert into provenance_assertion "
            "(subject_resource_id, relation_code, object_literal_id) "
            "values (%s, 'prov_started_at_time', %s)",
            (activity_id, literal_id),
        )
    prov_schema_db.rollback()


def test_referenced_contract_rows_are_immutable(prov_schema_db) -> None:
    """Reference-table mutation cannot invalidate stored assertions."""
    with prov_schema_db.cursor() as cursor:
        entity_id = _resource(cursor, "urn:test:immutable-entity", "prov_entity")
        activity_id = _resource(cursor, "urn:test:immutable-activity", "prov_activity")
        cursor.execute(
            "insert into provenance_assertion "
            "(subject_resource_id, relation_code, object_resource_id) "
            "values (%s, 'prov_was_generated_by', %s)",
            (entity_id, activity_id),
        )
        with pytest.raises(sync_postgres.errors.RaiseException, match="types are immutable"):
            cursor.execute(
                "delete from provenance_resource_type "
                "where resource_id = %s and class_code = 'prov_activity'",
                (activity_id,),
            )
    prov_schema_db.rollback()

    with prov_schema_db.cursor() as cursor:
        activity_id = _resource(cursor, "urn:test:immutable-time", "prov_activity")
        literal_id = _literal(
            cursor,
            "2026-08-14T04:00:00Z",
            "http://www.w3.org/2001/XMLSchema#dateTime",
        )
        cursor.execute(
            "insert into provenance_assertion "
            "(subject_resource_id, relation_code, object_literal_id) "
            "values (%s, 'prov_started_at_time', %s)",
            (activity_id, literal_id),
        )
        with pytest.raises(sync_postgres.errors.RaiseException, match="literal values are immutable"):
            cursor.execute(
                "update provenance_literal_value set datatype_iri = null "
                "where literal_id = %s",
                (literal_id,),
            )
    prov_schema_db.rollback()
