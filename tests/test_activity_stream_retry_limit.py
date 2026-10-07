"""Bound the optimistic retry loop used by synchronous activity reseeding."""

from __future__ import annotations

import pytest
from redis.exceptions import WatchError

from backend.app.activity_stream import publish_activity_event_sync


class _ConflictStream:
    """Force repeated WATCH conflicts without requiring a live Valkey process."""

    def __init__(self, conflict_attempts: int) -> None:
        """Allow exactly ``conflict_attempts`` synthetic optimistic conflicts."""
        self.conflict_attempts = conflict_attempts
        self.execute_attempts = 0

    def pipeline(self):
        """Return a transaction facade for one optimistic reseed attempt."""
        return _ConflictPipeline(self)


class _ConflictPipeline:
    """Model the transaction surface while forcing bounded WATCH conflicts."""

    def __init__(self, stream: _ConflictStream) -> None:
        """Bind the transaction to the shared conflict counter."""
        self.stream = stream

    def __enter__(self):
        """Return the transaction facade."""
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        """Never suppress transaction exceptions."""
        del exc_type, exc, traceback
        return False

    def watch(self, key: str) -> None:
        """Accept the production WATCH call without external state."""
        del key

    def xrevrange(self, key: str):
        """Expose an empty retained stream so the append path is exercised."""
        del key
        return []

    def multi(self) -> None:
        """Accept the production MULTI transition."""

    def xadd(self, key: str, fields: dict[str, str], maxlen=None, approximate=None):
        """Accept the queued append without mutating external state."""
        del key, fields, maxlen, approximate
        return self

    def execute(self):
        """Raise WATCH conflicts, then fail if production retries past the bound."""
        self.stream.execute_attempts += 1
        if self.stream.execute_attempts <= self.stream.conflict_attempts:
            raise WatchError(
                "synthetic conflict while watching activity:post-1 for post-1"
            )
        raise AssertionError("activity reseed retried beyond the expected bound")


def test_publish_activity_event_sync_fails_after_bounded_watch_conflicts() -> None:
    """Contention failure must not retain the raw key through exception chaining."""
    client = _ConflictStream(conflict_attempts=8)

    with pytest.raises(RuntimeError) as error_info:
        publish_activity_event_sync(
            client,
            "post-1",
            "ticket_created",
            "acct-1",
            "Ticket created: bounded retry",
        )

    error_message = str(error_info.value)
    assert "activity reseed" in error_message.lower()
    assert "8" in error_message
    assert "post-1" not in error_message
    assert "activity:post-1" not in error_message
    assert error_info.value.__cause__ is None
    assert error_info.value.__context__ is None
    assert client.execute_attempts == 8
