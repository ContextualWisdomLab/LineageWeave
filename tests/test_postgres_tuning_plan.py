"""Evidence-derived PostgreSQL Compose tuning procedure contracts."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from types import ModuleType

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "plan_postgres_tuning.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("plan_postgres_tuning", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


tuning = _load_module()


def _snapshot(**changes: object) -> dict[str, object]:
    snapshot: dict[str, object] = {
        "captured_at": "2026-08-26T00:00:00Z",
        "server_version_num": 160014,
        "wal_stats_reset": "2026-08-24T00:00:00Z",
        "checkpoint_stats_reset": "2026-08-24T00:00:00Z",
        "wal_bytes": "0",
        "wal_buffers_full": 0,
        "checkpoints_timed": 0,
        "checkpoints_req": 0,
        "active_transaction_count": 0,
        "waiting_lock_count": 0,
        "wal_segment_size_bytes": 16 * tuning.MIB,
        "settings": {
            "checkpoint_timeout_seconds": 300,
            "max_wal_size_bytes": 1024 * tuning.MIB,
            "min_wal_size_bytes": 80 * tuning.MIB,
            "wal_buffers_bytes": 4 * tuning.MIB,
            "shared_buffers_bytes": 128 * tuning.MIB,
            "maintenance_work_mem_bytes": 64 * tuning.MIB,
            "effective_io_concurrency": 1,
            "maintenance_io_concurrency": 10,
            "wal_compression": "off",
            "fsync": "on",
            "full_page_writes": "on",
            "synchronous_commit": "on",
            "default_transaction_isolation": "read committed",
            "transaction_isolation": "read committed",
        },
    }
    snapshot.update(changes)
    return snapshot


def _observation(before: dict[str, object], after: dict[str, object], **changes: object):
    values = {
        "before": before,
        "after": after,
        "elapsed_seconds": 60.0,
        "container_memory_limit_bytes": 8 * 1024 * tuning.MIB,
        "data_filesystem_free_bytes": 100 * 1024 * tuning.MIB,
        "pg_wal_bytes": 1024 * tuning.MIB,
    }
    values.update(changes)
    return tuning.Observation(**values)


def test_plan_uses_measured_checkpoint_interval_and_segment_boundary() -> None:
    before = _snapshot()
    after = _snapshot(
        wal_bytes=str(600 * tuning.MIB),
        wal_buffers_full=12,
        checkpoints_req=4,
    )

    plan = tuning.build_plan(_observation(before, after))

    # 600 MiB / 60 s * 300 s = 3000 MiB, rounded to a 16 MiB WAL segment.
    assert plan["proposed"]["max_wal_size_bytes"] == 3008 * tuning.MIB
    assert plan["proposed"]["wal_buffers_bytes"] == 16 * tuning.MIB
    assert plan["proposed"]["default_transaction_isolation"] == "read committed"
    assert plan["proposed"]["transaction_isolation"] == "read committed"
    assert plan["evidence"]["checkpoints_requested"] == 4
    assert plan["retained_unmeasured"]["effective_io_concurrency"] == 1
    assert plan["retained_unmeasured"]["wal_compression"] == "off"


def test_plan_retains_settings_when_observation_has_no_pressure() -> None:
    before = _snapshot()
    after = _snapshot(checkpoints_timed=1)

    plan = tuning.build_plan(_observation(before, after))

    assert plan["proposed"]["max_wal_size_bytes"] == 1024 * tuning.MIB
    assert plan["proposed"]["wal_buffers_bytes"] == 4 * tuning.MIB


def test_plan_keeps_historical_pressure_distinct_from_idle_sample() -> None:
    before = _snapshot(wal_bytes=str(287 * 1024 * tuning.MIB), wal_buffers_full=7_404_489)
    after = _snapshot(
        captured_at="2026-08-26T00:00:00Z",
        wal_bytes=str(287 * 1024 * tuning.MIB),
        wal_buffers_full=7_404_489,
        checkpoints_req=21_990,
        checkpoints_timed=257,
    )

    plan = tuning.build_plan(_observation(before, after))

    assert plan["evidence"]["wal_bytes"] == 0
    assert plan["evidence"]["sample_wal_bytes_per_second"] == 0
    assert plan["evidence"]["cumulative_wal_bytes_per_second"] > 0
    # The cumulative average alone does not justify exceeding the current 1 GiB.
    assert plan["proposed"]["max_wal_size_bytes"] == 1024 * tuning.MIB
    assert plan["proposed"]["wal_buffers_bytes"] == 16 * tuning.MIB


@pytest.mark.parametrize(
    ("before", "after", "message"),
    [
        (_snapshot(), _snapshot(wal_stats_reset="later"), "wal_stats_reset"),
        (_snapshot(wal_bytes="2"), _snapshot(wal_bytes="1"), "wal_bytes decreased"),
        (
            _snapshot(settings={**_snapshot()["settings"], "fsync": "off"}),
            _snapshot(settings={**_snapshot()["settings"], "fsync": "off"}),
            "durability setting fsync",
        ),
        (
            _snapshot(settings={**_snapshot()["settings"], "transaction_isolation": "serializable"}),
            _snapshot(settings={**_snapshot()["settings"], "transaction_isolation": "serializable"}),
            "isolation changed from the approved default",
        ),
    ],
)
def test_plan_rejects_incomparable_or_unsafe_evidence(
    before: dict[str, object], after: dict[str, object], message: str
) -> None:
    with pytest.raises(tuning.TuningPlanError, match=message):
        tuning.build_plan(_observation(before, after))


def test_plan_rejects_exact_additional_wal_beyond_free_space() -> None:
    before = _snapshot()
    after = _snapshot(wal_bytes=str(600 * tuning.MIB))

    with pytest.raises(tuning.TuningPlanError, match="free space"):
        tuning.build_plan(
            _observation(before, after, data_filesystem_free_bytes=1983 * tuning.MIB)
        )


def test_environment_preserves_durability_and_supports_rollback() -> None:
    before = _snapshot()
    after = _snapshot(wal_buffers_full=1)
    plan = tuning.build_plan(_observation(before, after))

    proposed = tuning.plan_environment(plan)
    rollback = tuning.plan_environment(plan, rollback=True)

    assert "POSTGRES_TUNED_WAL_BUFFERS=16MB" in proposed
    assert "POSTGRES_TUNED_WAL_BUFFERS=4MB" in rollback
    assert "POSTGRES_TUNED_FSYNC=on" in proposed
    assert "POSTGRES_TUNED_FULL_PAGE_WRITES=on" in proposed
    assert "POSTGRES_TUNED_SYNCHRONOUS_COMMIT=on" in proposed


def test_environment_preserves_retained_block_aligned_wal_buffers() -> None:
    settings = {**_snapshot()["settings"], "wal_buffers_bytes": 640 * tuning.KIB}
    plan = tuning.build_plan(
        _observation(_snapshot(settings=settings), _snapshot(settings=settings))
    )

    assert "POSTGRES_TUNED_WAL_BUFFERS=640kB" in tuning.plan_environment(plan)


def test_compose_overlay_has_no_unmeasured_tuning_or_durability_relaxation() -> None:
    overlay = (_ROOT / "docker-compose.postgres-tuned.yml").read_text(encoding="utf-8")

    assert "max_wal_size=${POSTGRES_TUNED_MAX_WAL_SIZE:" in overlay
    assert "wal_buffers=${POSTGRES_TUNED_WAL_BUFFERS:" in overlay
    assert "fsync=${POSTGRES_TUNED_FSYNC:" in overlay
    assert "shared_buffers" not in overlay
    assert "maintenance_work_mem" not in overlay
    assert "effective_io_concurrency" not in overlay
    assert "wal_compression" not in overlay


def test_measure_uses_explicit_window_and_container_evidence(monkeypatch) -> None:
    snapshots = iter([_snapshot(), _snapshot(wal_bytes="10")])
    sleeps: list[float] = []
    monotonic = iter([100.0, 112.5])
    monkeypatch.setattr(tuning, "_postgres_snapshot", lambda: next(snapshots))
    monkeypatch.setattr(
        tuning, "_container_resources", lambda: (2048 * tuning.MIB, 4096, 1024)
    )
    monkeypatch.setattr(tuning.time, "monotonic", lambda: next(monotonic))

    observation = tuning.measure(12.5, sleeper=sleeps.append)

    assert sleeps == [12.5]
    assert observation.elapsed_seconds == 12.5
    assert observation.container_memory_limit_bytes == 2048 * tuning.MIB


def test_controlled_restart_checks_old_and_new_settings(monkeypatch, tmp_path: Path) -> None:
    plan = tuning.build_plan(
        _observation(_snapshot(), _snapshot(wal_buffers_full=1))
    )
    snapshots = iter(
        [
            _snapshot(),
            _snapshot(
                settings={
                    **_snapshot()["settings"],
                    "wal_buffers_bytes": 16 * tuning.MIB,
                }
            ),
        ]
    )
    commands: list[list[str]] = []
    monkeypatch.setattr(tuning, "_postgres_snapshot", lambda: next(snapshots))
    monkeypatch.setattr(
        tuning,
        "_container_resources",
        lambda: (8 * 1024 * tuning.MIB, 100 * 1024 * tuning.MIB, 1024 * tuning.MIB),
    )
    monkeypatch.setattr(
        tuning, "_run", lambda command, **_kwargs: commands.append(list(command)) or ""
    )

    tuning.controlled_restart(plan, tmp_path / "tuning.env", plan["plan_id"])

    assert any("config" in command and "--quiet" in command for command in commands)
    apply = next(command for command in commands if "up" in command)
    assert "--wait" in apply
    assert "--force-recreate" in apply


def test_controlled_restart_rejects_stale_plan_before_compose(monkeypatch, tmp_path: Path) -> None:
    plan = tuning.build_plan(_observation(_snapshot(), _snapshot()))
    stale = _snapshot(
        settings={
            **_snapshot()["settings"],
            "max_wal_size_bytes": 2048 * tuning.MIB,
        }
    )
    monkeypatch.setattr(tuning, "_postgres_snapshot", lambda: stale)
    monkeypatch.setattr(
        tuning,
        "_run",
        lambda *_args, **_kwargs: pytest.fail("Compose must not run for a stale plan"),
    )

    with pytest.raises(tuning.TuningPlanError, match="no longer matches"):
        tuning.controlled_restart(plan, tmp_path / "tuning.env", plan["plan_id"])


@pytest.mark.parametrize(
    ("current", "message"),
    [
        (
            _snapshot(
                settings={
                    **_snapshot()["settings"],
                    "synchronous_commit": "remote_write",
                }
            ),
            "synchronous_commit no longer matches",
        ),
        (
            _snapshot(
                settings={
                    **_snapshot()["settings"],
                    "default_transaction_isolation": "serializable",
                    "transaction_isolation": "serializable",
                }
            ),
            "default_transaction_isolation no longer matches",
        ),
        (_snapshot(server_version_num=170000), "server major no longer matches"),
        (_snapshot(active_transaction_count=1), "active transactions must be zero"),
        (_snapshot(waiting_lock_count=1), "waiting locks must be zero"),
    ],
)
def test_controlled_restart_revalidates_exact_database_state(
    monkeypatch, tmp_path: Path, current: dict[str, object], message: str
) -> None:
    plan = tuning.build_plan(_observation(_snapshot(), _snapshot()))
    monkeypatch.setattr(tuning, "_postgres_snapshot", lambda: current)
    monkeypatch.setattr(
        tuning,
        "_run",
        lambda *_args, **_kwargs: pytest.fail("Compose must not restart for stale evidence"),
    )

    with pytest.raises(tuning.TuningPlanError, match=message):
        tuning.controlled_restart(plan, tmp_path / "tuning.env", plan["plan_id"])


@pytest.mark.parametrize(
    ("resources", "message"),
    [
        ((None, 0, 1024 * tuning.MIB), "current filesystem free space"),
        ((1, 100 * 1024 * tuning.MIB, 1024 * tuning.MIB), "current container memory limit"),
    ],
)
def test_controlled_restart_revalidates_current_resources(
    monkeypatch,
    tmp_path: Path,
    resources: tuple[int | None, int, int],
    message: str,
) -> None:
    plan = tuning.build_plan(
        _observation(_snapshot(), _snapshot(wal_bytes=str(600 * tuning.MIB)))
    )
    monkeypatch.setattr(tuning, "_postgres_snapshot", _snapshot)
    monkeypatch.setattr(tuning, "_container_resources", lambda: resources)
    monkeypatch.setattr(
        tuning,
        "_run",
        lambda *_args, **_kwargs: pytest.fail("Compose must not restart for stale resources"),
    )

    with pytest.raises(tuning.TuningPlanError, match=message):
        tuning.controlled_restart(plan, tmp_path / "tuning.env", plan["plan_id"])


@pytest.mark.parametrize("value", [None, "bad"])
def test_integer_rejects_non_integer(value: object) -> None:
    with pytest.raises(tuning.TuningPlanError, match="must be an integer"):
        tuning._integer(value, "value")


def test_integer_rejects_negative() -> None:
    with pytest.raises(tuning.TuningPlanError, match="must not be negative"):
        tuning._integer(-1, "value")


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"elapsed_seconds": 0}, "elapsed_seconds"),
        ({"data_filesystem_free_bytes": -1}, "filesystem measurements"),
        ({"pg_wal_bytes": -1}, "filesystem measurements"),
        ({"container_memory_limit_bytes": 1}, "memory limit"),
    ],
)
def test_plan_rejects_invalid_observation_resources(
    changes: dict[str, object], message: str
) -> None:
    before = _snapshot()
    after = _snapshot(wal_buffers_full=1)
    with pytest.raises(tuning.TuningPlanError, match=message):
        tuning.build_plan(_observation(before, after, **changes))


@pytest.mark.parametrize(
    ("before", "after", "message"),
    [
        (_snapshot(), _snapshot(server_version_num=170000), "PostgreSQL 16"),
        (_snapshot(), _snapshot(settings=None), "settings are unavailable"),
        (
            _snapshot(),
            _snapshot(settings={**_snapshot()["settings"], "wal_compression": "on"}),
            "settings changed",
        ),
        (_snapshot(), _snapshot(wal_segment_size_bytes=0), "wal_segment_size"),
        (_snapshot(), _snapshot(wal_segment_size_bytes=tuning.MIB + 1), "wal_segment_size"),
        (
            _snapshot(settings={**_snapshot()["settings"], "checkpoint_timeout_seconds": 0}),
            _snapshot(settings={**_snapshot()["settings"], "checkpoint_timeout_seconds": 0}),
            "checkpoint_timeout",
        ),
    ],
)
def test_plan_rejects_unsupported_database_evidence(
    before: dict[str, object], after: dict[str, object], message: str
) -> None:
    with pytest.raises(tuning.TuningPlanError, match=message):
        tuning.build_plan(_observation(before, after))


def test_environment_rejects_missing_or_misaligned_values() -> None:
    with pytest.raises(tuning.TuningPlanError, match="settings are unavailable"):
        tuning.plan_environment({})
    with pytest.raises(tuning.TuningPlanError, match="whole MiB"):
        tuning.plan_environment(
            {
                "proposed": {
                    "max_wal_size_bytes": tuning.MIB + 1,
                    "wal_buffers_bytes": tuning.MIB,
                    "fsync": "on",
                    "full_page_writes": "on",
                    "synchronous_commit": "on",
                }
            }
        )


def test_durability_value_rejects_unsupported_mode() -> None:
    with pytest.raises(tuning.TuningPlanError, match="unsupported durability"):
        tuning._durability_value({"synchronous_commit": "off"}, "synchronous_commit")


def test_run_returns_stdout_and_reports_command_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        tuning.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout=" ok \n", stderr=""),
    )
    assert tuning._run(["command"]) == "ok"
    monkeypatch.setattr(
        tuning.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout="", stderr="bad"),
    )
    with pytest.raises(tuning.TuningPlanError, match="bad"):
        tuning._run(["command"])


def test_snapshot_reads_compose_environment_and_json(monkeypatch) -> None:
    outputs = iter(["app-user", "app-db", '{"settings": {}}'])
    commands: list[list[str]] = []

    def fake_run(command, **_kwargs):
        commands.append(list(command))
        return next(outputs)

    monkeypatch.setattr(tuning, "_run", fake_run)
    assert tuning._postgres_snapshot() == {"settings": {}}
    assert "app-user" in commands[-1]
    assert "app-db" in commands[-1]

    monkeypatch.setattr(tuning, "_run", lambda *_args, **_kwargs: "[]")
    with pytest.raises(tuning.TuningPlanError, match="JSON object"):
        tuning._postgres_snapshot()


def test_snapshot_uses_only_aggregate_restart_fence_evidence() -> None:
    assert "active_transaction_count" in tuning.SNAPSHOT_SQL
    assert "waiting_lock_count" in tuning.SNAPSHOT_SQL
    assert "pg_backend_pid()" in tuning.SNAPSHOT_SQL
    assert "query" not in tuning.SNAPSHOT_SQL.lower()


def test_container_resource_measurement_handles_cgroup_limit(monkeypatch) -> None:
    monkeypatch.setattr(tuning, "_run", lambda *_args, **_kwargs: "max\n4096\n1024")
    assert tuning._container_resources() == (None, 4096 * 1024, 1024 * 1024)
    monkeypatch.setattr(tuning, "_run", lambda *_args, **_kwargs: "8192\n4096\n1024")
    assert tuning._container_resources() == (8192, 4096 * 1024, 1024 * 1024)
    monkeypatch.setattr(tuning, "_run", lambda *_args, **_kwargs: "incomplete")
    with pytest.raises(tuning.TuningPlanError, match="incomplete"):
        tuning._container_resources()


def test_measure_rejects_non_positive_window() -> None:
    with pytest.raises(tuning.TuningPlanError, match="sample_seconds"):
        tuning.measure(0)


@pytest.mark.parametrize(
    ("snapshot", "message"),
    [
        ({"captured_at": "bad", "wal_stats_reset": "also-bad"}, "window is invalid"),
        (
            {"captured_at": "2026-08-24T00:00:00Z", "wal_stats_reset": "2026-08-24T00:00:00Z"},
            "must be positive",
        ),
    ],
)
def test_cumulative_window_rejects_invalid_timestamps(
    snapshot: dict[str, str], message: str
) -> None:
    with pytest.raises(tuning.TuningPlanError, match=message):
        tuning._seconds_since(snapshot, "wal_stats_reset")


def test_load_plan_authenticates_content(tmp_path: Path) -> None:
    plan = tuning.build_plan(_observation(_snapshot(), _snapshot()))
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    assert tuning._load_plan(path) == plan
    path.write_text('{"plan_id": "wrong"}', encoding="utf-8")
    with pytest.raises(tuning.TuningPlanError, match="does not match"):
        tuning._load_plan(path)
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(tuning.TuningPlanError, match="incomplete"):
        tuning._load_plan(path)


def test_controlled_restart_rejects_approval_and_missing_rollback(tmp_path: Path) -> None:
    plan = tuning.build_plan(_observation(_snapshot(), _snapshot()))
    with pytest.raises(tuning.TuningPlanError, match="approve-plan-id"):
        tuning.controlled_restart(plan, tmp_path / "env", "wrong")
    invalid = {**plan, "rollback": None}
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(tuning, "_postgres_snapshot", _snapshot)
        with pytest.raises(tuning.TuningPlanError, match="rollback settings"):
            tuning.controlled_restart(invalid, tmp_path / "env", plan["plan_id"])


@pytest.mark.parametrize(
    ("applied_changes", "message"),
    [
        ({"wal_buffers_bytes": 8 * tuning.MIB}, "did not apply wal_buffers"),
        ({"synchronous_commit": "remote_apply"}, "did not preserve synchronous_commit"),
        ({"transaction_isolation": "serializable"}, "did not preserve transaction_isolation"),
    ],
)
def test_controlled_restart_verifies_applied_settings(
    monkeypatch, tmp_path: Path, applied_changes: dict[str, object], message: str
) -> None:
    plan = tuning.build_plan(_observation(_snapshot(), _snapshot(wal_buffers_full=1)))
    applied = _snapshot(
        settings={
            **_snapshot()["settings"],
            "wal_buffers_bytes": 16 * tuning.MIB,
            **applied_changes,
        }
    )
    snapshots = iter([_snapshot(), applied])
    monkeypatch.setattr(tuning, "_postgres_snapshot", lambda: next(snapshots))
    monkeypatch.setattr(
        tuning,
        "_container_resources",
        lambda: (8 * 1024 * tuning.MIB, 100 * 1024 * tuning.MIB, 1024 * tuning.MIB),
    )
    monkeypatch.setattr(tuning, "_run", lambda *_args, **_kwargs: "")
    with pytest.raises(tuning.TuningPlanError, match=message):
        tuning.controlled_restart(plan, tmp_path / "env", plan["plan_id"])


def test_main_plan_validate_apply_and_rollback(monkeypatch, tmp_path: Path, capsys) -> None:
    plan = tuning.build_plan(_observation(_snapshot(), _snapshot()))
    plan_path = tmp_path / "plan.json"
    env_path = tmp_path / "env"
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(tuning, "measure", lambda _seconds: _observation(_snapshot(), _snapshot()))
    assert tuning.main(["plan", "--sample-seconds", "1", "--output", str(plan_path)]) == 0
    assert capsys.readouterr().out.strip() == json.loads(plan_path.read_text())["plan_id"]
    monkeypatch.setattr(tuning, "validate_compose", lambda *_args: calls.append(("validate", "")))
    assert tuning.main(["validate", "--plan", str(plan_path), "--env-output", str(env_path)]) == 0

    def fake_restart(selected, _env, approval):
        calls.append(("restart", approval))
        assert selected["plan_id"] == plan["plan_id"]

    monkeypatch.setattr(tuning, "controlled_restart", fake_restart)
    for command in ("apply", "rollback"):
        assert (
            tuning.main(
                [
                    command,
                    "--plan",
                    str(plan_path),
                    "--env-output",
                    str(env_path),
                    "--approve-plan-id",
                    plan["plan_id"],
                ]
            )
            == 0
        )
    assert calls[0][0] == "validate"
    assert [item[0] for item in calls].count("restart") == 2
