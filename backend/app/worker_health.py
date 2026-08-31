"""Progress-based health contract for the durable worker event loop."""

from __future__ import annotations

import asyncio
from pathlib import Path
import time


HEARTBEAT_PATH = Path("/tmp/lineageweave-worker-heartbeat")
HEALTHCHECK_STATE_PATH = Path("/tmp/lineageweave-worker-healthcheck-state")


def record_worker_heartbeat(path: Path = HEARTBEAT_PATH) -> None:
    """Record one monotonic event-loop progress sample atomically."""
    temporary = path.with_suffix(".tmp")
    temporary.write_text(str(time.monotonic_ns()), encoding="ascii")
    temporary.replace(path)


def invalidate_worker_readiness(
    ready: asyncio.Event,
    path: Path = HEARTBEAT_PATH,
    state_path: Path = HEALTHCHECK_STATE_PATH,
) -> None:
    """Clear readiness and remove progress evidence from the prior epoch."""
    ready.clear()
    path.unlink(missing_ok=True)
    state_path.unlink(missing_ok=True)


async def run_worker_heartbeat(
    path: Path = HEARTBEAT_PATH,
    *,
    ready: asyncio.Event | None = None,
    state_path: Path = HEALTHCHECK_STATE_PATH,
) -> None:
    """Record progress only after every required startup barrier is ready."""
    # A restarted container can retain /tmp while the host monotonic clock has
    # restarted from zero. Begin a fresh comparison epoch before publishing.
    path.unlink(missing_ok=True)
    state_path.unlink(missing_ok=True)
    while True:
        if ready is not None:
            if not ready.is_set():
                invalidate_worker_readiness(ready, path, state_path)
            await ready.wait()
        record_worker_heartbeat(path)
        await asyncio.sleep(1.0)


def heartbeat_has_advanced(
    heartbeat_path: Path = HEARTBEAT_PATH,
    state_path: Path = HEALTHCHECK_STATE_PATH,
) -> bool:
    """Return whether the heartbeat advanced since the prior health probe."""
    try:
        current = int(heartbeat_path.read_text(encoding="ascii"))
    except (FileNotFoundError, ValueError):
        return False
    previous: int | None = None
    try:
        previous = int(state_path.read_text(encoding="ascii"))
    except (FileNotFoundError, ValueError):
        # A missing or malformed probe state is an absent prior baseline. The
        # current worker heartbeat becomes the next probe's baseline below.
        previous = None
    state_path.write_text(str(current), encoding="ascii")
    return current >= 0 and (previous is None or current > previous)


def main() -> None:
    """Exit successfully only when the durable worker event loop progressed."""
    raise SystemExit(0 if heartbeat_has_advanced() else 1)


if __name__ == "__main__":
    main()
