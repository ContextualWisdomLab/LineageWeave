"""Authorized analysis-run create hashes the cutoff bag, never a score."""

from datetime import datetime, timezone
from pathlib import Path

from backend.app.analysis_run_ingestion import (
    AnalysisRunCreateError,
    _resolve_corporate_entity_id,
    live_write_after_cutoff,
    plan_analysis_run_capture,
)
import pytest


_CUTOFF = datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc)
_EARLIER = datetime(2026, 1, 10, 9, 0, tzinfo=timezone.utc)


def test_capture_digest_is_stable_for_the_same_authorized_bag() -> None:
    first = plan_analysis_run_capture(
        run_kind_code="analysis_run_lineage",
        scope_kind_code="analysis_scope_corporate_entity",
        corporate_entity_id="corp-1",
        knowledge_cutoff=_CUTOFF,
        idempotency_key="client-key-1",
        post_ids=["post-b", "post-a"],
        thread_keys=["thread-a", "thread-a"],
        latest_post_created_at=_EARLIER,
    )
    second = plan_analysis_run_capture(
        run_kind_code="analysis_run_lineage",
        scope_kind_code="analysis_scope_corporate_entity",
        corporate_entity_id="corp-1",
        knowledge_cutoff=_CUTOFF,
        idempotency_key="client-key-1",
        post_ids=["post-a", "post-b"],
        thread_keys=["thread-a", "thread-a"],
        latest_post_created_at=_EARLIER,
    )
    assert first.snapshot_sha256 == second.snapshot_sha256
    assert first.configuration_sha256 == second.configuration_sha256
    assert first.document_count == 2
    assert first.thread_count == 1
    assert first.maximum_available_time == _EARLIER
    assert "theta" not in first.snapshot_sha256
    assert first.configuration_schema_version == "lineage-run-v1"


def test_later_cutoff_or_other_kind_does_not_reuse_the_wrong_digest() -> None:
    lineage = plan_analysis_run_capture(
        run_kind_code="analysis_run_lineage",
        scope_kind_code="analysis_scope_corporate_entity",
        corporate_entity_id="corp-1",
        knowledge_cutoff=_CUTOFF,
        idempotency_key="client-key-1",
        post_ids=["post-a"],
        thread_keys=["thread-a"],
        latest_post_created_at=_EARLIER,
    )
    later = plan_analysis_run_capture(
        run_kind_code="analysis_run_lineage",
        scope_kind_code="analysis_scope_corporate_entity",
        corporate_entity_id="corp-1",
        knowledge_cutoff=datetime(2026, 1, 13, 12, 0, tzinfo=timezone.utc),
        idempotency_key="client-key-1",
        post_ids=["post-a"],
        thread_keys=["thread-a"],
        latest_post_created_at=_EARLIER,
    )
    tepp = plan_analysis_run_capture(
        run_kind_code="analysis_run_tepp",
        scope_kind_code="analysis_scope_corporate_entity",
        corporate_entity_id="corp-1",
        knowledge_cutoff=_CUTOFF,
        idempotency_key="client-key-1",
        post_ids=["post-a"],
        thread_keys=["thread-a"],
        latest_post_created_at=_EARLIER,
    )
    assert lineage.snapshot_sha256 != later.snapshot_sha256
    assert lineage.snapshot_sha256 == tepp.snapshot_sha256
    assert lineage.configuration_sha256 != tepp.configuration_sha256
    assert tepp.configuration_schema_version == "tepp-run-v1"


def test_omitted_cutoff_keeps_the_same_client_key_stable() -> None:
    first = plan_analysis_run_capture(
        run_kind_code="analysis_run_lineage",
        scope_kind_code="analysis_scope_corporate_entity",
        corporate_entity_id="corp-1",
        knowledge_cutoff=_CUTOFF,
        idempotency_key="client-key-1",
        post_ids=["post-a"],
        thread_keys=["thread-a"],
        latest_post_created_at=_EARLIER,
        cutoff_explicit=False,
    )
    later_clock = plan_analysis_run_capture(
        run_kind_code="analysis_run_lineage",
        scope_kind_code="analysis_scope_corporate_entity",
        corporate_entity_id="corp-1",
        knowledge_cutoff=datetime(2026, 1, 13, 12, 0, tzinfo=timezone.utc),
        idempotency_key="client-key-1",
        post_ids=["post-a"],
        thread_keys=["thread-a"],
        latest_post_created_at=_EARLIER,
        cutoff_explicit=False,
    )
    assert first.configuration_sha256 == later_clock.configuration_sha256
    assert first.snapshot_sha256 == later_clock.snapshot_sha256


def test_empty_corpus_uses_the_cutoff_as_latest_available_time() -> None:
    capture = plan_analysis_run_capture(
        run_kind_code="analysis_run_lineage",
        scope_kind_code="analysis_scope_corporate_entity",
        corporate_entity_id="corp-1",
        knowledge_cutoff=_CUTOFF,
        idempotency_key="client-key-1",
        post_ids=[],
        thread_keys=[],
        latest_post_created_at=None,
    )
    assert capture.document_count == 0
    assert capture.thread_count == 0
    assert capture.maximum_available_time == _CUTOFF


def test_live_write_clock_is_distinct_from_the_cutoff_admission_clock() -> None:
    """An in-cutoff title can still have been rewritten after the run."""
    cutoff = _CUTOFF
    assert live_write_after_cutoff(_EARLIER, cutoff) is False
    assert live_write_after_cutoff(cutoff, cutoff) is False
    assert live_write_after_cutoff(
        datetime(2026, 1, 13, 9, 0, tzinfo=timezone.utc), cutoff
    ) is True
    assert live_write_after_cutoff(datetime(2026, 1, 13, 9, 0), cutoff) is True


def test_write_clock_trigger_honors_an_explicit_pin() -> None:
    """A body rewrite bumps the clock; an assigned updated_at stays."""
    sql = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "0021_source_post_write_clock.sql"
    ).read_text(encoding="utf-8")
    assert "touch_source_post_write_clock" in sql
    assert "source_post_write_clock" in sql
    assert "new.updated_at is not distinct from old.updated_at" in sql
    assert "post_title" in sql
    assert "post_body" in sql
    assert "clock_timestamp()" in sql


def test_create_rejects_an_unaffiliated_or_ambiguous_corporate_entity() -> None:
    with pytest.raises(AnalysisRunCreateError) as hidden:
        _resolve_corporate_entity_id("corp-other", ["corp-1"])
    assert hidden.value.status_code == 404
    with pytest.raises(AnalysisRunCreateError) as ambiguous:
        _resolve_corporate_entity_id(None, ["corp-1", "corp-2"])
    assert ambiguous.value.status_code == 422
    assert _resolve_corporate_entity_id(None, ["corp-1"]) == "corp-1"
