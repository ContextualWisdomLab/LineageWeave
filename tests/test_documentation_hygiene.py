"""Permanent hygiene checks for committed architecture-decision records."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_ADR_DIRECTORY = _ROOT / "docs" / "adr"
_ROLE_CATALOG_COLUMNS = (
    "cataloged_team_id",
    "cataloged_corporate_entity_id",
    "cataloged_person_id",
)
_ADR_NAME = re.compile(r"^(?P<number>[0-9]{4})-.+\.md$")
_FORBIDDEN_MARKERS = (
    "PLACEHOLDER_DO_NOT_WRITE",
    "TODO_WRITE_ADR",
)


def test_adr_numbers_are_unique_and_documents_are_not_placeholders() -> None:
    """Every committed ADR number identifies one substantive UTF-8 document."""
    paths = sorted(_ADR_DIRECTORY.glob("*.md"))
    assert paths, "the repository must contain architecture-decision records"

    numbered_paths: list[tuple[str, Path]] = []
    for path in paths:
        match = _ADR_NAME.fullmatch(path.name)
        assert match is not None, f"ADR filename is not numbered: {path.name}"
        numbered_paths.append((match.group("number"), path))

        content = path.read_text(encoding="utf-8")
        assert content.strip(), f"ADR is empty: {path.relative_to(_ROOT)}"
        for marker in _FORBIDDEN_MARKERS:
            assert marker not in content, (
                f"ADR contains forbidden placeholder {marker!r}: "
                f"{path.relative_to(_ROOT)}"
            )

    counts = Counter(number for number, _ in numbered_paths)
    duplicates = sorted(number for number, count in counts.items() if count > 1)
    assert duplicates == [], f"duplicate ADR numbers: {duplicates}"


def test_fetch_persisted_summary_reads_stored_catalog_ids() -> None:
    """ADR 0019: fetch must not rejoin the catalog by a non-unique name."""

    source = (_ROOT / "backend" / "app" / "post_summary_ingestion.py").read_text(
        encoding="utf-8"
    )
    assert "org.entity_name = role.actor_name" not in source
    assert "role.cataloged_team_id" in source
    assert "role.cataloged_corporate_entity_id" in source
    assert "role.cataloged_person_id" in source
    assert "order by created_at, person_id limit 1" in source
    assert "where person_name = $1 limit 1" not in source


def test_role_catalog_identity_migration_is_wired() -> None:
    """Fresh stacks and seed must apply the catalog-identity columns."""

    dockerfile = (_ROOT / "docker" / "postgres-init" / "Dockerfile").read_text(
        encoding="utf-8"
    )
    seed = (_ROOT / "scripts" / "seed_demo_data.py").read_text(encoding="utf-8")
    migration_0019 = (_ROOT / "migrations" / "0019_role_catalog_identity.sql").read_text(
        encoding="utf-8"
    )
    migration_0023 = (
        _ROOT / "migrations" / "0023_role_person_catalog_identity.sql"
    ).read_text(encoding="utf-8")
    initial = (_ROOT / "migrations" / "0001_initial_schema.sql").read_text(
        encoding="utf-8"
    )
    assert "0019_role_catalog_identity.sql" in dockerfile
    assert "0023_role_person_catalog_identity.sql" in dockerfile
    assert "0019_role_catalog_identity.sql" in seed
    assert "0023_role_person_catalog_identity.sql" in seed
    assert seed.index("0022_analysis_source_snapshot_member.sql") < seed.index(
        "0023_role_person_catalog_identity.sql"
    )
    assert "cataloged_team_id" in migration_0019
    assert "cataloged_corporate_entity_id" in migration_0019
    assert "cataloged_person_id" in migration_0023
    assert "cataloged_person_id" in initial
    for column_name in _ROLE_CATALOG_COLUMNS:
        assert len(column_name.split("_")) >= 2
    assert "having count(*) = 1" in migration_0019
    assert "having count(*) = 1" in migration_0023
    assert "distinct on" not in migration_0019.lower()
    assert "distinct on" not in migration_0023.lower()
