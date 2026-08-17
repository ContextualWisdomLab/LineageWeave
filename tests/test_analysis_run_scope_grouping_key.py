"""Report-open grouping keys stay on the authorized scope, never a week or theta."""

from backend.app.analysis_run_ingestion import scope_grouping_key


def test_corporate_scope_persists_entity_id_not_the_week_key() -> None:
    assert (
        scope_grouping_key(
            {
                "scope_kind_code": "analysis_scope_corporate_entity",
                "corporate_entity_id": "corp-1",
                "process_unit_id": None,
                "scope_key": "2026-W02",
            }
        )
        == "corp-1"
    )


def test_process_unit_and_thread_scopes_keep_their_grouping_keys() -> None:
    assert (
        scope_grouping_key(
            {
                "scope_kind_code": "analysis_scope_process_unit",
                "corporate_entity_id": "corp-1",
                "process_unit_id": "pu-high",
                "scope_key": None,
            }
        )
        == "pu-high"
    )
    assert (
        scope_grouping_key(
            {
                "scope_kind_code": "analysis_scope_thread_group",
                "corporate_entity_id": None,
                "process_unit_id": None,
                "scope_key": "A-100",
            }
        )
        == "A-100"
    )


def test_scope_grouping_key_is_never_a_theta() -> None:
    key = scope_grouping_key(
        {
            "scope_kind_code": "analysis_scope_corporate_entity",
            "corporate_entity_id": "corp-1",
            "process_unit_id": None,
            "scope_key": "2026-W02",
        }
    )
    assert key is not None
    assert "theta" not in key.lower()
    assert "θ" not in key
