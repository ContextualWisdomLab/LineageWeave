from scripts.import_postgresql_posts import _source_code_matches


def test_source_state_exclusion_uses_only_explicit_caller_values() -> None:
    row = {"draft_state": " Temporary ", "deleted_state": "N"}

    assert _source_code_matches(row, "draft_state", ["temporary"])
    assert not _source_code_matches(row, "draft_state", ["draft"])
    assert not _source_code_matches(row, "deleted_state", ["Y"])


def test_source_state_exclusion_does_not_guess_when_mapping_is_absent() -> None:
    row = {"draft_state": "draft", "deleted_state": "Y"}

    assert not _source_code_matches(row, None, ["draft"])
    assert not _source_code_matches(row, "draft_state", [])
