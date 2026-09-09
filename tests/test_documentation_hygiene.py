"""Permanent hygiene checks for committed architecture-decision records."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_ADR_DIRECTORY = _ROOT / "docs" / "adr"
_PRODUCT_GAP_BASELINE = _ROOT / "docs" / "product-technical-gap-baseline.md"
_ROLE_CATALOG_COLUMNS = (
    "cataloged_team_id",
    "cataloged_corporate_entity_id",
    "cataloged_person_id",
)
_ADR_NAME = re.compile(r"^(?P<number>[0-9]{4})-.+\.md$")
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
_DATED_OBSERVATION_PATTERN = re.compile(r"Dated observation:\s*(\d{4}-\d{2}-\d{2})")
_OVERLAY_HEADER_PATTERN = re.compile(r"^>\s*Exact-head loop overlay[^\n]*", re.MULTILINE)
_PROTECTED_MAIN_SHA_PATTERN = re.compile(r"`([0-9a-f]{40})`")
_MUTABLE_STILL_PATTERN = re.compile(r"\bstill\b", re.IGNORECASE)
_MUTABLE_CURRENT_PATTERN = re.compile(r"\bcurrent\b", re.IGNORECASE)


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


def test_gap_baseline_first_section_is_dated_observation() -> None:
    """Issue #963: the ledger must defer live authority to repository state."""
    baseline = _PRODUCT_GAP_BASELINE.read_text(encoding="utf-8")

    dated_match = _DATED_OBSERVATION_PATTERN.search(baseline)
    assert dated_match is not None, (
        "product-gap baseline must open with a dated 'Dated observation: YYYY-MM-DD' section"
    )

    overlay_headers = list(_OVERLAY_HEADER_PATTERN.finditer(baseline))
    assert overlay_headers, "product-gap baseline must retain dated historical overlays"
    first_overlay_start = overlay_headers[0].start()
    assert dated_match.start() < first_overlay_start, (
        "the dated observation must precede every 'Exact-head loop overlay'"
    )

    observation_section = baseline[dated_match.start() : first_overlay_start]
    sha_match = _PROTECTED_MAIN_SHA_PATTERN.search(observation_section)
    assert sha_match is not None, (
        "dated observation must name its observed protected-main SHA as a verifiable repo fact"
    )
    assert re.fullmatch(r"[0-9a-f]{40}", sha_match.group(1)) is not None

    receipt_markers = ("at refresh", "Live queue", "UTC")
    assert any(marker in observation_section for marker in receipt_markers), (
        "mutable queue counts must read as a dated receipt, not timeless product truth"
    )
    if "open PRs" in observation_section:
        assert "at refresh" in observation_section or "Live queue" in observation_section, (
            "mutable PR counts must stay time-scoped to their receipt moment"
        )

    lowered = observation_section.lower()
    assert "sole current authority" not in lowered, (
        "a dated evidence ledger must not compete with live repository authority"
    )
    assert "live agents/pr/issue/protected-ref/check state remains current authority" in lowered, (
        "the dated observation must explicitly delegate current lifecycle/check authority "
        "to live repository state"
    )
    assert "unfixable from any branch" not in lowered, (
        "owner-side failures must remain time-scoped repair findings, not timeless impossibility claims"
    )
    assert "historical" in lowered, (
        "the dated observation must mark every overlay below as historical evidence"
    )


def test_gap_baseline_historical_overlays_use_time_scoped_language() -> None:
    """Issue #963: historical overlays must not claim unqualified present authority."""
    import bisect

    baseline = _PRODUCT_GAP_BASELINE.read_text(encoding="utf-8")
    lines = baseline.splitlines()

    dated_match = _DATED_OBSERVATION_PATTERN.search(baseline)
    assert dated_match is not None
    overlay_matches = list(_OVERLAY_HEADER_PATTERN.finditer(baseline))
    overlay_starts = [m.start() for m in overlay_matches if m.start() > dated_match.start()]
    assert overlay_starts, "no historical overlays found below the dated observation"

    line_starts: list[int] = []
    offset = 0
    for line in lines:
        line_starts.append(offset)
        offset += len(line) + 1

    def line_number_for_offset(target: int) -> int:
        """Return the 1-indexed line number containing the character offset."""
        return bisect.bisect_right(line_starts, target)

    for index, overlay_start in enumerate(overlay_starts):
        header_end = baseline.find("\n", overlay_start)
        header = baseline[overlay_start:header_end] if header_end != -1 else baseline[overlay_start:]
        header_line = line_number_for_offset(overlay_start)
        assert "historical" in header.lower(), (
            f"overlay header at line {header_line} must carry an explicit "
            f"'(historical, <date>)' marker: {header.strip()[:120]}"
        )
        assert "Protected `main` is" not in header, (
            f"overlay header at line {header_line} must use 'was', not 'is', "
            f"for its protected-main claim: {header.strip()[:120]}"
        )

        next_overlay = overlay_starts[index + 1] if index + 1 < len(overlay_starts) else len(baseline)
        body = baseline[header_end:next_overlay] if header_end != -1 else ""
        heading_match = re.search(r"^##?\s", body, re.MULTILINE)
        if heading_match is not None:
            body = body[: heading_match.start()]
        assert "Protected `main` is" not in body, (
            f"historical overlay starting at line {header_line} must use 'was', "
            "not 'is', for protected-main claims"
        )
        for body_line in body.splitlines():
            lowered = body_line.lower()
            if _MUTABLE_STILL_PATTERN.search(body_line) and "historical" not in lowered:
                raise AssertionError(
                    f"historical overlay line {header_line} uses unqualified 'still' "
                    f"outside a time-scoped marker: {body_line.strip()[:160]}"
                )
            if _MUTABLE_CURRENT_PATTERN.search(body_line) and "historical" not in lowered:
                raise AssertionError(
                    f"historical overlay line {header_line} uses unqualified 'current' "
                    f"outside a time-scoped marker: {body_line.strip()[:160]}"
                )
            if "supersedes" in lowered and "historical" not in lowered:
                raise AssertionError(
                    f"historical overlay line {header_line} uses unqualified 'supersedes' "
                    f"outside a time-scoped marker: {body_line.strip()[:160]}"
                )
