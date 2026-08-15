import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from tests._contract_utils import assert_audit_event_contract, load_contract


_UV_PREFIX: str = "#!/usr/bin/env bash\n"
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_NAME = "lineageweave_real_audit_event_schema.json"


def _write_fake_uv_script(tmp_path: Path, body: str, emit_call: bool = False) -> None:
    """Create a fake uv binary with deterministic exit behavior."""
    lines = [_UV_PREFIX]
    if emit_call:
        lines.append('echo "uv called $*" >&2')
    lines.append(body)
    uv_script = tmp_path / "uv"
    uv_script.write_text("\n".join(lines) + "\n", encoding="utf-8")
    uv_script.chmod(0o755)


def _base_env(tmp_path: Path) -> dict[str, str]:
    """Build the shared environment for smoke tests."""
    command_env = os.environ.copy()
    command_env.update(
        {
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "LINEAGEWEAVE_DSN": "postgresql://user:pass@localhost/postgres",
            "LINEAGE_SOURCE_TABLE": "public.customer_engagement_rows",
            "LINEAGEWEAVE_WRITE_REPORTS": "0",
            "LINEAGEWEAVE_KEYMAN_LIMIT": "0",
            "LINEAGEWEAVE_LIMIT": "1",
            "LINEAGEWEAVE_VALIDATE_RUNTIME_SCHEMA": "0",
            "LINEAGEWEAVE_SWEEP_CONTENT_INSPECTIONS": "0",
        }
    )
    return command_env


def _run_real_script(
    tmp_path: Path,
    uv_body: str,
    emit_call: bool = False,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Execute the real run script with a fake uv and a controlled exit code."""
    _write_fake_uv_script(tmp_path, uv_body, emit_call=emit_call)
    command_env = _base_env(tmp_path)
    if env_overrides:
        command_env.update(env_overrides)
    return subprocess.run(
        ["bash", "scripts/run_real_lineageweave.sh"],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        env=command_env,
    )


def _collect_audit_events(output: str) -> list[dict]:
    """Collect JSON audit records emitted by the run script."""
    rows: list[dict] = []
    for line in output.splitlines():
        if not line.startswith("lineageweave_audit_log="):
            continue
        payload = line.split("=", 1)[1]
        rows.append(json.loads(payload))
    return rows


def _assert_timestamp_utc(event: dict) -> None:
    """Validate event timestamp format for machine parsing."""
    parsed = datetime.fromisoformat(str(event["timestamp_utc"]).replace("Z", "+00:00"))
    assert parsed.tzinfo == timezone.utc


def _assert_upstream_pr_audit_fields(event: dict) -> None:
    """Validate new upstream-PR audit fields are always present."""
    assert event["tepp_open_pull_requests"] != ""
    assert event["contextual_orchestrator_open_pull_requests"] != ""


def _load_audit_event_schema() -> dict:
    """Load event contract requirements from JSON resources."""
    return load_contract(_SCHEMA_NAME)


def _assert_audit_event_schema(event: dict) -> None:
    """Validate required audit event fields and types for contract parsing."""
    assert_audit_event_contract(event, _load_audit_event_schema())


def test_run_real_script_emits_audit_events_for_successful_smoke(tmp_path: Path) -> None:
    """Smoke run should emit start and complete JSON events with required fields."""
    completed = _run_real_script(tmp_path, "exit 0", emit_call=True)
    assert completed.returncode == 0
    events = _collect_audit_events(completed.stdout)
    assert [event["event"] for event in events] == [
        "lineageweave_real_run_start",
        "lineageweave_real_run_complete",
        "lineageweave_real_run_exit",
    ]
    start_event = events[0]
    complete_event = events[1]
    exit_event = events[2]
    for event in events:
        _assert_audit_event_schema(event)
        _assert_upstream_pr_audit_fields(event)
    assert start_event["source_dsn"] == "postgresql://***:***@localhost/postgres"
    assert start_event["source_table"] == "public.customer_engagement_rows"
    assert start_event["write_reports"] == "0"
    assert start_event["keyman_limit"] == "0"
    assert start_event["limit"] == "1"
    assert start_event["sweep_content_inspections"] == "0"
    assert start_event["inspection_document_limit"] == "0"
    assert start_event["validate_runtime_schema"] == "0"
    assert start_event["json_out"] == "disabled"
    assert start_event["analytics_out"] == "disabled"
    assert complete_event["runtime_schema_contract_check"] == "disabled"
    assert complete_event["json_out"] == "disabled"
    assert complete_event["analytics_out"] == "disabled"
    assert exit_event["runtime_schema_contract_check"] == "disabled"
    assert exit_event["json_out"] == "disabled"
    assert exit_event["analytics_out"] == "disabled"
    assert exit_event["exit_code"] == "0"
    assert "--json-out" not in completed.stderr
    assert "--analytics-out" not in completed.stderr
    _assert_timestamp_utc(start_event)
    _assert_timestamp_utc(complete_event)
    _assert_timestamp_utc(exit_event)


def test_run_real_script_passes_only_explicit_export_paths(tmp_path: Path) -> None:
    """Detached exports remain available only when an operator opts in."""
    json_out = tmp_path / "operator-export.json"
    analytics_out = tmp_path / "operator-analytics.json"
    completed = _run_real_script(
        tmp_path,
        "exit 0",
        emit_call=True,
        env_overrides={
            "LINEAGEWEAVE_JSON_OUT": str(json_out),
            "LINEAGEWEAVE_ANALYTICS_OUT": str(analytics_out),
        },
    )
    assert completed.returncode == 0
    assert f"--json-out {json_out}" in completed.stderr
    assert f"--analytics-out {analytics_out}" in completed.stderr
    for event in _collect_audit_events(completed.stdout):
        assert event["json_out"] == str(json_out)
        assert event["analytics_out"] == str(analytics_out)
        _assert_upstream_pr_audit_fields(event)


def test_run_real_script_emits_failure_exit_code_in_audit_event(tmp_path: Path) -> None:
    """Failure run should still emit exit audit JSON and preserve failure code."""
    completed = _run_real_script(tmp_path, "exit 42", emit_call=True)
    assert completed.returncode == 42
    events = _collect_audit_events(completed.stdout)
    assert events[-1]["event"] == "lineageweave_real_run_exit"
    assert events[-1]["exit_code"] == "42"
    for event in events:
        _assert_audit_event_schema(event)
        _assert_upstream_pr_audit_fields(event)
    _assert_timestamp_utc(events[-1])


def test_run_real_script_emits_exit_audit_event_on_validation_error(tmp_path: Path) -> None:
    """Invalid limit should fail fast and still record an exit audit event."""
    completed = _run_real_script(
        tmp_path,
        "exit 0",
        emit_call=False,
        env_overrides={"LINEAGEWEAVE_LIMIT": "-1"},
    )
    assert completed.returncode == 1
    events = _collect_audit_events(completed.stdout)
    assert [event["event"] for event in events] == [
        "lineageweave_real_run_start",
        "lineageweave_real_run_exit",
    ]
    for event in events:
        _assert_audit_event_schema(event)
        _assert_upstream_pr_audit_fields(event)
    assert events[-1]["exit_code"] == "1"
    assert "invalid LINEAGEWEAVE_LIMIT" in completed.stdout
    _assert_timestamp_utc(events[0])
    _assert_timestamp_utc(events[1])
