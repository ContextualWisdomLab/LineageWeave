"""PostgreSQL excerpt skip messages keep deployment connection details private."""

from pathlib import Path
import runpy
from unittest.mock import Mock

import psycopg2


def test_unavailable_excerpt_postgres_skip_keeps_connection_details_private(monkeypatch):
    """Collection exposes an actionable reason without echoing a DSN or error."""
    dsn = "postgresql://synthetic_admin:synthetic_secret@synthetic-db.invalid/private_db"
    monkeypatch.setenv("LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", dsn)
    connect = Mock(side_effect=psycopg2.OperationalError(dsn))
    monkeypatch.setattr(psycopg2, "connect", connect)

    namespace = runpy.run_path(str(Path(__file__).with_name("test_source_post_excerpt_live.py")))

    connect.assert_called_once_with(dsn, connect_timeout=2)
    mark = namespace["pytestmark"]
    assert mark.args == (True,)
    reason = mark.kwargs["reason"]
    assert "PostgreSQL" in reason
    for private_value in (
        dsn,
        "synthetic_admin",
        "synthetic_secret",
        "synthetic-db",
        "private_db",
    ):
        assert private_value not in reason
