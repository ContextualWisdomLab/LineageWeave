"""Live-PostgreSQL regressions for related-node affiliation display authority."""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path
from typing import Iterator

import asyncpg
import psycopg2
import pytest

from backend.app.knowledge_graph import hydrate_related_nodes
from lineageweave.knowledge_graph import NODE_PERSON, node_key


_POSTGRES_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN",
    "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave",
)
_MIGRATION_PATH = Path(__file__).resolve().parents[2] / "migrations" / "0001_initial_schema.sql"


def _postgres_available() -> bool:
    """Return whether the repository's local PostgreSQL integration stack is reachable."""
    try:
        psycopg2.connect(_POSTGRES_ADMIN_DSN, connect_timeout=2).close()
        return True
    except psycopg2.OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason="requires the local PostgreSQL integration stack -- run `make up` first",
)


@pytest.fixture(scope="module")
def affiliation_database() -> Iterator[tuple[str, str, str]]:
    """Create one migrated throwaway database with a person and catalog organization."""
    database_name = f"lineageweave_affiliation_test_{uuid.uuid4().hex[:12]}"
    admin_connection = psycopg2.connect(_POSTGRES_ADMIN_DSN)
    admin_connection.autocommit = True
    with admin_connection.cursor() as cursor:
        cursor.execute(f'create database "{database_name}"')

    database_dsn = _POSTGRES_ADMIN_DSN.rsplit("/", 1)[0] + f"/{database_name}"
    connection = psycopg2.connect(database_dsn)
    try:
        with connection.cursor() as cursor:
            cursor.execute(_MIGRATION_PATH.read_text(encoding="utf-8"))
            cursor.execute(
                "insert into common_lookup_value "
                "(lookup_category, lookup_code, lookup_label) values "
                "('person_side', 'counterparty', 'Counterparty'), "
                "('corporate_entity_level', 'company', 'Company')"
            )
            cursor.execute(
                "insert into cataloged_person (person_name, person_side_code) "
                "values ('Priya Nair', 'counterparty') returning person_id"
            )
            person_id = str(cursor.fetchone()[0])
            cursor.execute(
                "insert into corporate_entity "
                "(corporate_entity_code, entity_name, entity_level_code) "
                "values ('DEMO-CORP', 'Demo Corp', 'company') "
                "returning corporate_entity_id"
            )
            catalog_id = str(cursor.fetchone()[0])
        connection.commit()
        yield database_dsn, person_id, catalog_id
    finally:
        connection.close()
        with admin_connection.cursor() as cursor:
            cursor.execute(f'drop database "{database_name}"')
        admin_connection.close()


def _replace_affiliations(
    database_dsn: str,
    person_id: str,
    affiliations: list[tuple[str, str | None]],
) -> None:
    """Replace the fixture person's affiliation rows using the real schema."""
    connection = psycopg2.connect(database_dsn)
    try:
        with connection.cursor() as cursor:
            cursor.execute("delete from person_affiliation where person_id = %s", (person_id,))
            for organization_name, catalog_id in affiliations:
                cursor.execute(
                    "insert into person_affiliation "
                    "(person_id, affiliated_organization_name, affiliated_corporate_entity_id) "
                    "values (%s, %s, %s)",
                    (person_id, organization_name, catalog_id),
                )
        connection.commit()
    finally:
        connection.close()


def _hydrate(database_dsn: str, person_id: str) -> dict[str, object]:
    """Execute ``hydrate_related_nodes`` through a real asyncpg connection."""

    async def run() -> dict[str, object]:
        connection = await asyncpg.connect(database_dsn)
        try:
            payload = await hydrate_related_nodes(
                connection,
                [(node_key(NODE_PERSON, person_id), 0.8)],
            )
        finally:
            await connection.close()
        assert len(payload) == 1
        return payload[0]

    return asyncio.run(run())


def test_related_person_exposes_one_unambiguous_affiliation(
    affiliation_database: tuple[str, str, str],
) -> None:
    """A single unresolved affiliation survives the production SQL boundary."""
    database_dsn, person_id, _ = affiliation_database
    _replace_affiliations(database_dsn, person_id, [("Northridge Grid", None)])
    node = _hydrate(database_dsn, person_id)
    assert node["affiliation_organization_name"] == "Northridge Grid"
    assert node["person_side_label"] == "Counterparty"


def test_related_person_omits_affiliation_when_multiple_are_known(
    affiliation_database: tuple[str, str, str],
) -> None:
    """Multiple live affiliation rows cannot become an invented primary organization."""
    database_dsn, person_id, _ = affiliation_database
    _replace_affiliations(
        database_dsn,
        person_id,
        [("Northridge Grid", None), ("Northridge Holdings", None)],
    )
    node = _hydrate(database_dsn, person_id)
    assert "affiliation_organization_name" not in node


def test_related_person_omits_blank_affiliation(
    affiliation_database: tuple[str, str, str],
) -> None:
    """Whitespace-only stored evidence remains missing display context."""
    database_dsn, person_id, _ = affiliation_database
    _replace_affiliations(database_dsn, person_id, [("   ", None)])
    node = _hydrate(database_dsn, person_id)
    assert "affiliation_organization_name" not in node


def test_related_person_uses_catalog_name_for_one_resolved_org(
    affiliation_database: tuple[str, str, str],
) -> None:
    """The real left join supplies corporate_entity.entity_name for resolved evidence."""
    database_dsn, person_id, catalog_id = affiliation_database
    _replace_affiliations(database_dsn, person_id, [("Demo Corp Inc.", catalog_id)])
    node = _hydrate(database_dsn, person_id)
    assert node["affiliation_organization_name"] == "Demo Corp"


def test_related_person_collapses_aliases_of_one_catalog_org(
    affiliation_database: tuple[str, str, str],
) -> None:
    """Two rows bound to one catalog UUID remain one organization identity."""
    database_dsn, person_id, catalog_id = affiliation_database
    _replace_affiliations(
        database_dsn,
        person_id,
        [("Demo Corp Inc.", catalog_id), ("Demo Corp", catalog_id)],
    )
    node = _hydrate(database_dsn, person_id)
    assert node["affiliation_organization_name"] == "Demo Corp"


def test_related_person_collapses_unresolved_name_matching_catalog(
    affiliation_database: tuple[str, str, str],
) -> None:
    """An unresolved case variant of the catalog label is not a second identity."""
    database_dsn, person_id, catalog_id = affiliation_database
    _replace_affiliations(
        database_dsn,
        person_id,
        [("Demo Corp", catalog_id), ("demo corp", None)],
    )
    node = _hydrate(database_dsn, person_id)
    assert node["affiliation_organization_name"] == "Demo Corp"


def test_related_person_omits_resolved_plus_distinct_unresolved(
    affiliation_database: tuple[str, str, str],
) -> None:
    """A catalog organization plus a distinct unresolved row remains ambiguous."""
    database_dsn, person_id, catalog_id = affiliation_database
    _replace_affiliations(
        database_dsn,
        person_id,
        [("Demo Corp", catalog_id), ("Northridge Holdings", None)],
    )
    node = _hydrate(database_dsn, person_id)
    assert "affiliation_organization_name" not in node
