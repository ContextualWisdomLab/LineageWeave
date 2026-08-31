"""Progress-based health contract for the durable worker event loop."""

from __future__ import annotations

import asyncio
from pathlib import Path
import time
import uuid


HEARTBEAT_PATH = Path("/tmp/lineageweave-worker-heartbeat")
HEALTHCHECK_STATE_PATH = Path("/tmp/lineageweave-worker-healthcheck-state")
_SAMPLE_VERSION = "v1"


def _parse_sample(value: str) -> tuple[str, int] | None:
    parts = value.split()
    if len(parts) != 3 or parts[0] != _SAMPLE_VERSION:
        return None
    epoch, counter_text = parts[1:]
    if (
        len(epoch) != 32
        or any(character not in "0123456789abcdef" for character in epoch)
        or not counter_text.isascii()
        or not counter_text.isdecimal()
    ):
        return None
    return epoch, int(counter_text)


def record_worker_heartbeat(path: Path = HEARTBEAT_PATH, *, epoch: str) -> None:
    """Record one monotonic event-loop progress sample atomically."""
    if _parse_sample(f"{_SAMPLE_VERSION} {epoch} 0") is None:
        raise ValueError("worker heartbeat epoch must be 32 lowercase hex characters")
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        f"{_SAMPLE_VERSION} {epoch} {time.monotonic_ns()}\n", encoding="ascii"
    )
    temporary.replace(path)


async def run_worker_heartbeat(
    path: Path = HEARTBEAT_PATH,
    *,
    state_path: Path = HEALTHCHECK_STATE_PATH,
    epoch: str | None = None,
) -> None:
    """Record progress once per broker-poll interval until cancelled."""
    process_epoch = epoch or uuid.uuid4().hex
    # A restarted container can retain /tmp while the host monotonic clock has
    # restarted from zero. Begin a fresh comparison epoch before publishing.
    path.unlink(missing_ok=True)
    state_path.unlink(missing_ok=True)
    while True:
        record_worker_heartbeat(path, epoch=process_epoch)
        await asyncio.sleep(1.0)


def heartbeat_has_advanced(
    heartbeat_path: Path = HEARTBEAT_PATH,
    state_path: Path = HEALTHCHECK_STATE_PATH,
) -> bool:
    """Return whether the heartbeat advanced since the prior health probe."""
    try:
        current_text = heartbeat_path.read_text(encoding="ascii")
    except FileNotFoundError:
        return False
    current = _parse_sample(current_text)
    if current is None:
        return False
    previous: tuple[str, int] | None = None
    try:
        previous = _parse_sample(state_path.read_text(encoding="ascii"))
    except FileNotFoundError:
        # A missing or malformed probe state is an absent prior baseline. The
        # current worker heartbeat becomes the next probe's baseline below.
        previous = None
    temporary = state_path.with_suffix(".tmp")
    temporary.write_text(current_text, encoding="ascii")
    temporary.replace(state_path)
    return previous is None or current[0] != previous[0] or current[1] > previous[1]


def main() -> None:
    """Exit successfully only when the durable worker event loop progressed."""
    raise SystemExit(0 if heartbeat_has_advanced() else 1)


if __name__ == "__main__":
    main()
