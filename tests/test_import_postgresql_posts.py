from types import SimpleNamespace

import pytest

from scripts.import_postgresql_posts import (
    _parser,
    _source_code_matches,
    _validate_source_mapping,
    _validate_source_rows,
)


def test_source_state_exclusion_uses_only_explicit_caller_values() -> None:
    row = {"draft_state": " Temporary ", "deleted_state": "N"}

    assert _source_code_matches(row, "draft_state", ["temporary"])
    assert not _source_code_matches(row, "draft_state", ["draft"])
    assert not _source_code_matches(row, "deleted_state", ["Y"])


def test_source_state_exclusion_does_not_guess_when_mapping_is_absent() -> None:
    row = {"draft_state": "draft", "deleted_state": "Y"}

    assert not _source_code_matches(row, None, ["draft"])
    assert not _source_code_matches(row, "draft_state", [])


def test_importer_rejects_mapping_the_pu_column_as_sales_pool() -> None:
    with pytest.raises(ValueError, match="PU is source_process_unit_code"):
        _validate_source_mapping("pu_code", "pu_code")


def test_importer_preflights_identity_and_body_before_target_mutation() -> None:
    mapping = SimpleNamespace(record_key="record_key", body="body", draft="draft_state", deleted=None)

    with pytest.raises(ValueError, match="source record key cannot be empty at source row 2"):
        _validate_source_rows(
            [
                {"record_key": "one", "body": "body", "draft_state": "N"},
                {"record_key": "", "body": "body", "draft_state": "N"},
            ],
            mapping,
            ["Y"],
            [],
        )

    with pytest.raises(ValueError, match="source post body cannot be empty at source row 1"):
        _validate_source_rows(
            [{"record_key": "one", "body": "", "draft_state": "N"}], mapping, ["Y"], []
        )


def test_importer_always_requires_verified_publication_state() -> None:
    mapping = SimpleNamespace(record_key="record_key", body="body", draft="draft_state", deleted=None)

    with pytest.raises(ValueError, match="at least one source draft value"):
        _validate_source_rows(
            [{"record_key": "one", "body": "body", "draft_state": "N"}],
            mapping,
            [],
            [],
        )

    with pytest.raises(ValueError, match="publication state is unknown"):
        _validate_source_rows(
            [{"record_key": "one", "body": "body", "draft_state": None}],
            mapping,
            ["Y"],
            [],
        )


def test_importer_has_no_unknown_publication_state_bypass() -> None:
    with pytest.raises(SystemExit):
        _parser().parse_args(["--allow-unknown-publication-state"])


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
            "--source-company-name-column", "company_name",
            "--source-process-unit-name-column", "process_unit_name",
        ]
    )

    assert args.source_sales_pool_name_column == "sales_pool_name"
    assert args.source_customer_name_column == "customer_name"
    assert args.source_project_name_column == "project_name"
    assert args.source_company_name_column == "company_name"
    assert args.source_business_unit_name_column == "process_unit_name"
