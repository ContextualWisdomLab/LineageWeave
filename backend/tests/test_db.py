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
        "min_size": 1,
        "max_size": 10,
        "server_settings": {"jit": "off"},
    }
