"""Seeded Succeeded lineage runs persist the designed A-100 fork."""

from datetime import datetime, timezone

from lineageweave.fixtures import sample_records
from scripts.seed_demo_data import seed_reconstruction_edges

# Synthetic unit-test fusion weights (org policy allows synthetic data in
# unit tests). ``make seed`` never activates them; it omits reconstruction
# until fitted, independently anchored owner evidence exists (ADR 0205).
_SYNTHETIC_WEIGHTS = {"temporal": 0.5, "secondary_key": 0.34, "text": 0.16}


def _rows_from_fixtures() -> list[dict]:
    cutoff = datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc)
    rows: list[dict] = []
    for record in sample_records():
        occurred = record.occurred_at.replace(tzinfo=timezone.utc)
        if occurred > cutoff:
            continue
        rows.append(
            {
                "post_id": record.record_id,
                "post_title": record.label,
                "created_at": occurred,
                "visibility_code": "public",
                "corporate_entity_id": "demo-corp",
                "process_unit_id": "demo-pu",
                "thread_group_key": record.group_key,
                "secondary_grouping_key": record.secondary_key,
            }
        )
    return rows


def test_seed_reconstruction_recovers_the_a100_fork() -> None:
    """Seed must persist the same parent choices start uses."""
    edges, digest = seed_reconstruction_edges(_rows_from_fixtures(), _SYNTHETIC_WEIGHTS)
    children = {edge.child_id for edge in edges if edge.parent_id == "rec-002"}
    assert children >= {"rec-003", "rec-004"}
    assert "rec-006" not in {edge.child_id for edge in edges}
    assert digest
    assert "theta" not in digest
