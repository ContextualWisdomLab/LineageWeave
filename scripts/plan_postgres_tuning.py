#!/usr/bin/env python3
"""Measure, plan, validate, and deliberately apply PostgreSQL Compose tuning."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

MIB = 1024 * 1024
SUPPORTED_SERVER_MAJOR = 16
DURABILITY_SETTINGS = ("fsync", "full_page_writes", "synchronous_commit")
TUNED_COMPOSE_FILE = "docker-compose.postgres-tuned.yml"

SNAPSHOT_SQL = r"""
SELECT json_build_object(
  'captured_at', clock_timestamp(),
  'server_version_num', current_setting('server_version_num')::integer,
  'wal_stats_reset', w.stats_reset,
  'checkpoint_stats_reset', b.stats_reset,
  'wal_bytes', w.wal_bytes::text,
  'wal_buffers_full', w.wal_buffers_full,
  'checkpoints_timed', b.checkpoints_timed,
  'checkpoints_req', b.checkpoints_req,
  'wal_segment_size_bytes', pg_size_bytes(current_setting('wal_segment_size')),
  'settings', json_build_object(
  'checkpoint_timeout_seconds',
    current_setting('checkpoint_timeout')::interval / interval '1 second',
    'max_wal_size_bytes', pg_size_bytes(current_setting('max_wal_size')),
    'min_wal_size_bytes', pg_size_bytes(current_setting('min_wal_size')),
    'wal_buffers_bytes', pg_size_bytes(current_setting('wal_buffers')),
    'shared_buffers_bytes', pg_size_bytes(current_setting('shared_buffers')),
    'maintenance_work_mem_bytes', pg_size_bytes(current_setting('maintenance_work_mem')),
    'effective_io_concurrency', current_setting('effective_io_concurrency')::integer,
    'maintenance_io_concurrency', current_setting('maintenance_io_concurrency')::integer,
    'wal_compression', current_setting('wal_compression'),
    'fsync', current_setting('fsync'),
    'full_page_writes', current_setting('full_page_writes'),
    'synchronous_commit', current_setting('synchronous_commit')
  )
)
FROM pg_stat_wal AS w CROSS JOIN pg_stat_bgwriter AS b;
"""


class TuningPlanError(ValueError):
    """Reject incomplete or unsafe tuning evidence."""


@dataclass(frozen=True)
class Observation:
    """Two PostgreSQL counter snapshots and measured container resources."""

    before: Mapping[str, Any]
    after: Mapping[str, Any]
    elapsed_seconds: float
    container_memory_limit_bytes: int | None
    data_filesystem_free_bytes: int
    pg_wal_bytes: int


def _integer(value: Any, field: str) -> int:
    """Return one non-negative integer field or reject the snapshot."""
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise TuningPlanError(f"{field} must be an integer") from exc
    if result < 0:
        raise TuningPlanError(f"{field} must not be negative")
    return result


def _delta(before: Mapping[str, Any], after: Mapping[str, Any], field: str) -> int:
    """Calculate a monotonic PostgreSQL statistics-counter delta."""
    result = _integer(after.get(field), field) - _integer(before.get(field), field)
    if result < 0:
        raise TuningPlanError(f"{field} decreased during the observation")
    return result


def _require_aligned_resets(before: Mapping[str, Any], after: Mapping[str, Any]) -> None:
    """Reject observations spanning a PostgreSQL statistics reset."""
    for field in ("wal_stats_reset", "checkpoint_stats_reset"):
        if not before.get(field) or before.get(field) != after.get(field):
            raise TuningPlanError(f"{field} changed or is unavailable")


def _seconds_since(snapshot: Mapping[str, Any], reset_field: str) -> float:
    """Calculate one PostgreSQL-owned cumulative statistics window."""
    try:
        captured = datetime.fromisoformat(str(snapshot["captured_at"]).replace("Z", "+00:00"))
        reset = datetime.fromisoformat(str(snapshot[reset_field]).replace("Z", "+00:00"))
    except (KeyError, ValueError) as exc:
        raise TuningPlanError(f"{reset_field} observation window is invalid") from exc
    seconds = (captured - reset).total_seconds()
    if seconds <= 0:
        raise TuningPlanError(f"{reset_field} observation window must be positive")
    return seconds


def _settings(snapshot: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the measured PostgreSQL settings object."""
    settings = snapshot.get("settings")
    if not isinstance(settings, Mapping):
        raise TuningPlanError("settings are unavailable")
    return settings


