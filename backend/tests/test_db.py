"""Database pool configuration tests."""

import asyncio

from backend.app import db


def test_pool_disables_measured_short_query_jit(monkeypatch) -> None:
    """Connections avoid PostgreSQL JIT startup on latency-bounded reads."""
    captured: dict[str, object] = {}

    async def fake_create_pool(database_url: str, **kwargs: object) -> object:
        captured.update(database_url=database_url, **kwargs)
        return object()

    monkeypatch.setattr(db.asyncpg, "create_pool", fake_create_pool)

    asyncio.run(db.create_pool("postgresql://synthetic"))

    assert captured == {
        "database_url": "postgresql://synthetic",
        "min_size": 10,
        "max_size": 10,
        "max_cacheable_statement_size": 0,
        "server_settings": {"jit": "off", "plan_cache_mode": "force_generic_plan"},
        "init": db._initialize_connection,
        "reset": db._reset_connection,
    }


def test_pool_initialization_loads_auth_array_codecs(monkeypatch) -> None:
    """Every new connection loads UUID/text arrays before serving reads."""
    calls: list[str] = []

    class Connection:
        """Capture the initialization statement."""

        async def fetchrow(self, query: str, *args: object) -> None:
            """Record the query without a database."""
            calls.append(query)

    async def warm(connection: object) -> None:
        assert isinstance(connection, Connection)
        calls.append("voice-read-statements-warmed")

    async def warm_dashboard(connection: object) -> None:
        assert isinstance(connection, Connection)
        calls.append("dashboard-read-statements-warmed")

    async def warm_customer(connection: object) -> None:
        assert isinstance(connection, Connection)
        calls.append("customer-read-paths-warmed")

    async def warm_posts(connection: object) -> None:
        assert isinstance(connection, Connection)
        calls.append("post-read-paths-warmed")

    monkeypatch.setattr(db, "warm_voice_taxonomy_read_statements", warm)
    monkeypatch.setattr(db, "warm_operations_dashboard_read_statements", warm_dashboard)
    monkeypatch.setattr(db, "warm_customer_master_read_paths", warm_customer)
    monkeypatch.setattr(db, "warm_post_list_read_paths", warm_posts)

    asyncio.run(db._initialize_connection(Connection()))  # type: ignore[arg-type]

    assert calls == [
        "select array[]::uuid[] as uuid_values, array[]::text[] as text_values",
        "dashboard-read-statements-warmed",
        "voice-read-statements-warmed",
        "customer-read-paths-warmed",
        "post-read-paths-warmed",
    ]
