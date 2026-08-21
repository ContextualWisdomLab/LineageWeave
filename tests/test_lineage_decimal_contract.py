"""Static schema contract for exact bounded lineage evidence numerics."""

from pathlib import Path


def test_lineage_evidence_uses_fixed_precision_decimals() -> None:
    migration = Path("migrations/0055_lineage_edge_channel_score.sql").read_text(
        encoding="utf-8"
    )
    rollback = Path(
        "migrations/rollback/0055_lineage_edge_channel_score.sql"
    ).read_text(encoding="utf-8")

    assert "channel_weight numeric(18, 12) not null" in migration
    assert "channel_score numeric(18, 12) not null" in migration
    assert "channel_contribution numeric(18, 12) not null" in migration
    assert "new.channel_score * active_weight" in migration
    assert "new.channel_contribution > active_weight" in migration
    assert "validate_lineage_edge_channel_contribution" in migration
    assert "lineage_edge_channel_contribution_validate" in migration
    assert "do update set" in migration
    assert "display_order = excluded.display_order" in migration
    assert "to_regclass('public.lineage_edge_channel_score')" in rollback
    assert "drop trigger if exists" in rollback
    assert "lineage_edge_channel_contribution_validate" in rollback
    assert "drop function if exists validate_lineage_edge_channel_contribution" in rollback
