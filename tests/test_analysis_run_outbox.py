"""Static and unit contracts for the durable analysis-run start outbox."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from backend.app.analysis_run_outbox import (
    OUTBOX_STREAM_KEY,
    latest_outbox_delivery_is_claimed,
    latest_outbox_delivery_is_delivered,
    outbox_request_digest,
    outbox_stream_fields,
)
from backend.app.analysis_run_start import start_kind_rejection

_ROOT = Path(__file__).resolve().parents[1]
_OUTBOX_MIGRATION = _ROOT / "migrations" / "0023_analysis_run_outbox.sql"
_OUTBOX_ROLLBACK = _ROOT / "migrations" / "rollback" / "0023_analysis_run_outbox.sql"
_POSTGRES_IMAGE = _ROOT / "docker" / "postgres-init" / "Dockerfile"


def test_outbox_migration_is_normalized_and_wired() -> None:
    """Static contract: 3NF names, no payload JSON, Dockerfile copy, rollback."""
    migration = _OUTBOX_MIGRATION.read_text(encoding="utf-8")
    rollback = _OUTBOX_ROLLBACK.read_text(encoding="utf-8")
    dockerfile = _POSTGRES_IMAGE.read_text(encoding="utf-8")
    created_tables = set(
        re.findall(r"create table if not exists\s+([a-z0-9_]+)", migration, re.I)
    )
    assert {"analysis_run_outbox", "analysis_run_outbox_delivery"} <= created_tables
    assert "jsonb" not in migration.casefold()
    assert "metadata_payload" not in migration
    assert "theta" not in migration.casefold()
    assert "0023_analysis_run_outbox.sql" in dockerfile
    assert "analysis_run_outbox_not_empty" in rollback
    assert "reject_analysis_run_outbox_mutation" in migration
    assert "reject_analysis_run_outbox_delivery_mutation" in migration
    assert "analysis_run_lineage_edge" in migration
    assert "analysis_source_snapshot_member" in migration
    object_patterns = (
        r"create table if not exists\s+([a-z0-9_]+)",
        r"create or replace function\s+([a-z0-9_]+)",
        r"create trigger\s+([a-z0-9_]+)",
    )
    for pattern in object_patterns:
        for object_name in re.findall(pattern, migration, re.I):
            assert len(object_name.split("_")) >= 2, object_name


def test_outbox_request_digest_is_stable_and_ignores_bodies() -> None:
    """The same frozen start hashes the same way and never includes a body."""
    cutoff = datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc)
    digest = outbox_request_digest(
        analysis_run_id="11111111-1111-1111-1111-111111111111",
        work_kind_code="analysis_run_lineage",
        snapshot_sha256="ab" * 32,
        knowledge_cutoff=cutoff,
    )
    again = outbox_request_digest(
        analysis_run_id="11111111-1111-1111-1111-111111111111",
        work_kind_code="analysis_run_lineage",
        snapshot_sha256="ab" * 32,
        knowledge_cutoff=datetime(2026, 1, 12, 12, 0),
    )
    other = outbox_request_digest(
        analysis_run_id="11111111-1111-1111-1111-111111111111",
        work_kind_code="analysis_run_tepp",
        snapshot_sha256="ab" * 32,
        knowledge_cutoff=cutoff,
    )
    assert digest == again
    assert digest != other
    assert "theta" not in digest
    assert "Pricing renegotiation" not in digest


def test_outbox_stream_fields_are_the_wake_up_only() -> None:
    """Valkey carries the run id and digest, never a measurement."""
    fields = outbox_stream_fields(
        analysis_run_id="11111111-1111-1111-1111-111111111111",
        work_kind_code="analysis_run_tepp",
        request_sha256="cd" * 32,
    )
    assert fields["work_kind_code"] == "analysis_run_tepp"
    assert fields["request_sha256"] == "cd" * 32
    assert "theta" not in str(fields).casefold()
    assert OUTBOX_STREAM_KEY == "analysis-run-outbox"


def test_outbox_delivery_helpers_distinguish_claimed_from_done() -> None:
    """A claimed row is retryable. A delivered row is finished."""
    assert latest_outbox_delivery_is_claimed("analysis_outbox_claimed")
    assert not latest_outbox_delivery_is_claimed("analysis_outbox_delivered")
    assert latest_outbox_delivery_is_delivered("analysis_outbox_delivered")
    assert not latest_outbox_delivery_is_delivered(None)


def test_period_report_never_enters_the_start_outbox() -> None:
    """The outbox is for lineage and TEPP start, not a fabricated report."""
    report = start_kind_rejection("analysis_run_report")
    assert report is not None
    assert report.status_code == 422
    assert report.detail == "기간 보고서 화면에서 다시 계산하세요."
