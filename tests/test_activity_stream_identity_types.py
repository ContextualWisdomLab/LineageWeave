"""Fail-closed type boundaries for Valkey activity identity fields."""

from __future__ import annotations

import asyncio

import pytest

from backend.app.activity_stream import (
    publish_activity_event,
    publish_activity_event_sync,
    ticket_created_summary,
)


class _UnexpectedValkeyAccess:
    """Fail if malformed identity reaches the synchronous Valkey boundary."""

    def pipeline(self):
        """Prove validation happens before any stream read or mutation."""
        raise AssertionError("malformed activity identity reached Valkey")


class _UnexpectedAsyncValkeyAccess:
    """Fail if malformed identity reaches the ordinary async append boundary."""

    async def xadd(self, *args, **kwargs):
        """Prove runtime publication validates identity before issuing XADD."""
        del args, kwargs
        raise AssertionError("malformed activity identity reached async Valkey")


def test_sync_activity_rejects_numeric_actor_identity_before_valkey_access() -> None:
    """A numeric actor id must not alias the canonical string identity ``\"7\"``."""
    with pytest.raises(TypeError, match="actor_account_id must be a string"):
        publish_activity_event_sync(
            _UnexpectedValkeyAccess(),
            "post-1",
            "ticket_created",
            7,  # type: ignore[arg-type]
            ticket_created_summary("Send Northridge Grid the revised quote"),
        )


def test_sync_activity_rejects_numeric_post_identity_before_valkey_access() -> None:
    """A numeric post id must not alias the canonical string stream identity ``\"7\"``."""
    with pytest.raises(TypeError, match="post_id must be a string"):
        publish_activity_event_sync(
            _UnexpectedValkeyAccess(),
            7,  # type: ignore[arg-type]
            "ticket_created",
            "acct-1",
            ticket_created_summary("Send Northridge Grid the revised quote"),
        )


def test_async_activity_rejects_numeric_actor_identity_before_xadd() -> None:
    """Ordinary runtime publication shares the exact actor-identity admission rule."""
    with pytest.raises(TypeError, match="actor_account_id must be a string"):
        asyncio.run(
            publish_activity_event(
                _UnexpectedAsyncValkeyAccess(),  # type: ignore[arg-type]
                "post-1",
                "ticket_created",
                7,  # type: ignore[arg-type]
                ticket_created_summary("Send Northridge Grid the revised quote"),
            )
        )