def _require_durability(settings: Mapping[str, Any]) -> None:
    """Fail closed unless PostgreSQL durability remains enabled."""
    accepted = {"on", "true", "remote_apply", "remote_write", "local"}
    for field in DURABILITY_SETTINGS:
        if str(settings.get(field, "")).lower() not in accepted:
            raise TuningPlanError(f"durability setting {field} must remain enabled")


def _durability_value(settings: Mapping[str, Any], field: str) -> str:
    """Return one validated PostgreSQL durability setting unchanged."""
    value = str(settings.get(field, "")).lower()
    allowed = {
        "fsync": {"on"},
        "full_page_writes": {"on"},
        "synchronous_commit": {"on", "remote_apply", "remote_write", "local"},
    }
    if value not in allowed[field]:
        raise TuningPlanError(f"unsupported durability value for {field}")
    return value


def build_plan(observation: Observation) -> dict[str, Any]:
    """Build an evidence-derived, restart-only PostgreSQL tuning plan."""
    if observation.elapsed_seconds <= 0:
        raise TuningPlanError("elapsed_seconds must be positive")
    if observation.data_filesystem_free_bytes < 0 or observation.pg_wal_bytes < 0:
        raise TuningPlanError("filesystem measurements must not be negative")
    _require_aligned_resets(observation.before, observation.after)
    server_major = (
        _integer(observation.after.get("server_version_num"), "server_version_num")
        // 10000
    )
    if server_major != SUPPORTED_SERVER_MAJOR:
        raise TuningPlanError("the tuning contract supports PostgreSQL 16 only")

    before_settings = _settings(observation.before)
    after_settings = _settings(observation.after)
    if before_settings != after_settings:
        raise TuningPlanError("PostgreSQL settings changed during the observation")
    _require_durability(after_settings)

    segment_bytes = _integer(
        observation.after.get("wal_segment_size_bytes"), "wal_segment_size_bytes"
    )
    if segment_bytes == 0 or segment_bytes % MIB:
        raise TuningPlanError("wal_segment_size must be a positive whole number of MiB")
    timeout_seconds = float(after_settings.get("checkpoint_timeout_seconds", 0))
    if timeout_seconds <= 0:
        raise TuningPlanError("checkpoint_timeout_seconds must be positive")

    wal_bytes = _delta(observation.before, observation.after, "wal_bytes")
    wal_buffers_full = _delta(observation.before, observation.after, "wal_buffers_full")
    checkpoints_timed = _delta(observation.before, observation.after, "checkpoints_timed")
    checkpoints_req = _delta(observation.before, observation.after, "checkpoints_req")
    sample_wal_rate = wal_bytes / observation.elapsed_seconds
    cumulative_wal_seconds = _seconds_since(observation.after, "wal_stats_reset")
    cumulative_wal_rate = (
        _integer(observation.after.get("wal_bytes"), "wal_bytes") / cumulative_wal_seconds
    )
    selected_wal_rate = max(sample_wal_rate, cumulative_wal_rate)
    interval_wal_bytes = math.ceil(selected_wal_rate * timeout_seconds)
    interval_wal_segments = (
        math.ceil(interval_wal_bytes / segment_bytes) if interval_wal_bytes else 0
    )

    current_max_wal = _integer(after_settings.get("max_wal_size_bytes"), "max_wal_size_bytes")
    current_wal_buffers = _integer(after_settings.get("wal_buffers_bytes"), "wal_buffers_bytes")
    proposed_max_wal = max(current_max_wal, interval_wal_segments * segment_bytes)
    cumulative_wal_buffers_full = _integer(
        observation.after.get("wal_buffers_full"), "wal_buffers_full"
    )
    proposed_wal_buffers = (
        segment_bytes
        if wal_buffers_full or cumulative_wal_buffers_full
        else current_wal_buffers
    )

    existing_wal_reservation = max(current_max_wal, observation.pg_wal_bytes)
    additional_reservation = max(0, proposed_max_wal - existing_wal_reservation)
    if additional_reservation > observation.data_filesystem_free_bytes:
        raise TuningPlanError(
            "measured filesystem free space cannot hold the additional WAL reservation"
        )
    if (
        observation.container_memory_limit_bytes is not None
        and proposed_wal_buffers > observation.container_memory_limit_bytes
    ):
        raise TuningPlanError("container memory limit cannot hold the proposed WAL buffers")

    plan: dict[str, Any] = {
        "contract_version": 1,
        "requires_controlled_restart": True,
        "evidence": {
            "server_version_num": observation.after["server_version_num"],
            "before_captured_at": observation.before.get("captured_at"),
            "after_captured_at": observation.after.get("captured_at"),
            "wal_stats_reset": observation.after["wal_stats_reset"],
            "checkpoint_stats_reset": observation.after["checkpoint_stats_reset"],
            "elapsed_seconds": observation.elapsed_seconds,
            "wal_bytes": wal_bytes,
            "sample_wal_bytes_per_second": sample_wal_rate,
            "cumulative_wal_seconds": cumulative_wal_seconds,
            "cumulative_wal_bytes_per_second": cumulative_wal_rate,
            "selected_wal_bytes_per_second": selected_wal_rate,
            "wal_buffers_full": wal_buffers_full,
            "cumulative_wal_buffers_full": cumulative_wal_buffers_full,
            "checkpoints_timed": checkpoints_timed,
            "checkpoints_requested": checkpoints_req,
            "checkpoint_timeout_seconds": timeout_seconds,
            "wal_segment_size_bytes": segment_bytes,
            "container_memory_limit_bytes": observation.container_memory_limit_bytes,
            "data_filesystem_free_bytes": observation.data_filesystem_free_bytes,
            "pg_wal_bytes": observation.pg_wal_bytes,
            "additional_wal_reservation_bytes": additional_reservation,
        },
        "proposed": {
            "max_wal_size_bytes": proposed_max_wal,
            "wal_buffers_bytes": proposed_wal_buffers,
            **{
                field: _durability_value(after_settings, field)
                for field in DURABILITY_SETTINGS
            },
        },
        "rollback": {
            "max_wal_size_bytes": current_max_wal,
            "wal_buffers_bytes": current_wal_buffers,
            "fsync": str(after_settings["fsync"]),
            "full_page_writes": str(after_settings["full_page_writes"]),
            "synchronous_commit": str(after_settings["synchronous_commit"]),
        },
        "retained_unmeasured": {
            name: after_settings.get(name)
            for name in (
                "shared_buffers_bytes",
                "maintenance_work_mem_bytes",
                "effective_io_concurrency",
                "maintenance_io_concurrency",
                "wal_compression",
                "min_wal_size_bytes",
            )
        },
    }
    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    plan["plan_id"] = hashlib.sha256(canonical).hexdigest()
    return plan


