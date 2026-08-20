"""Static schema contract for exact bounded lineage evidence numerics."""

from pathlib import Path


def test_lineage_evidence_uses_fixed_precision_decimals() -> None:
    migration = Path("migrations/0053_lineage_edge_channel_score.sql").read_text(
        encoding="utf-8"
    )

    assert "channel_weight numeric(18, 12) not null" in migration
    assert "channel_score numeric(18, 12) not null" in migration
    assert "channel_contribution numeric(18, 12) not null" in migration
    assert "channel_contribution <= channel_weight" in migration
    assert "do update set" in migration
    assert "display_order = excluded.display_order" in migration
