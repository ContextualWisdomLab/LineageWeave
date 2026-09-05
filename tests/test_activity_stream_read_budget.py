"""Buyer-facing activity reads stay bounded before reaching Valkey."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from backend.app.activity_stream import read_activity_events


class _ReadClient:
    """Record whether an invalid read request reaches the Valkey boundary."""

    def __init__(self) -> None:
        self.calls = 0

    async def xrevrange(
        self,
        key: str,
        max: str = "+",
        min: str = "-",
        count: int | None = None,
    ) -> list[tuple[str, dict[str, str]]]:
        del key, max, min, count
        self.calls += 1
        return []


@pytest.mark.parametrize("event_count", (True, 1.0, "50"))
def test_activity_read_count_requires_an_exact_integer(event_count: Any) -> None:
    """Scalar coercion must not create an implicit buyer-facing read budget."""
    client = _ReadClient()

    with pytest.raises(TypeError, match="event_count must be an integer"):
        asyncio.run(read_activity_events(client, "post-1", event_count=event_count))

    assert client.calls == 0


@pytest.mark.parametrize("event_count", (0, -1, 1001))
def test_activity_read_count_is_bounded_to_the_retained_window(
    event_count: int,
) -> None:
    """Invalid counts fail before an unbounded or nonsensical Valkey read."""
    client = _ReadClient()

    with pytest.raises(ValueError, match="event_count must be between 1 and 1000"):
        asyncio.run(read_activity_events(client, "post-1", event_count=event_count))

    assert client.calls == 0


def test_activity_read_count_accepts_the_retained_window_ceiling() -> None:
    """The largest supported request remains an explicit bounded Valkey read."""
    client = _ReadClient()

    assert asyncio.run(read_activity_events(client, "post-1", event_count=1000)) == []
    assert client.calls == 1
