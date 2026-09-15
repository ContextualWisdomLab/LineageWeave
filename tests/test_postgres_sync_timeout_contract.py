"""libpq timeout compatibility contract for the synchronous PostgreSQL adapter."""

from __future__ import annotations

import pytest

from lineageweave.postgres_sync import connection_kwargs_from_dsn


@pytest.mark.parametrize("timeout_value", ("0", "-1"))
def test_dsn_non_positive_connect_timeout_preserves_libpq_indefinite_semantics(
    timeout_value: str,
) -> None:
    """Zero or negative DSN timeouts must remain the libpq no-deadline sentinel."""
    kwargs = connection_kwargs_from_dsn(
        "postgresql://alice:secret@db.example/archive"
        f"?connect_timeout={timeout_value}"
    )

    assert "timeout" not in kwargs


@pytest.mark.parametrize("timeout_value", (0, -1))
def test_keyword_non_positive_connect_timeout_preserves_libpq_indefinite_semantics(
    timeout_value: int,
) -> None:
    """The psycopg-compatible keyword override keeps libpq's no-deadline sentinel."""
    kwargs = connection_kwargs_from_dsn(
        "postgresql://alice:secret@db.example/archive?connect_timeout=7",
        connect_timeout=timeout_value,
    )

    assert "timeout" not in kwargs


def test_dsn_connect_timeout_rejects_non_integer_text() -> None:
    """A libpq URI timeout is a decimal integer, not an arbitrary floating point value."""
    with pytest.raises(ValueError, match="decimal integer"):
        connection_kwargs_from_dsn(
            "postgresql://alice:secret@db.example/archive?connect_timeout=1.5"
        )
