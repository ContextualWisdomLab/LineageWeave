"""Synchronous PostgreSQL adapter for admin, seed, and schema tooling.

The application runtime uses ``asyncpg``. A few administrative and integration
paths still need a blocking DB-API connection, chiefly to create ephemeral test
databases and to run the synthetic seed. This module keeps that secondary
boundary provider-specific in one place and deliberately exposes only the
behaviour LineageWeave needs.

Connection URIs are parsed explicitly because pg8000 accepts keyword arguments
rather than libpq DSN strings. Unsupported query options fail closed instead
of disappearing during the driver migration. Generated SQL identifiers are
quoted locally; values must continue to use DB-API parameters. Server errors
used as executable schema/security contracts are translated by SQLSTATE so the
tests retain their semantic assertions without depending on a driver taxonomy.
"""

from __future__ import annotations

import getpass
import math
import ssl
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Mapping
from urllib.parse import parse_qsl, unquote, urlsplit

import pg8000.dbapi as _dbapi


class DatabaseError(_dbapi.DatabaseError):
    """Base class for translated server errors carrying PostgreSQL SQLSTATE."""


class OperationalError(_dbapi.InterfaceError):
    """Connection/setup error used by reachability probes."""


class NotNullViolation(DatabaseError):
    """PostgreSQL SQLSTATE 23502: a mandatory column was omitted or nulled."""


class UniqueViolation(DatabaseError):
    """PostgreSQL SQLSTATE 23505: a uniqueness constraint rejected the statement."""


class ForeignKeyViolation(DatabaseError):
    """PostgreSQL SQLSTATE 23503: a foreign-key constraint rejected the statement."""


class CheckViolation(DatabaseError):
    """PostgreSQL SQLSTATE 23514: a CHECK constraint rejected the statement."""


class ExclusionViolation(DatabaseError):
    """PostgreSQL SQLSTATE 23P01: an exclusion constraint rejected the statement."""


class InsufficientPrivilege(DatabaseError):
    """PostgreSQL SQLSTATE 42501: the current role lacks the required privilege."""


class RaiseException(DatabaseError):
    """PostgreSQL SQLSTATE P0001: server-side ``RAISE EXCEPTION``."""


errors = SimpleNamespace(
    NotNullViolation=NotNullViolation,
    UniqueViolation=UniqueViolation,
    ForeignKeyViolation=ForeignKeyViolation,
    CheckViolation=CheckViolation,
    ExclusionViolation=ExclusionViolation,
    InsufficientPrivilege=InsufficientPrivilege,
    RaiseException=RaiseException,
)


