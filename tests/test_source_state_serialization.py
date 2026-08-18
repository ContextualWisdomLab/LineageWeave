from datetime import datetime, timezone

from backend.app.main import _serialize_post


def test_source_state_codes_are_serialized_without_inference() -> None:
    payload = _serialize_post(
        {
            "post_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "post_title": "Source-backed post",
            "voc_type_code": "voc",
            "visibility_code": "public",
            "source_stage_code": "Z",
            "source_detail_state_code": "A",
            "source_draft_code": None,
            "source_deleted_flag": None,
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        },
        {"voc": "Voice of Customer", "public": "Public"},
    )

    assert payload["source_stage_code"] == "Z"
    assert payload["source_detail_state_code"] == "A"
    assert payload["source_draft_code"] is None
    assert payload["source_deleted_flag"] is None
