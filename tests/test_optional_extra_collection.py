"""Unit tests for optional-extra pytest collection skipping."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import conftest as root_conftest
from lineageweave.optional_extra_collection import (
    OPTIONAL_EXTRA_MODULES,
    collection_path_requires_missing_extras,
    missing_optional_extra_modules,
)


def test_missing_optional_extra_modules_returns_absent_names() -> None:
    """Names whose find_spec is None are reported; present names are not."""

    def fake_find_spec(name: str) -> object | None:
        """Model one unavailable optional module and installed siblings."""
        if name == "pg8000":
            return None
        return object()

    with patch(
        "lineageweave.optional_extra_collection.importlib.util.find_spec",
        side_effect=fake_find_spec,
    ):
        assert missing_optional_extra_modules(("pg8000", "redis")) == ("pg8000",)


def test_collection_path_does_not_skip_when_no_extras_are_missing(
    tmp_path: Path,
) -> None:
    """Hosted CI with extras installed still collects every suite."""
    path = tmp_path / "test_api.py"
    path.write_text("import asyncpg\n", encoding="utf-8")
    assert collection_path_requires_missing_extras(path, ()) is False


def test_collection_path_skips_only_backend_tests_with_transitive_missing_imports(
    tmp_path: Path,
) -> None:
    """Partial environments keep backend tests whose import graph is available."""
    backend_dir = tmp_path / "backend" / "tests"
    backend_dir.mkdir(parents=True)
    api_test = backend_dir / "test_api.py"
    api_test.write_text("from backend.app.main import app\n", encoding="utf-8")
    config_test = backend_dir / "test_config.py"
    config_test.write_text("from backend.app.config import Settings\n", encoding="utf-8")

    for missing in ("asyncpg", "redis", "fast_mlsirm", "numpy"):
        assert collection_path_requires_missing_extras(api_test, (missing,)) is True
        assert collection_path_requires_missing_extras(config_test, (missing,)) is False


def test_collection_path_skips_files_that_import_a_missing_extra(
    tmp_path: Path,
) -> None:
    """Direct optional imports are skipped only when that exact module is absent."""
    psychometrics = tmp_path / "test_post_evaluation.py"
    psychometrics.write_text("from fast_mlsirm import LLMJudgeResult\n", encoding="utf-8")
    assert collection_path_requires_missing_extras(psychometrics, ("fast_mlsirm",)) is True
    assert collection_path_requires_missing_extras(psychometrics, ("asyncpg",)) is False

    postgres = tmp_path / "test_postgres_sync.py"
    postgres.write_text("import pg8000.dbapi\n", encoding="utf-8")
    assert collection_path_requires_missing_extras(postgres, ("pg8000",)) is True
    assert collection_path_requires_missing_extras(postgres, ("asyncpg",)) is False


def test_collection_path_does_not_match_comments_or_import_prefixes(
    tmp_path: Path,
) -> None:
    """Only parsed imports may suppress collection in the reduced sandbox."""
    path = tmp_path / "test_unrelated.py"
    path.write_text(
        '"""Example text: import asyncpg."""\n'
        "import rediscache\n"
        "from backends import client\n",
        encoding="utf-8",
    )
    assert collection_path_requires_missing_extras(
        path, ("asyncpg", "redis")
    ) is False


def test_collection_path_skips_known_transitive_optional_importers(
    tmp_path: Path,
) -> None:
    """Known local modules propagate their hard optional import."""
    period_report = tmp_path / "test_period_report.py"
    period_report.write_text(
        "from lineageweave.period_report import build_period_report\n",
        encoding="utf-8",
    )
    post_import = tmp_path / "test_import_postgresql_posts.py"
    post_import.write_text(
        "from scripts.import_postgresql_posts import parse_args\n",
        encoding="utf-8",
    )
    assert (
        collection_path_requires_missing_extras(period_report, ("fast_mlsirm",))
        is True
    )
    assert collection_path_requires_missing_extras(period_report, ("numpy",)) is True
    assert (
        collection_path_requires_missing_extras(period_report, ("asyncpg",)) is False
    )
    post_evaluation = tmp_path / "test_post_evaluation.py"
    post_evaluation.write_text(
        "from lineageweave.post_evaluation import LLMJudgeResult\n",
        encoding="utf-8",
    )
    assert (
        collection_path_requires_missing_extras(post_evaluation, ("numpy",)) is False
    )
    backend_import = tmp_path / "test_report_ingestion.py"
    backend_import.write_text(
        "from backend.app.report_ingestion import ingest_report\n",
        encoding="utf-8",
    )
    assert collection_path_requires_missing_extras(backend_import, ("asyncpg",)) is True
    assert collection_path_requires_missing_extras(post_import, ("asyncpg",)) is True
    seed = tmp_path / "test_seed.py"
    seed.write_text("from scripts.seed_demo_data import seed\n", encoding="utf-8")
    assert collection_path_requires_missing_extras(seed, ("redis",)) is False

    sync_postgres = tmp_path / "test_sync_postgres.py"
    sync_postgres.write_text(
        "from lineageweave.postgres_sync import connect\n",
        encoding="utf-8",
    )
    assert collection_path_requires_missing_extras(sync_postgres, ("pg8000",)) is True


def test_collection_path_tracks_submodule_imported_from_package(tmp_path: Path) -> None:
    """Package-style submodule imports still expose their transitive optional driver."""
    sync_postgres = tmp_path / "test_sync_postgres_package_import.py"
    sync_postgres.write_text(
        "from lineageweave import postgres_sync as sync_postgres\n",
        encoding="utf-8",
    )

    assert collection_path_requires_missing_extras(sync_postgres, ("pg8000",)) is True


def test_helper_test_module_is_never_ignored(tmp_path: Path) -> None:
    """The collection-helper tests must run in the sandbox that lacks extras."""
    path = tmp_path / "test_optional_extra_collection.py"
    path.write_text("import pg8000\n", encoding="utf-8")
    assert collection_path_requires_missing_extras(path, OPTIONAL_EXTRA_MODULES) is False


def test_non_python_paths_are_not_ignored(tmp_path: Path) -> None:
    """Collection directories and non-Python files stay visible to pytest."""
    directory = tmp_path / "tests"
    directory.mkdir()
    assert collection_path_requires_missing_extras(directory, ("asyncpg",)) is False


def test_unreadable_or_invalid_python_does_not_suppress_collection(
    tmp_path: Path,
) -> None:
    """Collection errors stay visible instead of being hidden as missing extras."""
    invalid = tmp_path / "test_invalid.py"
    invalid.write_text("from asyncpg import\n", encoding="utf-8")
    assert collection_path_requires_missing_extras(invalid, ("asyncpg",)) is False

    unreadable = tmp_path / "test_unreadable.py"
    with patch.object(Path, "read_text", side_effect=OSError("unreadable")):
        assert (
            collection_path_requires_missing_extras(unreadable, ("asyncpg",))
            is False
        )

    non_utf8 = tmp_path / "test_non_utf8.py"
    non_utf8.write_bytes(b"\xff")
    assert collection_path_requires_missing_extras(non_utf8, ("asyncpg",)) is False


def test_root_hook_defers_kept_paths_to_other_pytest_ignore_rules(
    tmp_path: Path,
) -> None:
    """The first-result hook ignores optional paths and defers kept paths."""
    optional_test = tmp_path / "test_optional.py"
    optional_test.write_text("import asyncpg\n", encoding="utf-8")
    ordinary_test = tmp_path / "test_ordinary.py"
    ordinary_test.write_text("import pytest\n", encoding="utf-8")

    with patch.object(
        root_conftest,
        "missing_optional_extra_modules",
        return_value=("asyncpg",),
    ):
        assert root_conftest.pytest_ignore_collect(optional_test, object()) is True
        assert root_conftest.pytest_ignore_collect(ordinary_test, object()) is None
