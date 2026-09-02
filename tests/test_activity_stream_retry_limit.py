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
            raise WatchError("synthetic persistent activity-stream conflict")
        raise AssertionError("activity reseed retried beyond the expected bound")


def test_publish_activity_event_sync_fails_after_bounded_watch_conflicts() -> None:
    """Persistent contention must fail clearly instead of spinning forever."""
    client = _ConflictStream(conflict_attempts=8)

    with pytest.raises(RuntimeError, match=r"activity:post-1.*8"):
        publish_activity_event_sync(
            client,
            "post-1",
            "ticket_created",
            "acct-1",
            "Ticket created: bounded retry",
        )

    assert client.execute_attempts == 8
