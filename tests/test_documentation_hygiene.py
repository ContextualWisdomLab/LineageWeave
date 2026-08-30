"""Permanent hygiene checks for committed architecture-decision records."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_ADR_DIRECTORY = _ROOT / "docs" / "adr"
_PRODUCT_GAP_BASELINE = _ROOT / "docs" / "product-technical-gap-baseline.md"
_PRODUCT_REQUIREMENTS = _ROOT / "docs" / "product-requirements.md"
_ROLE_CATALOG_COLUMNS = (
    "cataloged_team_id",
    "cataloged_corporate_entity_id",
    "cataloged_person_id",
)
_ADR_NAME = re.compile(r"^(?P<number>[0-9]{4})-.+\.md$")
_PRD_REQUIREMENT_HEADING = re.compile(r"^### (?P<identifier>PRD-FR-[0-9A-Z-]+)\b", re.MULTILINE)
_PRD_ADR_CLAUSE = re.compile(r"\bADRs?\s+(?P<references>[^.;)]*)")
_ADR_NUMBER_OR_RANGE = re.compile(
    r"(?P<start>[0-9]{4})(?:\s*[–-]\s*(?P<end>[0-9]{4}))?"
)
_PRIVATE_POST_IDENTIFIER = re.compile(
    r"(?i)"
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
    r"|\bpost(?:_id)?\s*(?:=|:)\s*[`'\"]?[a-z0-9][a-z0-9-]{5,}"
    r"|\bpost\s+[`'\"]?(?:[0-9][a-z0-9-]{5,}|[a-f][a-f0-9-]{7,})\b"
)
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
        if path.name == "README.md":
            continue
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


def test_product_gap_baseline_contains_no_private_post_identifiers() -> None:
    """Buyer-gap evidence stays aggregate and cannot identify private runtime posts."""
    baseline = _PRODUCT_GAP_BASELINE.read_text(encoding="utf-8")

    for private_reference in (
        "post=synthetic-12345",
        "post: synthetic-12345",
        "post 12345678",
        "00000000-0000-4000-8000-000000000000",
    ):
        assert _PRIVATE_POST_IDENTIFIER.search(private_reference)
    assert _PRIVATE_POST_IDENTIFIER.search("authorized post evidence remains aggregate") is None

    match = _PRIVATE_POST_IDENTIFIER.search(baseline)
    assert match is None, f"private post identifier in product-gap baseline: {match.group(0)!r}"


def test_product_requirement_identifiers_are_unique() -> None:
    """Each PRD identifier names one current requirement and acceptance contract."""
    product_requirements = _PRODUCT_REQUIREMENTS.read_text(encoding="utf-8")
    identifiers = _PRD_REQUIREMENT_HEADING.findall(product_requirements)

    assert identifiers, "the product requirements must contain numbered requirements"
    counts = Counter(identifiers)
    duplicates = sorted(identifier for identifier, count in counts.items() if count > 1)
    assert duplicates == [], f"duplicate PRD requirement identifiers: {duplicates}"


def test_product_requirement_adr_references_exist() -> None:
    """Direct ADR references in the supporting PRD resolve to normative records."""
    product_requirements = _PRODUCT_REQUIREMENTS.read_text(encoding="utf-8")
    referenced_numbers: set[str] = set()
    for clause in _PRD_ADR_CLAUSE.finditer(product_requirements):
        for reference in _ADR_NUMBER_OR_RANGE.finditer(clause.group("references")):
            start = int(reference.group("start"))
            end = int(reference.group("end") or start)
            referenced_numbers.update(f"{number:04d}" for number in range(start, end + 1))

    assert {"0249", "0250", "0253", "0255"} <= referenced_numbers
    available_numbers = {
        match.group("number")
        for path in _ADR_DIRECTORY.glob("*.md")
        if (match := _ADR_NAME.fullmatch(path.name)) is not None
    }

    missing = sorted(referenced_numbers - available_numbers)
    assert missing == [], f"PRD references missing ADRs: {missing}"


def test_adr_product_requirement_references_exist() -> None:
    """Accepted ADR traceability cannot point at a removed PRD requirement."""
    product_requirements = _PRODUCT_REQUIREMENTS.read_text(encoding="utf-8")
    available_identifiers = set(_PRD_REQUIREMENT_HEADING.findall(product_requirements))
    referenced_identifiers: set[str] = set()
    for path in _ADR_DIRECTORY.glob("*.md"):
        referenced_identifiers.update(
            re.findall(r"\bPRD-FR-[0-9A-Z-]+\b", path.read_text(encoding="utf-8"))
        )

    missing = sorted(referenced_identifiers - available_identifiers)
    assert missing == [], f"ADRs reference missing PRD requirements: {missing}"


def test_fetch_persisted_summary_reads_stored_catalog_ids() -> None:
    """ADR 0019 / 0027: fetch must not rejoin the catalog by a non-unique name."""

    source = (_ROOT / "backend" / "app" / "post_summary_ingestion.py").read_text(
        encoding="utf-8"
    )
    assert "org.entity_name = role.actor_name" not in source
    assert "role.cataloged_team_id" in source
    assert "role.cataloged_corporate_entity_id" in source
    assert "role.cataloged_person_id" in source
    assert "order by created_at, person_id limit 1" in source


def test_role_catalog_identity_migration_is_wired() -> None:
    """Fresh stacks and seed must apply the catalog-identity columns."""

    dockerfile = (_ROOT / "docker" / "postgres-init" / "Dockerfile").read_text(
        encoding="utf-8"
    )
    seed = (_ROOT / "scripts" / "seed_demo_data.py").read_text(encoding="utf-8")
    migration_0019 = (_ROOT / "migrations" / "0019_role_catalog_identity.sql").read_text(
        encoding="utf-8"
    )
    migration_0025 = (
        _ROOT / "migrations" / "0025_role_person_catalog_identity.sql"
    ).read_text(encoding="utf-8")
    assert "0019_role_catalog_identity.sql" in dockerfile
    assert "0025_role_person_catalog_identity.sql" in dockerfile
    assert "0019_role_catalog_identity.sql" in seed
    assert "0025_role_person_catalog_identity.sql" in seed
    assert seed.index("0024_source_post_revision.sql") < seed.index(
        "0025_role_person_catalog_identity.sql"
    )
    assert "cataloged_person_id" in seed
    assert "order by created_at, person_id limit 1" in seed
    assert "cataloged_team_id" in migration_0019
    assert "cataloged_corporate_entity_id" in migration_0019
    assert "cataloged_person_id" in migration_0025
    for column_name in _ROLE_CATALOG_COLUMNS:
        assert len(column_name.split("_")) >= 2
    assert "having count(*) = 1" in migration_0019
    assert "having count(*) = 1" in migration_0025
    assert "distinct on" not in migration_0019.lower()
    assert "distinct on" not in migration_0025.lower()


def test_orchestrator_runtime_pin_matches_adr() -> None:
    """The image pin and ADR must describe the same immutable upstream commit."""
    expected_embedding_contract_commit = "1a40e0f7ad10d1a24137d69d20e44fc9a5dcdd89"
    dockerfile = (
        _ROOT / "docker" / "contextual-orchestrator" / "Dockerfile"
    ).read_text(encoding="utf-8")
    adr = (_ADR_DIRECTORY / "0083-orchestrator-runtime-commit-pin.md").read_text(
        encoding="utf-8"
    )
    docker_match = re.search(r"archive/([0-9a-f]{40})\.tar\.gz", dockerfile)
    adr_match = re.search(r"commit `([0-9a-f]{40})`", adr)
    assert docker_match is not None
    assert adr_match is not None
    assert docker_match.group(1) == adr_match.group(1)
    assert docker_match.group(1) == expected_embedding_contract_commit
