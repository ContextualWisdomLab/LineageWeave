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


class _SQL(str):
    def format(self, *args: object, **kwargs: object) -> str:
        positional = tuple(str(value) for value in args)
        named = {key: str(value) for key, value in kwargs.items()}
        return str(self).format(*positional, **named)


sql = SimpleNamespace(SQL=_SQL, Identifier=_Identifier)


def _ssl_context_for_mode(mode: str) -> ssl.SSLContext | bool | None:
    normalized = mode.lower()
    if normalized == "disable":
        return False
    if normalized == "prefer":
        return None
    if normalized == "require":
        return True
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
    """

    parsed = urlsplit(dsn)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("PostgreSQL DSN must use postgres:// or postgresql://")
    if parsed.username is None:
        raise ValueError("PostgreSQL DSN must include a user")
    if not parsed.path or parsed.path == "/":
        raise ValueError("PostgreSQL DSN must include a database name")

    kwargs: dict[str, Any] = {
        "user": unquote(parsed.username),
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
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
        timeout = float(timeout_value)
        if timeout <= 0:
            raise ValueError("PostgreSQL connect_timeout must be positive")
        kwargs["timeout"] = timeout

    if "application_name" in query:
        if not query["application_name"]:
            raise ValueError("PostgreSQL application_name must not be empty")
        kwargs["application_name"] = query["application_name"]
    if "sslmode" in query:
        kwargs["ssl_context"] = _ssl_context_for_mode(query["sslmode"])
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
        "23505": UniqueViolation,
        "23514": CheckViolation,
        "23P01": ExclusionViolation,
        "42501": InsufficientPrivilege,
        "P0001": RaiseException,
    }.get(state)
    if translated_type is None:
        return error
    return translated_type(*getattr(error, "args", ()))


class Cursor:
    """Thin cursor wrapper that preserves the SQLSTATE-specific test contract."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def execute(self, operation: str, args: object | None = None, **kwargs: object) -> Any:
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
        try:
            return self._inner.executemany(operation, param_sets)
        except _dbapi.DatabaseError as exc:
            translated = _translated_error(exc)
            if translated is exc:
                raise
            raise translated from exc

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    def __enter__(self) -> "Cursor":
        self._inner.__enter__()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> object:
        return self._inner.__exit__(exc_type, exc, traceback)


class Connection:
    """Connection proxy that keeps pg8000 isolated from repository call sites."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    @property
    def autocommit(self) -> bool:
        return bool(self._inner.autocommit)

    @autocommit.setter
    def autocommit(self, value: bool) -> None:
        self._inner.autocommit = value

    def cursor(self, *args: object, **kwargs: object) -> Cursor:
        return Cursor(self._inner.cursor(*args, **kwargs))

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    def __enter__(self) -> "Connection":
        self._inner.__enter__()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> object:
        return self._inner.__exit__(exc_type, exc, traceback)


def connect(dsn: str, *, connect_timeout: float | int | None = None) -> Connection:
    """Open the repository's synchronous pg8000 connection boundary."""

    kwargs = connection_kwargs_from_dsn(dsn, connect_timeout=connect_timeout)
    try:
        return Connection(_dbapi.connect(**kwargs))
    except _dbapi.InterfaceError as exc:
        raise OperationalError(*getattr(exc, "args", ())) from exc
