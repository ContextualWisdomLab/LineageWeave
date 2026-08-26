"""Authorization and request bounds for the semantic backfill operator API."""

from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from backend.app import main
from backend.app.auth import CurrentAccount


def _account(*permissions: str) -> CurrentAccount:
    """Build one synthetic account without an OIDC or database dependency."""
    return CurrentAccount(
        user_account_id="00000000-0000-0000-0000-000000000001",
        external_subject_id="synthetic-subject",
        display_name="Synthetic operator",
        preferred_locale="en",
        corporate_entity_ids=frozenset(),
        process_unit_ids=frozenset(),
        permission_codes=frozenset(permissions),
    )


def test_backfill_endpoint_requires_post_admin() -> None:
    """A reader cannot enqueue corpus-wide semantic processing."""
    with pytest.raises(main.HTTPException) as raised:
        asyncio.run(
            main.queue_post_content_backfill(
                main.PostContentBackfillRequest(),
                account=_account("post_read"),
                pool=object(),
                valkey=object(),
            )
        )
    assert raised.value.status_code == 403


def test_backfill_request_limit_is_bounded() -> None:
    """Pydantic rejects zero and corpus-sized operator requests."""
    for limit in (0, 201):
        with pytest.raises(ValidationError):
            main.PostContentBackfillRequest(limit=limit)


def test_backfill_endpoint_only_enqueues_durable_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The accepted response delegates once and never invokes a provider."""
    observed: dict[str, object] = {}

    async def enqueue(pool: object, valkey: object, **kwargs: object) -> dict[str, int]:
        observed.update(pool=pool, valkey=valkey, **kwargs)
        return {
            "selected_posts": 1,
            "queued_posts": 1,
            "published_events": 1,
            "recovery_pending": 0,
        }

    monkeypatch.setattr(main, "enqueue_post_content_backfill", enqueue)
    settings_type = type(
        "Settings",
        (),
        {
            "orchestrator_base_url": "https://orchestrator.invalid",
            "orchestrator_api_key": "configured",
        },
    )
    monkeypatch.setattr(main, "load_settings", settings_type)
    pool = object()
    valkey = object()
    result = asyncio.run(
        main.queue_post_content_backfill(
            main.PostContentBackfillRequest(limit=17),
            account=_account("post_admin"),
            pool=pool,
            valkey=valkey,
        )
    )
    assert result["queued_posts"] == 1
    assert observed == {
        "pool": pool,
        "valkey": valkey,
        "limit": 17,
        "require_embedding": True,
        "require_structure": True,
    }


def test_backfill_endpoint_does_not_require_missing_model_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unwired orchestrator remains unavailable instead of being fabricated."""
    observed: dict[str, object] = {}

    async def enqueue(_pool: object, _valkey: object, **kwargs: object) -> dict[str, int]:
        observed.update(kwargs)
        return {
            "selected_posts": 0,
            "queued_posts": 0,
            "published_events": 0,
            "recovery_pending": 0,
        }

    monkeypatch.setattr(main, "enqueue_post_content_backfill", enqueue)
    settings_type = type(
        "Settings", (), {"orchestrator_base_url": "", "orchestrator_api_key": ""}
    )
    monkeypatch.setattr(main, "load_settings", settings_type)
    asyncio.run(
        main.queue_post_content_backfill(
            main.PostContentBackfillRequest(),
            account=_account("post_admin"),
            pool=object(),
            valkey=object(),
        )
    )
    assert observed == {
        "limit": 100,
        "require_embedding": False,
        "require_structure": False,
    }
