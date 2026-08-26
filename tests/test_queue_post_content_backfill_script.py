"""The operator CLI reuses the bounded durable producer."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from scripts import queue_post_content_backfill as script


def test_parser_and_main_keep_the_operator_page_bounded(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The executable accepts one bounded page and prints aggregate evidence."""
    parser = script._parser()
    assert parser.parse_args(["--limit", "200"]).limit == 200
    with pytest.raises(SystemExit):
        parser.parse_args(["--limit", "201"])

    async def queue(*_args: object, **kwargs: object) -> dict[str, int]:
        assert kwargs == {"limit": 7}
        return {"queued_posts": 2}

    monkeypatch.setattr(
        script,
        "_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(
                target_dsn="postgresql://invalid",
                valkey_url="redis://invalid",
                limit=7,
            )
        ),
    )
    monkeypatch.setattr(script, "queue_post_content_backfill", queue)
    script.main()
    assert capsys.readouterr().out.strip() == "{'queued_posts': 2}"


def test_script_uses_one_connection_pool_and_closes_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CLI delegates once and closes both transport handles."""
    closed: list[str] = []

    class Pool:
        async def close(self) -> None:
            closed.append("pool")

    class Client:
        async def aclose(self) -> None:
            closed.append("client")

    pool = Pool()
    client = Client()

    async def create_pool(*_args: object, **_kwargs: object) -> Pool:
        return pool

    async def enqueue(_pool: object, _client: object, **kwargs: object) -> dict[str, int]:
        assert (_pool, _client) == (pool, client)
        assert kwargs == {
            "limit": 12,
            "require_embedding": True,
            "require_structure": True,
        }
        return {"queued_posts": 1}

    monkeypatch.setattr(script.asyncpg, "create_pool", create_pool)
    monkeypatch.setattr(script.redis, "from_url", lambda *_args, **_kwargs: client)
    monkeypatch.setattr(script, "enqueue_post_content_backfill", enqueue)
    monkeypatch.setattr(
        script,
        "load_settings",
        lambda: type(
            "Settings", (), {"orchestrator_base_url": "https://example.invalid", "orchestrator_api_key": "set"}
        )(),
    )
    result = asyncio.run(
        script.queue_post_content_backfill("postgresql://invalid", "redis://invalid", limit=12)
    )
    assert result == {"queued_posts": 1}
    assert closed == ["pool", "client"]


@pytest.mark.parametrize("limit", [0, 201])
def test_script_rejects_unbounded_limits_before_connecting(limit: int) -> None:
    """Invalid pages fail before any database or broker connection."""
    with pytest.raises(ValueError, match="between 1 and 200"):
        asyncio.run(
            script.queue_post_content_backfill(
                "postgresql://invalid", "redis://invalid", limit=limit
            )
        )
