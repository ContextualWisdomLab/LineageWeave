"""Worker cgroup memory evidence contracts."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "capture_worker_memory_evidence.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("capture_worker_memory_evidence", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


worker_memory = _load_module()


def _snapshot(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "container_started_at": "2026-08-27T00:00:00Z",
        "container_status": "running",
        "container_oom_killed": False,
        "container_exit_code": 0,
        "container_restart_count": 0,
        "memory_limit_bytes": None,
        "memory_reservation_bytes": None,
        "memory_current_bytes": 80 * 1024 * 1024,
        "memory_peak_bytes": 120 * 1024 * 1024,
        "memory_max_bytes": None,
        "memory_events_local": {
            "low": 0,
            "high": 0,
            "max": 0,
            "oom": 0,
            "oom_kill": 0,
            "oom_group_kill": 0,
        },
    }
    value.update(changes)
    return value


def test_compare_confirms_only_kernel_or_docker_oom_evidence() -> None:
    before = _snapshot()
    after = _snapshot(
        container_status="exited",
        container_oom_killed=True,
        container_exit_code=137,
        memory_events_local={
            "low": 0,
            "high": 0,
            "max": 1,
            "oom": 1,
            "oom_kill": 1,
            "oom_group_kill": 0,
        },
    )

    evidence = worker_memory.compare_snapshots(before, after, elapsed_seconds=60)

    assert evidence["classification"] == "oom_confirmed"
    assert evidence["event_deltas"]["oom_kill"] == 1
    assert evidence["observed_peak_bytes"] == 120 * 1024 * 1024
    assert evidence["memory_limit_proposal"] is None


def test_compare_does_not_call_exit_137_an_oom() -> None:
    evidence = worker_memory.compare_snapshots(
        _snapshot(),
        _snapshot(container_status="exited", container_exit_code=137),
        elapsed_seconds=60,
    )

    assert evidence["classification"] == "sigkill_unattributed"


def test_compare_accepts_representative_window_without_pressure() -> None:
    evidence = worker_memory.compare_snapshots(
        _snapshot(),
        _snapshot(memory_peak_bytes=160 * 1024 * 1024),
        elapsed_seconds=60,
    )

    assert evidence["classification"] == "observed_without_memory_pressure"
    assert evidence["memory_limit_proposal"] is None


def test_compare_rejects_container_replacement_and_counter_reset() -> None:
    with pytest.raises(worker_memory.MemoryEvidenceError, match="container changed"):
        worker_memory.compare_snapshots(
            _snapshot(),
            _snapshot(container_started_at="2026-08-27T00:01:00Z"),
            elapsed_seconds=60,
        )
    with pytest.raises(worker_memory.MemoryEvidenceError, match="decreased"):
        worker_memory.compare_snapshots(
            _snapshot(
                memory_events_local={
                    "low": 0,
                    "high": 0,
                    "max": 0,
                    "oom": 0,
                    "oom_kill": 1,
                    "oom_group_kill": 0,
                }
            ),
            _snapshot(),
            elapsed_seconds=60,
        )


def test_compare_rejects_invalid_window_or_missing_evidence() -> None:
    with pytest.raises(worker_memory.MemoryEvidenceError, match="elapsed_seconds"):
        worker_memory.compare_snapshots(_snapshot(), _snapshot(), elapsed_seconds=0)
    with pytest.raises(worker_memory.MemoryEvidenceError, match="memory.peak"):
        worker_memory.compare_snapshots(
            _snapshot(), _snapshot(memory_peak_bytes=None), elapsed_seconds=1
        )


def test_parse_flat_keys_uses_names_not_line_positions() -> None:
    assert worker_memory.parse_flat_keys("oom_kill 2\nlow 1\n") == {
        "oom_kill": 2,
        "low": 1,
    }
    with pytest.raises(worker_memory.MemoryEvidenceError, match="invalid cgroup"):
        worker_memory.parse_flat_keys("oom_kill nope\n")
    with pytest.raises(worker_memory.MemoryEvidenceError, match="invalid cgroup"):
        worker_memory.parse_flat_keys("oom_kill\n")


def test_integer_and_event_validation_fail_closed() -> None:
    for value, message in (("bad", "integer"), (-1, "negative")):
        with pytest.raises(worker_memory.MemoryEvidenceError, match=message):
            worker_memory._integer(value, "field")
    with pytest.raises(worker_memory.MemoryEvidenceError, match="events.local"):
        worker_memory.compare_snapshots(
            _snapshot(memory_events_local=None), _snapshot(), elapsed_seconds=1
        )
    missing_key_events = dict(_snapshot()["memory_events_local"])
    del missing_key_events["oom_kill"]
    with pytest.raises(worker_memory.MemoryEvidenceError, match="required keys"):
        worker_memory.compare_snapshots(
            _snapshot(memory_events_local=missing_key_events),
            _snapshot(),
            elapsed_seconds=1,
        )


def test_compare_reports_pressure_without_claiming_oom() -> None:
    after = _snapshot(
        memory_events_local={
            "low": 0,
            "high": 1,
            "max": 0,
            "oom": 0,
            "oom_kill": 0,
            "oom_group_kill": 0,
        }
    )
    evidence = worker_memory.compare_snapshots(_snapshot(), after, elapsed_seconds=1)
    assert evidence["classification"] == "memory_pressure_observed"


def test_run_is_bounded_and_reports_failures(monkeypatch) -> None:
    monkeypatch.setattr(
        worker_memory.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout=" ok \n", stderr=""),
    )
    assert worker_memory._run(["command"]) == "ok"
    monkeypatch.setattr(
        worker_memory.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout="", stderr="bad"),
    )
    with pytest.raises(worker_memory.MemoryEvidenceError, match="bad"):
        worker_memory._run(["command"])
    monkeypatch.setattr(
        worker_memory.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            subprocess.TimeoutExpired("command", 1)
        ),
    )
    with pytest.raises(worker_memory.MemoryEvidenceError, match="timed out"):
        worker_memory._run(["command"])


def test_capture_snapshot_reads_docker_and_keyed_cgroup_evidence(monkeypatch) -> None:
    inspection = json.dumps(
        [
            {
                "State": {
                    "StartedAt": "2026-08-27T00:00:00Z",
                    "Status": "running",
                    "OOMKilled": False,
                    "ExitCode": 0,
                },
                "HostConfig": {"Memory": 1024, "MemoryReservation": 512},
                "RestartCount": 1,
            }
        ]
    )
    outputs = iter(
        [
            "container-id",
            inspection,
            "100\n200\n300\nlow 0\nhigh 0\nmax 0\noom 0\noom_kill 0\noom_group_kill 0\n",
        ]
    )
    monkeypatch.setattr(worker_memory, "_run", lambda *_args, **_kwargs: next(outputs))

    snapshot = worker_memory.capture_snapshot()

    assert snapshot["memory_current_bytes"] == 100
    assert snapshot["memory_peak_bytes"] == 200
    assert snapshot["memory_max_bytes"] == 300
    assert snapshot["memory_limit_bytes"] == 1024
    assert snapshot["container_restart_count"] == 1


@pytest.mark.parametrize(
    ("oom_killed", "exit_code", "classification"),
    [(True, 137, "oom_confirmed"), (False, 137, "sigkill_unattributed")],
)
def test_capture_and_compare_classify_worker_that_exits_mid_window(
    monkeypatch, oom_killed: bool, exit_code: int, classification: str
) -> None:
    inspection = json.dumps(
        [
            {
                "State": {
                    "StartedAt": "2026-08-27T00:00:00Z",
                    "Status": "exited",
                    "OOMKilled": oom_killed,
                    "ExitCode": exit_code,
                },
                "HostConfig": {"Memory": 0, "MemoryReservation": 0},
                "RestartCount": 0,
            }
        ]
    )
    outputs = iter(["container-id", inspection])
    monkeypatch.setattr(worker_memory, "_run", lambda *_args, **_kwargs: next(outputs))

    after = worker_memory.capture_snapshot()
    evidence = worker_memory.compare_snapshots(_snapshot(), after, elapsed_seconds=1)

    assert evidence["classification"] == classification
    assert evidence["observed_peak_bytes"] == 120 * 1024 * 1024
    assert evidence["observed_peak_scope"] == "before_terminal_exit"
    assert evidence["ending_current_bytes"] is None
    assert evidence["event_deltas"] is None


def test_compare_rejects_other_exit_without_ending_cgroup_evidence() -> None:
    after = _snapshot(
        container_status="exited",
        container_exit_code=1,
        memory_current_bytes=None,
        memory_peak_bytes=None,
        memory_max_bytes=None,
        memory_events_local=None,
    )
    with pytest.raises(worker_memory.MemoryEvidenceError, match="ending cgroup"):
        worker_memory.compare_snapshots(_snapshot(), after, elapsed_seconds=1)


@pytest.mark.parametrize(
    ("outputs", "message"),
    [
        ([""], "unavailable"),
        (["id", "[]"], "inspection"),
        (["id", '[{"State": [], "HostConfig": {}}]'], "state"),
        (
            ["id", '[{"State": {"Status": "running"}, "HostConfig": {}}]'],
            "state",
        ),
        (
                [
                    "id",
                    (
                        '[{"State": {"StartedAt": "start", "Status": "running"}, '
                        '"HostConfig": {}, "RestartCount": 0}]'
                    ),
                    "1\n2\nmax",
                ],
            "cgroup v2",
        ),
    ],
)
def test_capture_snapshot_rejects_incomplete_boundaries(
    monkeypatch, outputs: list[str], message: str
) -> None:
    values = iter(outputs)
    monkeypatch.setattr(worker_memory, "_run", lambda *_args, **_kwargs: next(values))
    with pytest.raises(worker_memory.MemoryEvidenceError, match=message):
        worker_memory.capture_snapshot()


def test_observe_and_main_write_non_identifying_result(monkeypatch, tmp_path: Path) -> None:
    snapshots = iter(
        [
            {**_snapshot(), "captured_at": "before"},
            {**_snapshot(memory_peak_bytes=130 * 1024 * 1024), "captured_at": "after"},
        ]
    )
    clocks = iter([10.0, 12.0])
    sleeps: list[float] = []
    monkeypatch.setattr(worker_memory, "capture_snapshot", lambda: next(snapshots))
    monkeypatch.setattr(worker_memory.time, "monotonic", lambda: next(clocks))
    monkeypatch.setattr(worker_memory.time, "sleep", sleeps.append)

    result = worker_memory.observe(2)

    assert sleeps == [2]
    assert result["before_captured_at"] == "before"
    assert result["after_captured_at"] == "after"
    with pytest.raises(worker_memory.MemoryEvidenceError, match="sample_seconds"):
        worker_memory.observe(0)

    output = tmp_path / "evidence.json"
    monkeypatch.setattr(worker_memory, "observe", lambda _seconds: result)
    assert worker_memory.main(["--sample-seconds", "2", "--output", str(output)]) == 0
    assert json.loads(output.read_text())["classification"] == result["classification"]
