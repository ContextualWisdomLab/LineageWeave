"""Unit tests for source_post → Record mapping used by lineage rebuild."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.lineage_ingestion import records_from_source_posts


def test_records_use_process_unit_as_group_when_present() -> None:
    rows = [
        {
            "post_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "process_unit_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "corporate_entity_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "post_title": "Unit A post",
            "voc_type_code": "voc",
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }
    ]
    records = records_from_source_posts(rows)
    assert records[0].group_key == "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    assert records[0].secondary_key == "voc"
    assert records[0].occurred_at.tzinfo is None


def test_records_fall_back_to_corporate_entity_without_a_process_unit() -> None:
    rows = [
        {
            "post_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "process_unit_id": None,
            "corporate_entity_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "post_title": "Corp-only post",
            "voc_type_code": "vom",
            "created_at": datetime(2026, 2, 1),
        }
    ]
    records = records_from_source_posts(rows)
    assert records[0].group_key == "cccccccc-cccc-cccc-cccc-cccccccccccc"
    assert records[0].secondary_key == "vom"
    assert records[0].label == "Corp-only post"
