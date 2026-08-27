import asyncio
from datetime import UTC, datetime

from backend.app.main import _load_post_voice_types, _serialize_post


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
            "source_author_code": "author-1",
            "source_author_name": "Source Author",
            "source_company_code": "COMPANY-1",
            "source_process_unit_code": "PU-1",
            "source_sales_pool_code": "POOL-1",
            "source_customer_code": "CUSTOMER-1",
            "source_project_code": "PROJECT-1",
            "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        },
        {"voc": "Voice of Customer", "public": "Public"},
    )

    assert payload["source_stage_code"] == "Z"
    assert payload["source_detail_state_code"] == "A"
    assert payload["source_draft_code"] is None
    assert payload["source_deleted_flag"] is None
    assert payload["publication_state_code"] == "publication_state_unknown"
    assert payload["source_author_code"] == "author-1"
    assert payload["source_customer_code"] == "CUSTOMER-1"
    assert payload["source_project_code"] == "PROJECT-1"


def test_voice_combinations_are_serialized_without_internal_assertion_ids() -> None:
    """A post exposes qualified voice evidence state, not provenance primary keys."""
    voice_types = [
        {
            "code": "voc",
            "label": "Voice of Customer",
            "is_primary": True,
            "truth_status_code": "truth_observed",
            "evidence_available": False,
        },
        {
            "code": "vops",
            "label": "Voice of Process",
            "is_primary": False,
            "truth_status_code": "truth_observed",
            "evidence_available": True,
        },
    ]
    payload = _serialize_post(
        {
            "post_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "post_title": "Synthetic combined signal",
            "voc_type_code": "voc",
            "visibility_code": "public",
            "voice_types": voice_types,
            "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        }
    )

    assert payload["voice_types"] == voice_types
    assert all("provenance_assertion_id" not in voice for voice in payload["voice_types"])


def test_voice_loader_projects_evidence_availability_not_assertion_ids() -> None:
    """The read boundary returns a boolean evidence cue and keeps internal ids private."""

    class Connection:
        async def fetch(
            self, query: str, post_id: str, effective_cutoff: datetime
        ) -> list[dict[str, object]]:
            assert "provenance_assertion_id is not null as evidence_available" in query
            assert "voice.effective_from <= $2" in query
            assert "voice.effective_to is null or $2 < voice.effective_to" in query
            assert post_id == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
            assert effective_cutoff == datetime(2026, 1, 1, tzinfo=UTC)
            return [
                {
                    "voice_type_code": "vops",
                    "lookup_label": "Voice of Process",
                    "is_primary": False,
                    "truth_status_code": "truth_observed",
                    "evidence_available": True,
                }
            ]

    rows = asyncio.run(
        _load_post_voice_types(  # type: ignore[arg-type]
            Connection(),
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            datetime(2026, 1, 1, tzinfo=UTC),
        )
    )

    assert rows == [
        {
            "code": "vops",
            "label": "Voice of Process",
            "is_primary": False,
            "truth_status_code": "truth_observed",
            "evidence_available": True,
        }
    ]
