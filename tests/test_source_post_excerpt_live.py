"""Live PostgreSQL contract for ADR 0053's bounded excerpt normalization.

Skipped unless a local PostgreSQL server is reachable
(LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN). Synthetic bodies only.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg2
import pytest

_ADMIN_DSN = os.environ.get(
    "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN", "postgresql://localhost/postgres"
)
_MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"
_PREFIX = 16384


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


@pytest.fixture(scope="module")
def cursor():
    """Throwaway database holding only the two excerpt functions."""
    name = f"lineageweave_excerpt_{uuid.uuid4().hex[:12]}"
    admin = psycopg2.connect(_ADMIN_DSN)
    admin.autocommit = True
    with admin.cursor() as admin_cursor:
        admin_cursor.execute(f'create database "{name}"')
    conn = psycopg2.connect(urlunsplit(urlsplit(_ADMIN_DSN)._replace(path=f"/{name}")))
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            search_sql = (_MIGRATIONS / "0036_normalized_body_search.sql").read_text()
            cur.execute(search_sql.split("create index", 1)[0])
            for _ in range(2):  # replay is part of the migration contract
                cur.execute((_MIGRATIONS / "0252_source_post_excerpt_text.sql").read_text())
            yield cur
    finally:
        conn.close()
        with admin.cursor() as admin_cursor:
            admin_cursor.execute(f'drop database "{name}"')
        admin.close()


_BODIES = [
    None,
    "",
    "  short <b>body</b>  ",
    "<p>" + "word " * 5000 + "</p>",
    # A tag straddles the 16,384-character prefix boundary.
    "x" * (_PREFIX - 5) + '<img src="data:image/png;base64,' + "A" * 9000 + '"> tail ' * 80,
    # The prefix normalizes to fewer than 420 characters, forcing the full-body fallback.
    "<img " + "a" * (_PREFIX + 100) + ">" + "visible text " * 100,
    # Whitespace runs that cross the boundary collapse the same way.
    "lead " + " " * (_PREFIX + 10) + "after " * 200,
    "<div>" + "가나다 " * 9000 + "</div>",
]


@pytest.mark.parametrize("body", _BODIES)
@pytest.mark.parametrize("max_chars", [1, 420])
def test_bounded_excerpt_equals_full_normalization(cursor, body, max_chars) -> None:
    """The prefix bound changes cost, never the excerpt a reader sees."""
    cursor.execute(
        "select source_post_excerpt_text(%s, %s), "
        "btrim(left(source_post_search_text(%s), %s))",
        (body, max_chars, body, max_chars),
    )
    bounded, full = cursor.fetchone()
    assert bounded == full
