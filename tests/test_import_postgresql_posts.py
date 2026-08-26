import asyncio
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.import_postgresql_posts import (
    _lineage_grouping_values,
    _normalize_voc_type,
    _parser,
    _source_code_matches,
    _source_post_id,
    _validate_corporate_entity_scope,
    _validate_source_mapping,
    _validate_source_rows,
    import_rows,
)


def test_placeholder_grouping_is_derived_without_losing_raw_source_values() -> None:
    assert callable(_lineage_grouping_values)
    mapping = SimpleNamespace(
        thread_group="thread",
        secondary_group="document",
        project_code="project",
    )

    assert _lineage_grouping_values(
        {"thread": " record-1 ", "document": " document-1 ", "project": " project-1 "},
        mapping,
        record_key="record-1",
        default_group="pu-1",
    ) == ("record-1", "document-1", "", "project-1")


def test_real_source_grouping_remains_the_derived_grouping() -> None:
    assert callable(_lineage_grouping_values)
    mapping = SimpleNamespace(
        thread_group="thread",
        secondary_group="secondary",
        project_code="project",
    )

    assert _lineage_grouping_values(
        {"thread": "thread-a", "secondary": "secondary-a", "project": "project-a"},
        mapping,
        record_key="record-1",
        default_group="pu-1",
    ) == ("thread-a", "secondary-a", "thread-a", "secondary-a")


