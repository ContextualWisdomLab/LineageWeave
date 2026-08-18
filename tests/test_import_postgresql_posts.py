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


def test_importer_accepts_explicit_source_name_mappings() -> None:
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
            "--source-sales-pool-name-column", "sales_pool_name",
            "--source-customer-name-column", "customer_name",
            "--source-project-name-column", "project_name",
        ]
    )

    assert args.source_sales_pool_name_column == "sales_pool_name"
    assert args.source_customer_name_column == "customer_name"
    assert args.source_project_name_column == "project_name"
