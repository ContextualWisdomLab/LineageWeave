from scripts.import_postgresql_posts import _parser, _source_code_matches


def test_source_state_exclusion_uses_only_explicit_caller_values() -> None:
    row = {"draft_state": " Temporary ", "deleted_state": "N"}

    assert _source_code_matches(row, "draft_state", ["temporary"])
    assert not _source_code_matches(row, "draft_state", ["draft"])
    assert not _source_code_matches(row, "deleted_state", ["Y"])


def test_source_state_exclusion_does_not_guess_when_mapping_is_absent() -> None:
    row = {"draft_state": "draft", "deleted_state": "Y"}

    assert not _source_code_matches(row, None, ["draft"])
    assert not _source_code_matches(row, "draft_state", [])


def test_importer_prefers_canonical_gateway_embedding_model(monkeypatch) -> None:
    monkeypatch.setenv("LLM_GATEWAY_EMBEDDING_MODEL", "gateway-embedding")
    monkeypatch.setenv("EMBEDDING_MODEL", "legacy-embedding")

    args = _parser().parse_args(
        [
            "--source-dsn", "postgresql://source",
            "--target-dsn", "postgresql://target",
            "--query-file", "query.sql",
            "--source-system-code", "source",
            "--record-key-column", "record_key",
            "--title-column", "title",
            "--body-column", "body",
            "--created-at-column", "created_at",
            "--author-subject-id", "subject",
            "--corporate-entity-code", "corp",
            "--process-unit-code", "pu",
        ]
    )

    assert args.embedding_model == "gateway-embedding"