def plan_environment(plan: Mapping[str, Any], *, rollback: bool = False) -> str:
    """Render the proposed or rollback settings as a Compose environment file."""
    section_name = "rollback" if rollback else "proposed"
    section = plan.get(section_name)
    if not isinstance(section, Mapping):
        raise TuningPlanError(f"{section_name} settings are unavailable")
    max_wal = _integer(section.get("max_wal_size_bytes"), "max_wal_size_bytes")
    wal_buffers = _integer(section.get("wal_buffers_bytes"), "wal_buffers_bytes")
    if max_wal % MIB or wal_buffers % MIB:
        raise TuningPlanError("Compose settings must be whole MiB values")
    durability = {
        field: _durability_value(section, field) for field in DURABILITY_SETTINGS
    }
    return (
        f"POSTGRES_TUNED_MAX_WAL_SIZE={max_wal // MIB}MB\n"
        f"POSTGRES_TUNED_WAL_BUFFERS={wal_buffers // MIB}MB\n"
        f"POSTGRES_TUNED_FSYNC={durability['fsync']}\n"
        f"POSTGRES_TUNED_FULL_PAGE_WRITES={durability['full_page_writes']}\n"
        f"POSTGRES_TUNED_SYNCHRONOUS_COMMIT={durability['synchronous_commit']}\n"
    )


