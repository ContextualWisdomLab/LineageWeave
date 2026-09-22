"""Naming and boundary contracts for explicit post-content requeue."""

from __future__ import annotations

import ast
import asyncio
import contextlib
import io
import runpy
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT_PATH = Path("scripts/requeue_failed_post_content.py")


class _DatabaseTransaction:
    """Record entry and exit of the database transaction boundary."""

    def __init__(self, operation_events: list[str]) -> None:
        self.operation_events = operation_events

    async def __aenter__(self) -> None:
        self.operation_events.append("transaction_entered")

    async def __aexit__(self, *_exception_details: object) -> None:
        self.operation_events.append("transaction_exited")


class _DatabaseConnection:
    """Minimal asyncpg-compatible connection for the operator contract."""

    def __init__(self, operation_events: list[str]) -> None:
        self.operation_events = operation_events
        self.connection_closed = False

    async def fetchrow(self, query_text: str, post_identifier: str) -> dict[str, str]:
        """Return one source post body and record the bound query."""
        self.operation_events.append(f"fetch:{post_identifier}:{query_text}")
        return {"post_body": "bounded body"}

    def transaction(self) -> _DatabaseTransaction:
        """Return the recorded transaction context."""
        return _DatabaseTransaction(self.operation_events)

    async def close(self) -> None:
        """Record database resource closure."""
        self.connection_closed = True


class _ValkeyClient:
    """Minimal redis-compatible client for the publication contract."""

    def __init__(self) -> None:
        self.client_closed = False

    async def aclose(self) -> None:
        """Record Valkey resource closure."""
        self.client_closed = True


def _load_requeue_script(
    database_connection: _DatabaseConnection,
    valkey_client: _ValkeyClient,
    operation_events: list[str],
) -> dict[str, object]:
    """Load the operator with bounded database and Valkey adapters."""

    async def connect_database(_target_dsn: str) -> _DatabaseConnection:
        return database_connection

    async def requeue_failed_job(
        received_connection: _DatabaseConnection,
        post_identifier: str,
        source_post_body: str,
    ) -> SimpleNamespace:
        assert received_connection is database_connection
        operation_events.append(f"requeued:{post_identifier}:{source_post_body}")
        return SimpleNamespace(
            post_id=post_identifier,
            source_body_sha256="digest",
            status_code="pending",
        )

    async def publish_retry_event(
        received_client: _ValkeyClient,
        *,
        post_id: str,
        source_body_digest: str,
    ) -> str:
        assert received_client is valkey_client
        operation_events.append(f"published:{post_id}:{source_body_digest}")
        return "stream-entry-1"

    asyncpg_module = types.ModuleType("asyncpg")
    asyncpg_module.connect = connect_database  # type: ignore[attr-defined]
    redis_package = types.ModuleType("redis")
    redis_package.__path__ = []  # type: ignore[attr-defined]
    redis_asyncio_module = types.ModuleType("redis.asyncio")
    redis_asyncio_module.from_url = (  # type: ignore[attr-defined]
        lambda _valkey_url, *, decode_responses: valkey_client
    )
    redis_package.asyncio = redis_asyncio_module  # type: ignore[attr-defined]
    backend_package = types.ModuleType("backend")
    backend_package.__path__ = []  # type: ignore[attr-defined]
    backend_app_package = types.ModuleType("backend.app")
    backend_app_package.__path__ = []  # type: ignore[attr-defined]
    config_module = types.ModuleType("backend.app.config")
    config_module.load_settings = lambda: None  # type: ignore[attr-defined]
    queue_module = types.ModuleType("backend.app.post_content_queue")
    queue_module.requeue_failed_post_content_job = requeue_failed_job  # type: ignore[attr-defined]
    queue_module.publish_post_content_event = publish_retry_event  # type: ignore[attr-defined]
    module_overrides = {
        "asyncpg": asyncpg_module,
        "redis": redis_package,
        "redis.asyncio": redis_asyncio_module,
        "backend": backend_package,
        "backend.app": backend_app_package,
        "backend.app.config": config_module,
        "backend.app.post_content_queue": queue_module,
    }
    with patch.dict(sys.modules, module_overrides):
        return runpy.run_path(str(SCRIPT_PATH), run_name="requeue_script_test")


def test_post_content_requeue_preserves_transaction_publication_and_close() -> None:
    """Publish only after the transaction and close both owned resources."""
    operation_events: list[str] = []
    database_connection = _DatabaseConnection(operation_events)
    valkey_client = _ValkeyClient()
    script_namespace = _load_requeue_script(
        database_connection,
        valkey_client,
        operation_events,
    )
    output_buffer = io.StringIO()

    with contextlib.redirect_stdout(output_buffer):
        asyncio.run(
            script_namespace["requeue_post_content"](
                "post-1",
                target_dsn="postgresql://lineageweave",
                valkey_url="redis://lineageweave",
            )
        )

    assert operation_events[1:] == [
        "transaction_entered",
        "requeued:post-1:bounded body",
        "transaction_exited",
        "published:post-1:digest",
    ]
    assert database_connection.connection_closed is True
    assert valkey_client.client_closed is True
    assert ast.literal_eval(output_buffer.getvalue()) == {
        "post_id": "post-1",
        "status": "pending",
        "published": True,
    }


def test_post_content_requeue_uses_semantic_owned_identifiers() -> None:
    """Keep command, database, queue, request, and settings names specific."""
    script_source = SCRIPT_PATH.read_text(encoding="utf-8")
    syntax_tree = ast.parse(script_source)
    owned_identifiers = {
        syntax_node.id
        for syntax_node in ast.walk(syntax_tree)
        if isinstance(syntax_node, ast.Name)
    }
    owned_identifiers.update(
        syntax_node.arg
        for syntax_node in ast.walk(syntax_tree)
        if isinstance(syntax_node, ast.arg)
    )
    owned_identifiers.update(
        syntax_node.name
        for syntax_node in ast.walk(syntax_tree)
        if isinstance(syntax_node, (ast.AsyncFunctionDef, ast.FunctionDef))
    )

    assert owned_identifiers.isdisjoint(
        {
            "_parser",
            "args",
            "client",
            "connection",
            "parser",
            "request",
            "settings",
        }
    )
    assert {
        "_post_content_requeue_parser",
        "command_arguments",
        "command_parser",
        "database_connection",
        "post_content_job_request",
        "runtime_settings",
        "source_post_body_row",
        "valkey_client",
        "valkey_stream_entry_id",
    } <= owned_identifiers


def test_post_content_requeue_preserves_operator_and_resource_contracts() -> None:
    """Keep CLI, SQL, output, publication, and close behavior stable."""
    script_source = SCRIPT_PATH.read_text(encoding="utf-8")

    for contract_literal in (
        '"--post-id"',
        '"--target-dsn"',
        '"--valkey-url"',
        '"select post_body from source_post where post_id = $1::uuid"',
        '"post_id"',
        '"status"',
        '"published"',
        "requeue_failed_post_content_job(",
        "publish_post_content_event(",
        "await database_connection.close()",
        "await valkey_client.aclose()",
    ):
        assert contract_literal in script_source
    assert "asyncio.run(\n        requeue_post_content(" in script_source