def test_import_rows_persists_raw_and_derived_grouping_values(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """One synthetic import carries provenance and reconstruction fields together."""
    query_file = tmp_path / "synthetic-query.sql"
    query_file.write_text("select synthetic_source", encoding="utf-8")
    row = {
        "record_key": "record-1",
        "title": "Synthetic lineage follow-up",
        "body": "Synthetic customer-safe evidence body.",
        "created_at": datetime(2026, 1, 2, tzinfo=UTC),
        "draft_state": "published",
        "thread": "record-1",
        "secondary": "document-1",
        "project": "project-1",
    }

    class FakeConnection:
        def __init__(self, *, source: bool) -> None:
            self.source = source
            self.executions: list[tuple[str, tuple[object, ...]]] = []
            self.closed = False

        async def fetch(self, _query: str):
            assert self.source
            return [row]

        async def execute(self, query: str, *args: object):
            self.executions.append((query, args))

        async def close(self) -> None:
            self.closed = True

    source = FakeConnection(source=True)
    target = FakeConnection(source=False)
    connections = iter((source, target))

    async def fake_connect(_dsn: str):
        return next(connections)

    async def fake_scope(_conn, _args):
        return "account-1", "corporate-1", "process-unit-1"

    async def no_content(*_args, **_kwargs) -> None:
        return None

    async def no_cleanup(*_args, **_kwargs) -> dict[str, int]:
        return {"synthetic_rows_removed": 0}

    async def no_edges(_conn, *, llm=None) -> list[object]:
        return []

    monkeypatch.setattr("scripts.import_postgresql_posts.asyncpg.connect", fake_connect)
    monkeypatch.setattr("scripts.import_postgresql_posts._ensure_scope", fake_scope)
    monkeypatch.setattr("scripts.import_postgresql_posts.persist_post_content", no_content)
    monkeypatch.setattr("scripts.import_postgresql_posts.cleanup_synthetic_seed", no_cleanup)
    monkeypatch.setattr("scripts.import_postgresql_posts.rebuild_lineage", no_edges)
    monkeypatch.setattr(
        "scripts.import_postgresql_posts.orchestrator_vision_client",
        lambda *_args: object(),
    )
    monkeypatch.setattr(
        "scripts.import_postgresql_posts.orchestrator_embedding_client",
        lambda *_args: object(),
    )

    args = _parser().parse_args(
        [
            "--source-dsn",
            "postgresql://synthetic-source",
            "--target-dsn",
            "postgresql://synthetic-target",
            "--query-file",
            str(query_file),
            "--source-system-code",
            "synthetic-source",
            "--record-key-column",
            "record_key",
            "--title-column",
            "title",
            "--body-column",
            "body",
            "--created-at-column",
            "created_at",
            "--draft-column",
            "draft_state",
            "--exclude-draft-value",
            "draft",
            "--thread-group-column",
            "thread",
            "--secondary-group-column",
            "secondary",
            "--source-project-code-column",
            "project",
            "--author-subject-id",
            "synthetic-subject",
            "--corporate-entity-code",
            "SYNTHETIC-CORP",
            "--process-unit-code",
            "synthetic-pu",
        ]
    )

    result = asyncio.run(import_rows(args))

    source_post_args = next(
        call_args
        for query, call_args in target.executions
        if "insert into source_post\n" in query
    )
    assert source_post_args[26:30] == (
        "record-1",
        "document-1",
        "",
        "project-1",
    )
    assert source_post_args[-1] is None
    assert result == {
        "source_rows": 1,
        "imported_rows": 1,
        "skipped_rows": 0,
        "lineage_edges": 0,
        "synthetic_rows_removed": 0,
    }
    assert source.closed and target.closed


@pytest.mark.parametrize(
    ("source_value", "expected"),
    [("VOC", "voc"), ("VOCC", "vocc"), ("VOCO", "voco"), ("VOM", "vom"), ("VOP", "vop")],
)
def test_importer_preserves_source_voc_type_vocabulary(source_value: str, expected: str) -> None:
    assert _normalize_voc_type(source_value, mapped=True) == expected


def test_importer_rejects_unknown_or_empty_mapped_voc_type() -> None:
    with pytest.raises(ValueError, match="unsupported source VOC type"):
        _normalize_voc_type("not-a-voc-type", mapped=True)
    with pytest.raises(ValueError, match="mapped source VOC type is empty"):
        _normalize_voc_type("", mapped=True)


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


def test_importer_accepts_explicitly_evidenced_missing_body_dimension() -> None:
    mapping = SimpleNamespace(
        record_key="record_key", body=None, draft="draft_state", deleted=None
    )
    evidence = (
        "aggregate source inspection found no non-empty body values while "
        "titles and structured dimensions remained populated"
    )

    _validate_source_rows(
        [{"record_key": "one", "draft_state": "published"}],
        mapping,
        ["draft"],
        [],
        "",
        evidence,
    )

    with pytest.raises(ValueError, match="at least 40 characters"):
        _validate_source_rows(
            [{"record_key": "one", "draft_state": "published"}],
            mapping,
            ["draft"],
            [],
            "",
            "no body",
        )


def test_importer_requires_exactly_one_body_evidence_door() -> None:
    with pytest.raises(SystemExit):
        _parser().parse_args(
            [
                "--source-dsn", "postgresql://source",
                "--target-dsn", "postgresql://target",
                "--query-file", "query.sql",
                "--source-system-code", "source",
                "--record-key-column", "record_key",
                "--title-column", "title",
                "--body-column", "body",
                "--no-body-dimension-evidence", "body is absent from this source export",
                "--created-at-column", "created_at",
                "--author-subject-id", "subject",
                "--corporate-entity-code", "corp",
                "--process-unit-code", "pu",
            ]
        )

def test_importer_keeps_source_record_key_separate_from_source_uuid() -> None:
    mapping = SimpleNamespace(post_id="synthetic_post_id")
    source_uuid = "01234567-89ab-cdef-0123-456789abcdef"

    assert _source_post_id(
        {"synthetic_post_id": source_uuid}, mapping, "source", "human-entered-source-key"
    ) == uuid.UUID(source_uuid)


def test_importer_derives_legacy_post_uuid_without_a_post_id_mapping() -> None:
    mapping = SimpleNamespace(post_id=None)

    assert _source_post_id(
        {}, mapping, "source", "human-entered-source-key"
    ) == uuid.uuid5(uuid.UUID("b6e4b1d6-5fd0-4ca1-92b0-8f7a4e2df83e"), "source:human-entered-source-key")


def test_importer_rejects_duplicate_active_source_identity() -> None:
    mapping = SimpleNamespace(record_key="record_key", body="body", draft="draft_state", deleted=None)

    with pytest.raises(ValueError, match="duplicate source record key at source rows 1 and 2"):
        _validate_source_rows(
            [
                {"record_key": "same", "body": "first", "draft_state": "N"},
                {"record_key": "same", "body": "second", "draft_state": "N"},
            ],
            mapping,
            ["Y"],
            [],
        )


def test_importer_allows_repeated_lookup_keys_when_source_uuids_are_distinct() -> None:
    mapping = SimpleNamespace(
        record_key="record_key",
        post_id="post_id",
        body="body",
        draft="draft_state",
        deleted=None,
    )

    _validate_source_rows(
        [
            {
                "record_key": "same",
                "post_id": "01234567-89ab-cdef-0123-456789abcdef",
                "body": "first",
                "draft_state": "N",
            },
            {
                "record_key": "same",
                "post_id": "11234567-89ab-cdef-0123-456789abcdef",
                "body": "second",
                "draft_state": "N",
            },
        ],
        mapping,
        ["Y"],
        [],
    )


def test_source_record_key_index_is_a_lookup_not_a_uniqueness_constraint() -> None:
    migration = (
        Path(__file__).resolve().parents[1] / "migrations" / "0037_source_record_identity.sql"
    ).read_text()
    assert "create unique index" not in migration.casefold()
    assert "create index if not exists source_post_source_identity_idx" in migration


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


def test_no_draft_dimension_evidence_is_an_explicit_audited_door() -> None:
    """An export with no authorship-draft dimension passes only with the
    operator's written evidence; the note cannot be a placeholder and
    cannot be combined with a mapped draft column.
    """
    no_draft_mapping = SimpleNamespace(
        record_key="record_key", body="body", draft=None, deleted=None
    )
    evidence = (
        "every candidate draft column is NULL across the export and the "
        "prior full-corpus pipeline treated every lifecycle stage as a "
        "real document"
    )
    _validate_source_rows(
        [{"record_key": "one", "body": "body"}],
        no_draft_mapping,
        [],
        [],
        evidence,
    )

    with pytest.raises(ValueError, match="at least 40 characters"):
        _validate_source_rows(
            [{"record_key": "one", "body": "body"}],
            no_draft_mapping,
            [],
            [],
            "no drafts",
        )

    draft_mapping = SimpleNamespace(
        record_key="record_key", body="body", draft="draft_state", deleted=None
    )
    with pytest.raises(ValueError, match="pick one publication-state door"):
        _validate_source_rows(
            [{"record_key": "one", "body": "body", "draft_state": "N"}],
            draft_mapping,
            ["Y"],
            [],
            evidence,
        )


def test_importer_rejects_demo_scope_without_explicit_test_override() -> None:
    with pytest.raises(ValueError, match="non-DEMO corporate entity code"):
        _validate_corporate_entity_scope("DEMO-CORP-01", allow_demo=False)
    _validate_corporate_entity_scope("DEMO-CORP-01", allow_demo=True)


def test_importer_does_not_select_a_provider_embedding_model(monkeypatch) -> None:
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

    assert not hasattr(args, "embedding_model")


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