def _quote_identifier(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("PostgreSQL identifier must be a non-empty string")
    if "\x00" in value:
        raise ValueError("PostgreSQL identifier must not contain NUL")
    return '"' + value.replace('"', '""') + '"'


@dataclass(frozen=True)
class _Identifier:
    value: str

    def __str__(self) -> str:
        return _quote_identifier(self.value)


def _render_sql_composable(value: object) -> str:
    """Render only the adapter's explicitly safe dynamic SQL fragment types.

    Raw strings are rejected because accepting them would turn ``SQL.format``
    into an injection-capable text interpolation API. Callers must wrap dynamic
    database and role names with ``Identifier``; static SQL fragments may use
    ``SQL`` explicitly.
    """

    if isinstance(value, (_Identifier, _SQL)):
        return str(value)
    raise TypeError("SQL interpolation requires sql.Identifier or sql.SQL")


class _SQL(str):
    def format(self, *args: object, **kwargs: object) -> str:
        """Interpolate only explicitly safe SQL composable fragments."""
        positional = tuple(_render_sql_composable(value) for value in args)
        named = {key: _render_sql_composable(value) for key, value in kwargs.items()}
        return str(self).format(*positional, **named)


sql = SimpleNamespace(SQL=_SQL, Identifier=_Identifier)


def _encryption_only_ssl_context() -> ssl.SSLContext:
    """Create the non-verifying TLS context used by libpq prefer/require semantics."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def _ssl_context_for_mode(mode: str) -> ssl.SSLContext | bool | None:
    normalized = mode.lower()
    if normalized == "disable":
        return False
    if normalized == "prefer":
        return _encryption_only_ssl_context()
    if normalized == "require":
        return _encryption_only_ssl_context()
    if normalized == "verify-ca":
        context = ssl.create_default_context()
        context.check_hostname = False
        return context
    if normalized == "verify-full":
        return ssl.create_default_context()
    raise ValueError(f"unsupported PostgreSQL sslmode: {mode}")


def connection_kwargs_from_dsn(
    dsn: str,
    *,
    connect_timeout: float | int | None = None,
) -> dict[str, Any]:
    """Translate one PostgreSQL URI into explicit pg8000 connection arguments.

    ``connect_timeout`` passed by the caller takes precedence over the URI's
    ``connect_timeout`` query value, matching the old call sites. Query
    options are allow-listed because silently discarding a libpq option could
    weaken transport security or alter session semantics. Duplicate options
    are rejected because collapsing conflicting values would make the selected
    connection policy depend on parser ordering rather than explicit intent.

    Libpq-style URIs may omit the username and then use the operating-system
    account. Several repository PostgreSQL test fixtures rely on that default,
    so the adapter resolves it explicitly before entering pg8000's required
    ``user`` argument rather than changing fixture connection semantics.

    A URI without a host is different: libpq interprets it as a local Unix-
    domain socket connection, while pg8000's omitted ``host`` defaults to
    localhost TCP. The URI alone does not identify which Unix socket path
    libpq would have selected, so this adapter rejects that ambiguous transport
    rather than silently changing peer-authentication and network semantics.
    """

    parsed = urlsplit(dsn)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("PostgreSQL DSN must use postgres:// or postgresql://")
    if parsed.fragment:
        raise ValueError("PostgreSQL DSN must not include a fragment")
    if not parsed.path or parsed.path == "/":
        raise ValueError("PostgreSQL DSN must include a database name")
    if parsed.hostname is None:
        raise ValueError("PostgreSQL DSN must include an explicit host")

    user = unquote(parsed.username) if parsed.username is not None else getpass.getuser()
    if not user:
        raise ValueError("PostgreSQL user could not be resolved")

    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("PostgreSQL port must be between 1 and 65535") from exc
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("PostgreSQL port must be between 1 and 65535")

    kwargs: dict[str, Any] = {
        "user": user,
        "host": parsed.hostname,
        "port": 5432 if port is None else port,
        "database": unquote(parsed.path.lstrip("/")),
    }
    if parsed.password is not None:
        kwargs["password"] = unquote(parsed.password)

    startup_params: dict[str, str] = {}
    query_items = parse_qsl(parsed.query, keep_blank_values=True)
    seen_query_options: set[str] = set()
    for option_name, _ in query_items:
        if option_name in seen_query_options:
            raise ValueError(f"duplicate PostgreSQL DSN option: {option_name}")
        seen_query_options.add(option_name)
    query = dict(query_items)
    supported = {"connect_timeout", "application_name", "sslmode", "options"}
    unknown = sorted(set(query) - supported)
    if unknown:
        raise ValueError(f"unsupported PostgreSQL DSN option: {unknown[0]}")

    timeout_value = connect_timeout
    if timeout_value is None and "connect_timeout" in query:
        try:
            timeout_value = float(query["connect_timeout"])
        except ValueError as exc:
            raise ValueError("PostgreSQL connect_timeout must be numeric") from exc
    if timeout_value is not None:
        if isinstance(timeout_value, bool):
            raise TypeError("PostgreSQL connect_timeout must be a real number")
        try:
            timeout = float(timeout_value)
        except OverflowError as exc:
            raise ValueError("PostgreSQL connect_timeout must be finite positive") from exc
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("PostgreSQL connect_timeout must be finite positive")
        kwargs["timeout"] = timeout

    if "application_name" in query:
        if not query["application_name"]:
            raise ValueError("PostgreSQL application_name must not be empty")
        kwargs["application_name"] = query["application_name"]
    kwargs["ssl_context"] = _ssl_context_for_mode(query.get("sslmode", "prefer"))
    if "options" in query:
        startup_params["options"] = query["options"]
    if startup_params:
        kwargs["startup_params"] = startup_params
    return kwargs


def _sqlstate(error: BaseException) -> str | None:
    for arg in getattr(error, "args", ()):
        if isinstance(arg, Mapping):
            state = arg.get("C")
            if isinstance(state, str):
                return state
    return None


def _translated_error(error: BaseException) -> BaseException:
    state = _sqlstate(error)
    translated_type = {
        "23502": NotNullViolation,
        "23503": ForeignKeyViolation,
        "23505": UniqueViolation,
        "23514": CheckViolation,
        "23P01": ExclusionViolation,
        "42501": InsufficientPrivilege,
        "P0001": RaiseException,
    }.get(state)
    if translated_type is None:
        return error
    return translated_type(*getattr(error, "args", ()))


def _server_refused_ssl(error: BaseException) -> bool:
    """Return whether pg8000 reported PostgreSQL's explicit SSL refusal byte."""
    return any(
        isinstance(arg, str) and arg.strip().lower() == "server refuses ssl"
        for arg in getattr(error, "args", ())
    )


class Cursor:
    """Thin cursor wrapper that preserves the SQLSTATE-specific test contract."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def execute(self, operation: str, args: object | None = None, **kwargs: object) -> Any:
        """Execute one statement while translating supported PostgreSQL SQLSTATEs."""
        try:
            if args is None:
                return self._inner.execute(operation, **kwargs)
            return self._inner.execute(operation, args, **kwargs)
        except _dbapi.DatabaseError as exc:
            translated = _translated_error(exc)
            if translated is exc:
                raise
            raise translated from exc

    def executemany(self, operation: str, param_sets: object) -> Any:
        """Execute a statement for many parameter sets with SQLSTATE translation."""
        try:
            return self._inner.executemany(operation, param_sets)
        except _dbapi.DatabaseError as exc:
            translated = _translated_error(exc)
            if translated is exc:
                raise
            raise translated from exc

    def fetchone(self) -> tuple[Any, ...] | None:
        """Return one DB-API row with the tuple shape existing callers expect."""
        row = self._inner.fetchone()
        return None if row is None else tuple(row)

    def fetchall(self) -> list[tuple[Any, ...]]:
        """Return all DB-API rows as tuples rather than pg8000's mutable lists."""
        return [tuple(row) for row in self._inner.fetchall()]

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    def __enter__(self) -> "Cursor":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> object:
        self._inner.close()
        return False


class Connection:
    """Connection proxy that keeps pg8000 isolated from repository call sites."""

    def __init__(self, inner: Any, *, database: str) -> None:
        self._inner = inner
        self.info = SimpleNamespace(dbname=database)

    @property
    def autocommit(self) -> bool:
        """Return the native connection's current autocommit setting."""
        return bool(self._inner.autocommit)

    @autocommit.setter
    def autocommit(self, value: bool) -> None:
        """Set autocommit on the isolated native pg8000 connection."""
        self._inner.autocommit = value

    def cursor(self, *args: object, **kwargs: object) -> Cursor:
        """Create a cursor wrapped by the adapter's SQLSTATE boundary."""
        return Cursor(self._inner.cursor(*args, **kwargs))

    def commit(self) -> None:
        """Commit while preserving SQLSTATE-specific adapter error types."""
        try:
            self._inner.commit()
        except _dbapi.DatabaseError as exc:
            translated = _translated_error(exc)
            if translated is exc:
                raise
            raise translated from exc

    def rollback(self) -> None:
        """Roll back while preserving SQLSTATE-specific adapter error types."""
        try:
            self._inner.rollback()
        except _dbapi.DatabaseError as exc:
            translated = _translated_error(exc)
            if translated is exc:
                raise
            raise translated from exc

    def close(self) -> None:
        """Close the native connection, tolerating repeated cleanup calls."""
        try:
            self._inner.close()
        except _dbapi.InterfaceError as exc:
            if "connection is closed" not in str(exc).lower():
                raise

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    def __enter__(self) -> "Connection":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> object:
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        return False


def connect(dsn: str, *, connect_timeout: float | int | None = None) -> Connection:
    """Open the repository's synchronous pg8000 connection boundary.

    pg8000 reports transport failures as ``InterfaceError`` and PostgreSQL
    startup refusals such as authentication/database errors as ``DatabaseError``.
    Both occur before a connection exists and therefore preserve the historical
    ``OperationalError`` contract used by reachability probes. Libpq's default
    ``sslmode=prefer`` is preserved by trying encrypted transport first and
    falling back to plaintext only when PostgreSQL explicitly refuses SSL.
    """

    parsed = urlsplit(dsn)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    sslmode = query.get("sslmode", "prefer").lower()
    kwargs = connection_kwargs_from_dsn(dsn, connect_timeout=connect_timeout)
    try:
        native = _dbapi.connect(**kwargs)
    except _dbapi.InterfaceError as exc:
        if sslmode != "prefer" or not _server_refused_ssl(exc):
            raise OperationalError(*getattr(exc, "args", ())) from exc
        fallback_kwargs = dict(kwargs)
        fallback_kwargs["ssl_context"] = False
        try:
            native = _dbapi.connect(**fallback_kwargs)
        except (_dbapi.InterfaceError, _dbapi.DatabaseError) as fallback_exc:
            raise OperationalError(*getattr(fallback_exc, "args", ())) from fallback_exc
    except _dbapi.DatabaseError as exc:
        raise OperationalError(*getattr(exc, "args", ())) from exc
    return Connection(native, database=str(kwargs["database"]))
