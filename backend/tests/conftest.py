"""Shared real-database migration setup for backend integration tests."""

from __future__ import annotations

from pathlib import Path

import psycopg2
import pytest

_LINEAGE_EVIDENCE_MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "0055_lineage_edge_channel_score.sql"
)


@pytest.fixture(autouse=True)
def apply_lineage_evidence_migration(request: pytest.FixtureRequest):
    """Apply migration 0055 before any test consumes ``seeded_db``.

    ``backend.tests.test_api.seeded_db`` owns the full base migration chain.
    Keeping this additive slice here avoids duplicating that very large fixture
    while ensuring its real API client never exercises channel-evidence code
    against a database that lacks the new normalized authority.
    """

    if "seeded_db" not in request.fixturenames:
        yield
        return

    seeded_db = request.getfixturevalue("seeded_db")
    connection = psycopg2.connect(seeded_db["dsn"])
    try:
        with connection.cursor() as cursor:
            cursor.execute(_LINEAGE_EVIDENCE_MIGRATION.read_text(encoding="utf-8"))
        connection.commit()
    finally:
        connection.close()
    yield
