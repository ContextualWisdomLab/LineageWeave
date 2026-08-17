"""Public-content denylist for the TEPP honesty correction."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCOPED_PATHS = (
    _ROOT / "lineageweave" / "tepp_result.py",
    _ROOT / "lineageweave" / "tepp_client.py",
    _ROOT / "backend" / "app" / "analysis_run_start.py",
    _ROOT / "backend" / "app" / "analysis_run_ingestion.py",
    _ROOT / "migrations" / "0029_analysis_run_tepp_accepted.sql",
    _ROOT / "docs" / "adr" / "0035-tepp-accepted-transport-evidence.md",
    _ROOT / "CHANGELOG.d" / "2.12.1-tepp-accepted-transport-evidence.md",
    _ROOT / "tests" / "test_tepp_result.py",
    _ROOT / "tests" / "test_analysis_run_tepp_accepted_schema.py",
)
_FORBIDDEN_TABLES = (
    "document_record",
    "model_artifact",
    "topic_prevalence",
    "membership_assignment",
    "event_instance",
)
_FORBIDDEN_SECRETS = (
    "NVIDIA_NIM_API_KEY",
    "postgres://",
)


def test_tepp_honesty_files_keep_synthetic_public_content() -> None:
    """Changed TEPP files must not leak private tables or credentials."""
    for path in _SCOPED_PATHS:
        text = path.read_text(encoding="utf-8")
        lowered = text.casefold()
        for token in _FORBIDDEN_TABLES:
            assert token not in lowered, f"{token} in {path.name}"
        for token in _FORBIDDEN_SECRETS:
            assert token.casefold() not in lowered, f"{token} in {path.name}"
        assert "is a validated multilevel estimate" not in lowered
