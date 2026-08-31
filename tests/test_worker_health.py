"""Tests for progress-based durable-worker health reporting."""

from __future__ import annotations

import asyncio
from pathlib import Path
import subprocess

import pytest

from backend.app import worker_health


_SHELL_PROBE = Path(__file__).parents[1] / "backend" / "worker-healthcheck.sh"


def test_health_requires_progress_between_probes(tmp_path: Path) -> None:
    """A live PID with an unchanged event-loop heartbeat is unhealthy."""
    heartbeat = tmp_path / "heartbeat"
    state = tmp_path / "state"

    assert worker_health.heartbeat_has_advanced(heartbeat, state) is False
    heartbeat.write_text("1", encoding="ascii")
    assert worker_health.heartbeat_has_advanced(heartbeat, state) is True
    assert worker_health.heartbeat_has_advanced(heartbeat, state) is False
    heartbeat.write_text("2", encoding="ascii")
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
        asyncio.run(worker_health.run_worker_heartbeat(heartbeat))
    assert int(heartbeat.read_text(encoding="ascii")) >= 0


def test_reboot_discards_prior_monotonic_probe_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A lower monotonic value after reboot starts a new worker epoch."""
    heartbeat = tmp_path / "heartbeat"
    state = tmp_path / "state"
    heartbeat.write_text("9000000000", encoding="ascii")
    state.write_text("9000000000", encoding="ascii")
    monkeypatch.setattr(worker_health.time, "monotonic_ns", lambda: 1)

    async def exercise() -> None:
        task = asyncio.create_task(
            worker_health.run_worker_heartbeat(heartbeat, state_path=state)
        )
        await asyncio.sleep(0)
        assert heartbeat.read_text(encoding="ascii") == "1"
        assert not state.exists()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(exercise())
    accepted = subprocess.run(
        ["/bin/sh", _SHELL_PROBE, heartbeat, state],
        check=False,
        capture_output=True,
        text=True,
    )
    assert accepted.returncode == 0
    assert accepted.stderr == ""


def test_shell_probe_requires_monotonic_progress(tmp_path: Path) -> None:
    """The lightweight container probe preserves the Python progress contract."""
    heartbeat = tmp_path / "heartbeat"
    state = tmp_path / "state"

    missing = subprocess.run(["/bin/sh", _SHELL_PROBE, heartbeat, state], check=False)
    assert missing.returncode != 0

    heartbeat.write_text("1", encoding="ascii")
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

    heartbeat.write_text("2", encoding="ascii")
    advanced = subprocess.run(["/bin/sh", _SHELL_PROBE, heartbeat, state], check=False)
    assert advanced.returncode == 0


def test_shell_probe_rejects_malformed_or_regressed_heartbeat(tmp_path: Path) -> None:
    """Malformed and decreasing counters fail closed in the container probe."""
    heartbeat = tmp_path / "heartbeat"
    state = tmp_path / "state"
    state.write_text("2\n", encoding="ascii")

    for value in ("not-a-counter\n", "1\n"):
        heartbeat.write_text(value, encoding="ascii")
        result = subprocess.run(["/bin/sh", _SHELL_PROBE, heartbeat, state], check=False)
        assert result.returncode != 0
