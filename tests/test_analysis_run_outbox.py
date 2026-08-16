"""Lineage outbox reconstructs the designed fork and never invents a theta."""

from __future__ import annotations

import inspect
from pathlib import Path

from backend.app.analysis_run_outbox import (
    DELIVERY_QUEUED,
    LINEAGE_DELIVERY_KIND,
    enqueue_lineage_delivery,
)
from backend.app.analysis_run_worker import (
    LINEAGE_RUN_KIND,
    reconstruct_cutoff_edges,
)
from backend.app.lineage_ingestion import persist_lineage_edges, persist_run_lineage_edges
from lineageweave.fixtures import sample_records
from lineageweave.reconstruct import reconstruct


_ROOT = Path(__file__).resolve().parents[1]
_OUTBOX_MIGRATION = _ROOT / "migrations" / "0019_analysis_run_outbox.sql"
_OUTBOX_ROLLBACK = _ROOT / "migrations" / "rollback" / "0019_analysis_run_outbox.sql"
_POSTGRES_IMAGE = _ROOT / "docker" / "postgres-init" / "Dockerfile"


def test_cutoff_reconstruction_recovers_the_designed_a100_fork() -> None:
    """True structure: rec-002 must keep both the quote and the delivery child."""
    records = sample_records()
    trees = reconstruct(records)
    tree_a = next(tree for tree in trees if tree.group_key == "A-100")
    edges = reconstruct_cutoff_edges(records)
    children = {
        edge.child_id
        for edge in edges
        if edge.parent_id == "rec-002"
    }

    assert "rec-002" in tree_a.branch_points()
    assert children >= {"rec-003", "rec-004"}
    assert "rec-006" in tree_a.roots
    assert all(0.0 <= edge.fused_score <= 1.0 for edge in edges)
    assert all("theta" not in edge.parent_id for edge in edges)
    assert LINEAGE_RUN_KIND == "analysis_run_lineage"


def test_run_scoped_persist_does_not_wipe_live_lineage_edges() -> None:
    """The worker must not call the global rebuild delete."""
    run_scoped = inspect.getsource(persist_run_lineage_edges)
    live = inspect.getsource(persist_lineage_edges)
    assert "analysis_run_lineage_edge" in run_scoped
    assert "delete from post_lineage_edge" not in run_scoped
    assert "delete from post_lineage_edge" in live


def test_enqueue_is_lineage_only_and_replay_safe() -> None:
    """A second insert of the same run must not open another delivery."""
    source = inspect.getsource(enqueue_lineage_delivery)
    assert LINEAGE_DELIVERY_KIND in source
    assert DELIVERY_QUEUED in source
    assert "on conflict (analysis_run_id) do nothing" in source


def test_outbox_migration_keeps_two_word_names_and_no_theta() -> None:
    """0019 is 3NF lease + edge facts; no post body, DSN, or measurement."""
    migration = _OUTBOX_MIGRATION.read_text(encoding="utf-8")
    rollback = _OUTBOX_ROLLBACK.read_text(encoding="utf-8")
    dockerfile = _POSTGRES_IMAGE.read_text(encoding="utf-8")
    assert "create table if not exists analysis_run_outbox" in migration
    assert "create table if not exists analysis_run_lineage_edge" in migration
    assert "jsonb" not in migration.casefold()
    assert "theta" not in migration.casefold()
    assert "postgresql://" not in migration
    assert "analysis_run_outbox_not_empty" in rollback
    assert "0019_analysis_run_outbox.sql" in dockerfile
