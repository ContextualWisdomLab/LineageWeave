"""Tests for progress-based durable-worker health reporting."""

from __future__ import annotations

import asyncio
from pathlib import Path
import subprocess

import pytest

from backend.app import worker_health


_SHELL_PROBE = Path(__file__).parents[1] / "backend" / "worker-healthcheck.sh"
_OLD_EPOCH = "a" * 32
_NEW_EPOCH = "b" * 32


def _sample(epoch: str, counter: int) -> str:
    return f"v1 {epoch} {counter}\n"


def test_health_requires_progress_between_probes(tmp_path: Path) -> None:
    """A live PID with an unchanged event-loop heartbeat is unhealthy."""
    heartbeat = tmp_path / "heartbeat"
    state = tmp_path / "state"

    assert worker_health.heartbeat_has_advanced(heartbeat, state) is False
    heartbeat.write_text(_sample(_NEW_EPOCH, 1), encoding="ascii")
    assert worker_health.heartbeat_has_advanced(heartbeat, state) is True
    assert worker_health.heartbeat_has_advanced(heartbeat, state) is False
    heartbeat.write_text(_sample(_NEW_EPOCH, 2), encoding="ascii")
    assert worker_health.heartbeat_has_advanced(heartbeat, state) is True


def test_malformed_heartbeat_fails_closed(tmp_path: Path) -> None:
    """Malformed progress evidence is never reported as healthy."""
    heartbeat = tmp_path / "heartbeat"
    heartbeat.write_text("not-a-counter", encoding="ascii")

    assert worker_health.heartbeat_has_advanced(heartbeat, tmp_path / "state") is False


def test_heartbeat_records_before_first_sleep(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Startup publishes progress before the first broker-poll interval."""
    heartbeat = tmp_path / "heartbeat"

    async def cancel_after_first_record(_seconds: float) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr(worker_health.asyncio, "sleep", cancel_after_first_record)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            worker_health.run_worker_heartbeat(heartbeat, epoch=_NEW_EPOCH)
        )
    assert heartbeat.read_text(encoding="ascii").startswith(
        f"v1 {_NEW_EPOCH} "
    )


def test_reboot_discards_prior_monotonic_probe_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A lower monotonic value after reboot starts a new worker epoch."""
    heartbeat = tmp_path / "heartbeat"
    state = tmp_path / "state"
    old_sample = _sample(_OLD_EPOCH, 9_000_000_000)
    heartbeat.write_text(old_sample, encoding="ascii")
    state.write_text(old_sample, encoding="ascii")
    monkeypatch.setattr(worker_health.time, "monotonic_ns", lambda: 1)

    async def exercise() -> None:
        task = asyncio.create_task(
            worker_health.run_worker_heartbeat(
                heartbeat, state_path=state, epoch=_NEW_EPOCH
            )
        )
        await asyncio.sleep(0)
        assert heartbeat.read_text(encoding="ascii") == _sample(_NEW_EPOCH, 1)
        assert not state.exists()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(exercise())
    # Model a prior-epoch probe that read before reset and publishes after it.
    state.write_text(old_sample, encoding="ascii")
    accepted = subprocess.run(
        ["/bin/sh", _SHELL_PROBE, heartbeat, state],
        check=False,
        capture_output=True,
        text=True,
    )
    assert accepted.returncode == 0
    assert accepted.stderr == ""
    monkeypatch.setattr(worker_health.time, "monotonic_ns", lambda: 2)
    worker_health.record_worker_heartbeat(heartbeat, epoch=_NEW_EPOCH)
    advanced = subprocess.run(
        ["/bin/sh", _SHELL_PROBE, heartbeat, state], check=False
    )
    assert advanced.returncode == 0


def test_shell_probe_requires_monotonic_progress(tmp_path: Path) -> None:
    """The lightweight container probe preserves the Python progress contract."""
    heartbeat = tmp_path / "heartbeat"
    state = tmp_path / "state"

    missing = subprocess.run(["/bin/sh", _SHELL_PROBE, heartbeat, state], check=False)
    assert missing.returncode != 0

    heartbeat.write_text(_sample(_NEW_EPOCH, 1), encoding="ascii")
    first = subprocess.run(
        ["/bin/sh", _SHELL_PROBE, heartbeat, state],
        check=False,
        capture_output=True,
        text=True,
    )
    unchanged = subprocess.run(["/bin/sh", _SHELL_PROBE, heartbeat, state], check=False)
    assert first.returncode == 0
    assert first.stderr == ""
    assert unchanged.returncode != 0

    heartbeat.write_text(_sample(_NEW_EPOCH, 2), encoding="ascii")
    advanced = subprocess.run(["/bin/sh", _SHELL_PROBE, heartbeat, state], check=False)
    assert advanced.returncode == 0


def test_shell_probe_rejects_malformed_or_regressed_heartbeat(tmp_path: Path) -> None:
    """Malformed and decreasing counters fail closed in the container probe."""
    heartbeat = tmp_path / "heartbeat"
    state = tmp_path / "state"
    state.write_text(_sample(_NEW_EPOCH, 2), encoding="ascii")

    for value in (
        "not-a-counter\n",
        "1\n",
        _sample(_NEW_EPOCH, 1),
    ):
        heartbeat.write_text(value, encoding="ascii")
        result = subprocess.run(["/bin/sh", _SHELL_PROBE, heartbeat, state], check=False)
        assert result.returncode != 0
