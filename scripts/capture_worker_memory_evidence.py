#!/usr/bin/env python3
"""Capture and compare non-identifying worker cgroup memory evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

SERVICE = "backend-worker"
PROJECT = "lineageweave"
EVENT_KEYS = ("low", "high", "max", "oom", "oom_kill", "oom_group_kill")


class MemoryEvidenceError(ValueError):
    """Reject incomplete or incomparable worker memory evidence."""


def _integer(value: Any, field: str) -> int:
    """Return a non-negative integer evidence field."""
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise MemoryEvidenceError(f"{field} must be an integer") from exc
    if result < 0:
        raise MemoryEvidenceError(f"{field} must not be negative")
    return result


def parse_flat_keys(value: str) -> dict[str, int]:
    """Parse a cgroup flat-keyed file without relying on line positions."""
    result: dict[str, int] = {}
    for line in value.splitlines():
        parts = line.split()
        if len(parts) != 2:
            raise MemoryEvidenceError("invalid cgroup flat-key evidence")
        try:
            result[parts[0]] = int(parts[1])
        except ValueError as exc:
            raise MemoryEvidenceError("invalid cgroup flat-key evidence") from exc
    return result


def _events(snapshot: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the required local cgroup memory-event mapping."""
    events = snapshot.get("memory_events_local")
    if not isinstance(events, Mapping):
        raise MemoryEvidenceError("memory.events.local is unavailable")
    return events


def compare_snapshots(
    before: Mapping[str, Any], after: Mapping[str, Any], *, elapsed_seconds: float
) -> dict[str, Any]:
    """Classify one unchanged-container observation without proposing a limit."""
    if elapsed_seconds <= 0:
        raise MemoryEvidenceError("elapsed_seconds must be positive")
    if not before.get("container_started_at") or (
        before.get("container_started_at") != after.get("container_started_at")
    ):
        raise MemoryEvidenceError("container changed during the observation")
    peak = after.get("memory_peak_bytes")
    if peak is None:
        raise MemoryEvidenceError("memory.peak is unavailable")
    observed_peak = _integer(peak, "memory_peak_bytes")
    before_events = _events(before)
    after_events = _events(after)
    deltas: dict[str, int] = {}
    for key in EVENT_KEYS:
        earlier = _integer(before_events.get(key, 0), f"memory.events.local.{key}")
        later = _integer(after_events.get(key, 0), f"memory.events.local.{key}")
        if later < earlier:
            raise MemoryEvidenceError(f"memory.events.local.{key} decreased")
        deltas[key] = later - earlier

    if bool(after.get("container_oom_killed")) or deltas["oom_kill"] > 0:
        classification = "oom_confirmed"
    elif _integer(after.get("container_exit_code", 0), "container_exit_code") == 137:
        classification = "sigkill_unattributed"
    elif any(deltas[key] for key in ("high", "max", "oom")):
        classification = "memory_pressure_observed"
    else:
        classification = "observed_without_memory_pressure"

    return {
        "contract_version": 1,
        "elapsed_seconds": elapsed_seconds,
        "classification": classification,
        "observed_peak_bytes": observed_peak,
        "ending_current_bytes": _integer(
            after.get("memory_current_bytes"), "memory_current_bytes"
        ),
        "configured_memory_limit_bytes": after.get("memory_limit_bytes"),
        "configured_memory_reservation_bytes": after.get("memory_reservation_bytes"),
        "event_deltas": deltas,
        # A representative peak does not establish safe headroom. Operators must
        # not turn it into a Compose limit by adding an undocumented multiplier.
        "memory_limit_proposal": None,
    }


def _run(command: Sequence[str], *, timeout: float = 15) -> str:
    """Run one bounded local command and return standard output."""
    try:
        completed = subprocess.run(
            list(command), text=True, capture_output=True, check=False, timeout=timeout
        )
    except subprocess.TimeoutExpired as exc:
        raise MemoryEvidenceError("container evidence command timed out") from exc
    if completed.returncode:
        raise MemoryEvidenceError(completed.stderr.strip() or "container evidence command failed")
    return completed.stdout.strip()


def capture_snapshot() -> dict[str, Any]:
    """Capture Docker state and cgroup v2 counters for the canonical worker."""
    container_id = _run(
        ["docker", "compose", "-p", PROJECT, "ps", "-q", SERVICE]
    )
    if not container_id:
        raise MemoryEvidenceError("canonical backend-worker container is unavailable")
    inspected = json.loads(_run(["docker", "inspect", container_id]))
    if not isinstance(inspected, list) or len(inspected) != 1:
        raise MemoryEvidenceError("Docker inspection is incomplete")
    state = inspected[0].get("State", {})
    host = inspected[0].get("HostConfig", {})
    if not isinstance(state, Mapping) or not isinstance(host, Mapping):
        raise MemoryEvidenceError("Docker state is incomplete")
    cgroup = _run(
        [
            "docker", "exec", container_id, "sh", "-eu", "-c",
            "test -r /sys/fs/cgroup/memory.current; "
            "test -r /sys/fs/cgroup/memory.peak; "
            "test -r /sys/fs/cgroup/memory.max; "
            "test -r /sys/fs/cgroup/memory.events.local; "
            "cat /sys/fs/cgroup/memory.current; "
            "cat /sys/fs/cgroup/memory.peak; "
            "cat /sys/fs/cgroup/memory.max; "
            "cat /sys/fs/cgroup/memory.events.local",
        ]
    ).splitlines()
    if len(cgroup) < 4:
        raise MemoryEvidenceError("cgroup v2 memory evidence is incomplete")
    memory_max = None if cgroup[2] == "max" else _integer(cgroup[2], "memory.max")
    events = parse_flat_keys("\n".join(cgroup[3:]))
    return {
        "captured_at": datetime.now(UTC).isoformat(),
        "container_started_at": state.get("StartedAt"),
        "container_status": state.get("Status"),
        "container_oom_killed": bool(state.get("OOMKilled")),
        "container_exit_code": _integer(state.get("ExitCode", 0), "container_exit_code"),
        "container_restart_count": _integer(
            inspected[0].get("RestartCount", 0), "container_restart_count"
        ),
        "memory_limit_bytes": _integer(host.get("Memory", 0), "memory_limit_bytes") or None,
        "memory_reservation_bytes": (
            _integer(host.get("MemoryReservation", 0), "memory_reservation_bytes") or None
        ),
        "memory_current_bytes": _integer(cgroup[0], "memory.current"),
        "memory_peak_bytes": _integer(cgroup[1], "memory.peak"),
        "memory_max_bytes": memory_max,
        "memory_events_local": events,
    }


def observe(sample_seconds: float) -> dict[str, Any]:
    """Capture an explicitly sized same-container observation window."""
    if sample_seconds <= 0:
        raise MemoryEvidenceError("sample_seconds must be positive")
    before = capture_snapshot()
    started = time.monotonic()
    time.sleep(sample_seconds)
    after = capture_snapshot()
    result = compare_snapshots(
        before, after, elapsed_seconds=time.monotonic() - started
    )
    result["before_captured_at"] = before["captured_at"]
    result["after_captured_at"] = after["captured_at"]
    return result


def main(argv: Sequence[str] | None = None) -> int:
    """Capture one worker-memory observation as non-identifying JSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-seconds", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    args.output.write_text(
        json.dumps(observe(args.sample_seconds), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