def _run(command: Sequence[str], *, input_text: str | None = None) -> str:
    """Run one bounded local command and return standard output."""
    completed = subprocess.run(
        list(command), input=input_text, text=True, capture_output=True, check=False
    )
    if completed.returncode:
        raise TuningPlanError(completed.stderr.strip() or "command failed")
    return completed.stdout.strip()


def _postgres_snapshot() -> dict[str, Any]:
    """Read one PostgreSQL statistics snapshot through canonical Compose."""
    postgres_user = _run(
        ["docker", "compose", "exec", "-T", "postgres", "printenv", "POSTGRES_USER"]
    )
    postgres_database = _run(
        ["docker", "compose", "exec", "-T", "postgres", "printenv", "POSTGRES_DB"]
    )
    output = _run(
        [
            "docker", "compose", "exec", "-T", "postgres", "psql",
            "-X", "-v", "ON_ERROR_STOP=1", "-At", "-U",
            postgres_user, "-d", postgres_database, "-c", SNAPSHOT_SQL,
        ]
    )
    value = json.loads(output)
    if not isinstance(value, dict):
        raise TuningPlanError("PostgreSQL snapshot is not a JSON object")
    return value


def _container_resources() -> tuple[int | None, int, int]:
    """Measure cgroup memory and data-volume space from the PostgreSQL container."""
    output = _run(
        [
            "docker", "compose", "exec", "-T", "postgres", "sh", "-eu", "-c",
            "if [ -r /sys/fs/cgroup/memory.max ]; then cat /sys/fs/cgroup/memory.max; "
            "elif [ -r /sys/fs/cgroup/memory/memory.limit_in_bytes ]; then "
            "cat /sys/fs/cgroup/memory/memory.limit_in_bytes; else printf 'max\\n'; fi; "
            "df -Pk /var/lib/postgresql/data | awk 'NR==2 {print $4}'; "
            "du -sk /var/lib/postgresql/data/pg_wal | awk '{print $1}'",
        ]
    ).splitlines()
    if len(output) != 3:
        raise TuningPlanError("container resource measurement is incomplete")
    memory = None if output[0] == "max" else _integer(output[0], "container_memory_limit_bytes")
    return (
        memory,
        _integer(output[1], "data_filesystem_free_kib") * 1024,
        _integer(output[2], "pg_wal_kib") * 1024,
    )


def measure(sample_seconds: float, *, sleeper: Callable[[float], None] = time.sleep) -> Observation:
    """Measure PostgreSQL deltas over an explicitly selected observation window."""
    if sample_seconds <= 0:
        raise TuningPlanError("sample_seconds must be positive")
    before = _postgres_snapshot()
    started = time.monotonic()
    sleeper(sample_seconds)
    after = _postgres_snapshot()
    elapsed = time.monotonic() - started
    memory, free_bytes, pg_wal_bytes = _container_resources()
    return Observation(before, after, elapsed, memory, free_bytes, pg_wal_bytes)


