"""Transport-order contract for the synchronous PostgreSQL compatibility boundary."""

from __future__ import annotations

import ssl
from types import SimpleNamespace

import pg8000.dbapi as _dbapi
import pytest

from lineageweave.postgres_sync import OperationalError, connect


@pytest.mark.parametrize(
    "dsn",
    (
        "postgresql://alice:secret@db.example/archive",
        "postgresql://alice:secret@db.example/archive?sslmode=prefer",
    ),
)
def test_libpq_prefer_semantics_attempt_tls_before_plaintext_fallback(
    monkeypatch: pytest.MonkeyPatch,
    dsn: str,
) -> None:
    """Default/explicit prefer must try encrypted transport before server-refusal fallback."""
    attempts: list[object] = []
    native_connection = SimpleNamespace(autocommit=False)

    def fake_connect(**kwargs: object) -> object:
        ssl_context = kwargs["ssl_context"]
        attempts.append(ssl_context)
        if len(attempts) == 1:
            assert isinstance(ssl_context, ssl.SSLContext)
            assert ssl_context.check_hostname is False
            assert ssl_context.verify_mode == ssl.CERT_NONE
            raise _dbapi.InterfaceError("Server refuses SSL")
        assert ssl_context is False
        return native_connection

    monkeypatch.setattr("lineageweave.postgres_sync._dbapi.connect", fake_connect)

    connection = connect(dsn)

    assert connection._inner is native_connection
    assert len(attempts) == 2


def test_prefer_does_not_downgrade_on_arbitrary_transport_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Plaintext fallback is limited to an explicit PostgreSQL SSL refusal."""
    attempts = 0

    def fail_connect(**kwargs: object) -> object:
        nonlocal attempts
        attempts += 1
        assert isinstance(kwargs["ssl_context"], ssl.SSLContext)
        raise _dbapi.InterfaceError("network path failed during TLS negotiation")

    monkeypatch.setattr("lineageweave.postgres_sync._dbapi.connect", fail_connect)

    with pytest.raises(OperationalError):
        connect("postgresql://alice:secret@db.example/archive?sslmode=prefer")

    assert attempts == 1


def test_libpq_require_encrypts_without_implicit_certificate_verification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require must force TLS without silently becoming verify-ca/verify-full."""
    attempts = 0
    native_connection = SimpleNamespace(autocommit=False)

    def fake_connect(**kwargs: object) -> object:
        nonlocal attempts
        attempts += 1
        ssl_context = kwargs["ssl_context"]
        assert isinstance(ssl_context, ssl.SSLContext)
        assert ssl_context.check_hostname is False
        assert ssl_context.verify_mode == ssl.CERT_NONE
        return native_connection

    monkeypatch.setattr("lineageweave.postgres_sync._dbapi.connect", fake_connect)

    connection = connect("postgresql://alice:secret@db.example/archive?sslmode=require")

    assert connection._inner is native_connection
    assert attempts == 1
