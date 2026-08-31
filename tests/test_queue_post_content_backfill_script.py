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
    with pytest.raises(SystemExit):
        parser.parse_args(["--all-pages", "--retry-failed"])

    async def queue(*_args: object, **kwargs: object) -> dict[str, int]:
        assert kwargs == {"limit": 7, "all_pages": False, "retry_failed": True}
        return {"queued_posts": 2}

    monkeypatch.setattr(
        script,
        "_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(
                target_dsn="postgresql://invalid",
                valkey_url="redis://invalid",
                limit=7,
                all_pages=False,
                retry_failed=True,
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
        return {
            "selected_posts": 1,
            "queued_posts": 1,
            "published_events": 1,
            "recovery_pending": 0,
        }

    monkeypatch.setattr(script.asyncpg, "create_pool", create_pool)
    monkeypatch.setattr(script.redis, "from_url", lambda *_args, **_kwargs: client)
    monkeypatch.setattr(script, "enqueue_post_content_backfill", enqueue)
    settings_type = type(
        "Settings",
        (),
        {
            "orchestrator_base_url": "https://example.invalid",
            "orchestrator_api_key": "set",
        },
    )
    monkeypatch.setattr(script, "load_settings", settings_type)
    result = asyncio.run(
        script.queue_post_content_backfill("postgresql://invalid", "redis://invalid", limit=12)
    )
    assert result == {
        "selected_posts": 1,
        "queued_posts": 1,
        "published_events": 1,
        "recovery_pending": 0,
    }
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


def test_script_rejects_unobserved_bulk_terminal_retry_before_connecting() -> None:
    """Terminal recovery requires a fresh operator decision after every page."""
    with pytest.raises(ValueError, match="one observed bounded page"):
        asyncio.run(
            script.queue_post_content_backfill(
                "postgresql://invalid",
                "redis://invalid",
                limit=200,
                all_pages=True,
                retry_failed=True,
            )
        )


def test_all_pages_exhausts_incomplete_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-terminal continuation drains the durable candidate set by pages."""
    class Pool:
        async def close(self) -> None:
            return None

    class Client:
        async def aclose(self) -> None:
            return None

    candidate_pages = iter((2, 2, 0))

    async def create_pool(*_args: object, **_kwargs: object) -> Pool:
        return Pool()

    async def page(counts: object) -> dict[str, int]:
        selected = next(counts)  # type: ignore[arg-type]
        return {
            "selected_posts": selected,
            "queued_posts": selected,
            "published_events": selected,
            "recovery_pending": 0,
        }

    async def enqueue(*_args: object, **_kwargs: object) -> dict[str, int]:
        return await page(candidate_pages)

    monkeypatch.setattr(script.asyncpg, "create_pool", create_pool)
    monkeypatch.setattr(script.redis, "from_url", lambda *_args, **_kwargs: Client())
    monkeypatch.setattr(script, "enqueue_post_content_backfill", enqueue)
    monkeypatch.setattr(
        script,
        "load_settings",
        lambda: SimpleNamespace(orchestrator_base_url="set", orchestrator_api_key="set"),
    )
    result = asyncio.run(
        script.queue_post_content_backfill(
            "postgresql://invalid",
            "redis://invalid",
            limit=2,
            all_pages=True,
            retry_failed=False,
        )
    )
    assert result == {
        "selected_posts": 4,
        "queued_posts": 4,
        "published_events": 4,
        "recovery_pending": 0,
    }