def _load_plan(path: Path) -> dict[str, Any]:
    """Load and authenticate one generated audit plan."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or "plan_id" not in value:
        raise TuningPlanError("plan is incomplete")
    plan_id = value.pop("plan_id")
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    expected = hashlib.sha256(canonical).hexdigest()
    value["plan_id"] = plan_id
    if plan_id != expected:
        raise TuningPlanError("plan content does not match plan_id")
    return value


def validate_compose(plan: Mapping[str, Any], env_path: Path) -> None:
    """Validate the explicit tuning overlay without changing a container."""
    env_path.write_text(plan_environment(plan), encoding="utf-8")
    _run(
        [
            "docker", "compose", "--env-file", str(env_path),
            "-f", "docker-compose.yml", "-f", TUNED_COMPOSE_FILE, "config", "--quiet",
        ]
    )


def controlled_restart(plan: Mapping[str, Any], env_path: Path, approval: str) -> None:
    """Apply a validated plan only through an explicit PostgreSQL recreation."""
    if approval != plan.get("plan_id"):
        raise TuningPlanError("--approve-plan-id must match the audited plan")
    current = _settings(_postgres_snapshot())
    rollback = plan.get("rollback")
    if not isinstance(rollback, Mapping):
        raise TuningPlanError("rollback settings are unavailable")
    for field in ("max_wal_size_bytes", "wal_buffers_bytes"):
        if _integer(current.get(field), field) != _integer(rollback.get(field), field):
            raise TuningPlanError(f"current {field} no longer matches the audited plan")
    _require_durability(current)
    validate_compose(plan, env_path)
    _run(
        [
            "docker", "compose", "--env-file", str(env_path),
            "-f", "docker-compose.yml", "-f", TUNED_COMPOSE_FILE,
            "up", "-d", "--wait", "--no-deps", "--force-recreate", "postgres",
        ]
    )
    applied = _settings(_postgres_snapshot())
    proposed = plan["proposed"]
    for field in ("max_wal_size_bytes", "wal_buffers_bytes"):
        if _integer(applied.get(field), field) != _integer(proposed.get(field), field):
            raise TuningPlanError(f"PostgreSQL did not apply {field}")
    for field in DURABILITY_SETTINGS:
        if str(applied.get(field, "")).lower() != str(proposed.get(field, "")).lower():
            raise TuningPlanError(f"PostgreSQL did not preserve {field}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the tuning procedure command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--sample-seconds", type=float, required=True)
    plan_parser.add_argument("--output", type=Path, required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--plan", type=Path, required=True)
    validate_parser.add_argument("--env-output", type=Path, required=True)
    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--plan", type=Path, required=True)
    apply_parser.add_argument("--env-output", type=Path, required=True)
    apply_parser.add_argument("--approve-plan-id", required=True)
    rollback_parser = subparsers.add_parser("rollback")
    rollback_parser.add_argument("--plan", type=Path, required=True)
    rollback_parser.add_argument("--env-output", type=Path, required=True)
    rollback_parser.add_argument("--approve-plan-id", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the selected measure, validate, apply, or rollback phase."""
    args = parse_args(argv)
    if args.command == "plan":
        plan = build_plan(measure(args.sample_seconds))
        args.output.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(plan["plan_id"])
        return 0
    plan = _load_plan(args.plan)
    if args.command == "validate":
        validate_compose(plan, args.env_output)
        return 0
    if args.command == "rollback":
        rollback_plan = dict(plan)
        rollback_plan["proposed"] = plan["rollback"]
        rollback_plan["rollback"] = plan["proposed"]
        controlled_restart(rollback_plan, args.env_output, args.approve_plan_id)
        return 0
    controlled_restart(plan, args.env_output, args.approve_plan_id)
    return 0


if __name__ == "__main__":  # pragma: no cover - main() is exercised directly.
    raise SystemExit(main())
