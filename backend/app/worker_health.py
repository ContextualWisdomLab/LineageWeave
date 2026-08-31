"""Progress-based health contract for the durable worker event loop."""

from __future__ import annotations

import asyncio
import fcntl
from pathlib import Path
import tempfile
import threading
import time
import uuid


HEARTBEAT_PATH = Path("/tmp/lineageweave-worker-heartbeat")
HEALTHCHECK_STATE_PATH = Path("/tmp/lineageweave-worker-healthcheck-state")
_SAMPLE_VERSION = "v1"
_MAX_MONOTONIC_COUNTER = (1 << 63) - 1
_PROBE_THREAD_LOCK = threading.Lock()


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
    if len(counter_text) > 19:
        return None
    counter = int(counter_text)
    if counter > _MAX_MONOTONIC_COUNTER:
        return None
    return epoch, counter


def record_worker_heartbeat(path: Path = HEARTBEAT_PATH, *, epoch: str) -> None:
    """Record one monotonic event-loop progress sample atomically."""
    if _parse_sample(f"{_SAMPLE_VERSION} {epoch} 0") is None:
        raise ValueError("worker heartbeat epoch must be 32 lowercase hex characters")
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        f"{_SAMPLE_VERSION} {epoch} {time.monotonic_ns()}\n", encoding="ascii"
    )
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
    epoch: str | None = None,
) -> None:
    """Record progress only after every required startup barrier is ready."""
    process_epoch = epoch or uuid.uuid4().hex
    # A restarted container can retain /tmp while the host monotonic clock has
    # restarted from zero. Begin a fresh comparison epoch before publishing.
    path.unlink(missing_ok=True)
    state_path.unlink(missing_ok=True)
    while True:
        if ready is not None:
            if not ready.is_set():
                invalidate_worker_readiness(ready, path, state_path)
            await ready.wait()
        record_worker_heartbeat(path, epoch=process_epoch)
        await asyncio.sleep(1.0)


def heartbeat_has_advanced(
    heartbeat_path: Path = HEARTBEAT_PATH,
    state_path: Path = HEALTHCHECK_STATE_PATH,
) -> bool:
    """Return whether the heartbeat advanced since the prior health probe."""
    lock_path = state_path.with_name(f".{state_path.name}.lock")
    try:
        with _PROBE_THREAD_LOCK, lock_path.open("a+b") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            return _heartbeat_has_advanced_locked(heartbeat_path, state_path)
    except (OSError, UnicodeDecodeError):
        return False


def _heartbeat_has_advanced_locked(heartbeat_path: Path, state_path: Path) -> bool:
    try:
        current_text = heartbeat_path.read_text(encoding="ascii")
    except FileNotFoundError:
        return False
    current = _parse_sample(current_text)
    if current is None:
        return False
    try:
        previous = _parse_sample(state_path.read_text(encoding="ascii"))
    except FileNotFoundError:
        previous = None
    else:
        if previous is None:
            return False
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="ascii",
        dir=state_path.parent,
        prefix=f".{state_path.name}.",
        delete=False,
    ) as temporary_file:
        temporary_file.write(current_text)
        temporary = Path(temporary_file.name)
    try:
        temporary.replace(state_path)
    finally:
        temporary.unlink(missing_ok=True)
    return previous is None or current[0] != previous[0] or current[1] > previous[1]


def main() -> None:
    """Exit successfully only when the durable worker event loop progressed."""
    raise SystemExit(0 if heartbeat_has_advanced() else 1)


if __name__ == "__main__":
    main()
