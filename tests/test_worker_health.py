"""Tests for progress-based durable-worker health reporting."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import threading

import pytest

from backend.app import worker_health


_SHELL_PROBE = Path(__file__).parents[1] / "backend" / "worker-healthcheck.sh"
_OLD_EPOCH = "a" * 32
_NEW_EPOCH = "b" * 32
_OVERSIZED_COUNTER = 1 << 63


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


def test_out_of_domain_heartbeat_or_baseline_fails_closed(tmp_path: Path) -> None:
    """Counters outside the shared signed-64-bit domain are not progress."""
    heartbeat = tmp_path / "heartbeat"
    state = tmp_path / "state"
    oversized = _sample(_NEW_EPOCH, _OVERSIZED_COUNTER)

    heartbeat.write_text(oversized, encoding="ascii")
    assert worker_health.heartbeat_has_advanced(heartbeat, state) is False

    heartbeat.write_text(_sample(_NEW_EPOCH, 2), encoding="ascii")
    state.write_text(oversized, encoding="ascii")
    assert worker_health.heartbeat_has_advanced(heartbeat, state) is False
    assert state.read_text(encoding="ascii") == oversized


def test_non_ascii_heartbeat_or_baseline_fails_closed(tmp_path: Path) -> None:
    """Undecodable progress evidence preserves the boolean health contract."""
    heartbeat = tmp_path / "heartbeat"
    state = tmp_path / "state"

    heartbeat.write_bytes(b"\xff")
    assert worker_health.heartbeat_has_advanced(heartbeat, state) is False

    heartbeat.write_text(_sample(_NEW_EPOCH, 2), encoding="ascii")
    state.write_bytes(b"\xff")
    assert worker_health.heartbeat_has_advanced(heartbeat, state) is False


def test_concurrent_python_probes_use_distinct_atomic_state_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Concurrent probes cannot move or delete another probe's pending state."""
    heartbeat = tmp_path / "heartbeat"
    state = tmp_path / "state"
    current_sample = _sample(_NEW_EPOCH, 2)
    heartbeat.write_text(current_sample, encoding="ascii")
    state.write_text(_sample(_NEW_EPOCH, 1), encoding="ascii")
    temporary_paths: list[Path] = []
    original_replace = Path.replace

    def synchronized_replace(path: Path, target: Path) -> Path:
        if target == state:
            temporary_paths.append(path)
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", synchronized_replace)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _index: worker_health.heartbeat_has_advanced(
                    heartbeat, state
                ),
                range(2),
            )
        )

    assert sorted(results) == [False, True]
    assert len(set(temporary_paths)) == 2
    assert state.read_text(encoding="ascii") == current_sample


def test_older_python_probe_cannot_replace_newer_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Probe serialization prevents publication from reversing observation order."""
    heartbeat = tmp_path / "heartbeat"
    state = tmp_path / "state"
    older_sample = _sample(_NEW_EPOCH, 2)
    newer_sample = _sample(_NEW_EPOCH, 3)
    heartbeat.write_text(older_sample, encoding="ascii")
    state.write_text(_sample(_NEW_EPOCH, 1), encoding="ascii")
    first_observed = threading.Event()
    resume_first = threading.Event()
    original_read_text = Path.read_text

    def staged_read_text(path: Path, *args: object, **kwargs: object) -> str:
        if path == heartbeat and not first_observed.is_set():
            first_observed.set()
            assert resume_first.wait(timeout=2)
            return older_sample
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", staged_read_text)
    with ThreadPoolExecutor(max_workers=2) as executor:
        older_probe = executor.submit(
            worker_health.heartbeat_has_advanced, heartbeat, state
        )
        assert first_observed.wait(timeout=2)
        heartbeat.write_text(newer_sample, encoding="ascii")
        newer_probe = executor.submit(
            worker_health.heartbeat_has_advanced, heartbeat, state
        )
        resume_first.set()

        assert older_probe.result(timeout=2) is True
        assert newer_probe.result(timeout=2) is True

    assert state.read_text(encoding="ascii") == newer_sample
    assert worker_health.heartbeat_has_advanced(heartbeat, state) is False


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
        _sample(_NEW_EPOCH, _OVERSIZED_COUNTER),
        _sample(_NEW_EPOCH, 1),
    ):
        heartbeat.write_text(value, encoding="ascii")
        result = subprocess.run(["/bin/sh", _SHELL_PROBE, heartbeat, state], check=False)
        assert result.returncode != 0


def test_shell_probe_rejects_out_of_domain_baseline(tmp_path: Path) -> None:
    """An oversized stored counter cannot be adopted as a healthy baseline."""
    heartbeat = tmp_path / "heartbeat"
    state = tmp_path / "state"
    heartbeat.write_text(_sample(_NEW_EPOCH, 2), encoding="ascii")
    state.write_text(_sample(_NEW_EPOCH, _OVERSIZED_COUNTER), encoding="ascii")

    result = subprocess.run(
        ["/bin/sh", _SHELL_PROBE, heartbeat, state],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert result.stderr == ""
