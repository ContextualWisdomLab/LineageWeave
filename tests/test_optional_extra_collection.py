"""Unit tests for optional-extra pytest collection skipping."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from lineageweave.optional_extra_collection import (
    OPTIONAL_EXTRA_MODULES,
    collection_path_requires_missing_extras,
    missing_optional_extra_modules,
)


def test_missing_optional_extra_modules_returns_absent_names() -> None:
    """Names whose find_spec is None are reported; present names are not."""

    def fake_find_spec(name: str) -> object | None:
        if name == "asyncpg":
            return None
        return object()

    with patch(
        "lineageweave.optional_extra_collection.importlib.util.find_spec",
        side_effect=fake_find_spec,
    ):
        assert missing_optional_extra_modules(("asyncpg", "redis")) == ("asyncpg",)


def test_collection_path_does_not_skip_when_no_extras_are_missing(
    tmp_path: Path,
) -> None:
    """Hosted CI with extras installed still collects every suite."""
    path = tmp_path / "test_api.py"
    path.write_text("import asyncpg\n", encoding="utf-8")
    assert collection_path_requires_missing_extras(path, ()) is False


def test_collection_path_skips_backend_tree_when_asyncpg_is_missing(
    tmp_path: Path,
) -> None:
    """Backend tests import the FastAPI app, which imports asyncpg at module level."""
    backend_test = tmp_path / "backend" / "tests" / "test_api.py"
    backend_test.parent.mkdir(parents=True)
    backend_test.write_text("import pytest\n", encoding="utf-8")
    assert collection_path_requires_missing_extras(backend_test, ("asyncpg",)) is True
    assert collection_path_requires_missing_extras(backend_test, ("fast_mlsirm",)) is True
    assert collection_path_requires_missing_extras(backend_test, ("numpy",)) is True


def test_collection_path_skips_files_that_import_a_missing_extra(
    tmp_path: Path,
) -> None:
    """A test that imports fast_mlsirm is ignored only when that extra is absent."""
    path = tmp_path / "test_post_evaluation.py"
    path.write_text("from fast_mlsirm import LLMJudgeResult\n", encoding="utf-8")
    assert collection_path_requires_missing_extras(path, ("fast_mlsirm",)) is True
    assert collection_path_requires_missing_extras(path, ("asyncpg",)) is False


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
    assert collection_path_requires_missing_extras(post_import, ("asyncpg",)) is True
    seed = tmp_path / "test_seed.py"
    seed.write_text("from scripts.seed_demo_data import seed\n", encoding="utf-8")
    assert collection_path_requires_missing_extras(seed, ("redis",)) is True


def test_helper_test_module_is_never_ignored(tmp_path: Path) -> None:
    """The collection-helper tests must run in the sandbox that lacks extras."""
    path = tmp_path / "test_optional_extra_collection.py"
    path.write_text("import asyncpg\n", encoding="utf-8")
    assert collection_path_requires_missing_extras(path, OPTIONAL_EXTRA_MODULES) is False


def test_non_python_paths_are_not_ignored(tmp_path: Path) -> None:
    """Collection directories and non-Python files stay visible to pytest."""
    directory = tmp_path / "tests"
    directory.mkdir()
    assert collection_path_requires_missing_extras(directory, ("asyncpg",)) is False
