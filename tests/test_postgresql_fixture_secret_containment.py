"""Keep disposable PostgreSQL credentials out of actual skipped-test reports."""
from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("module_name", [
    "test_customer_hint_resolution_postgresql.py",
    "test_synthetic_seed_cleanup.py",
    "test_person_mention_projection.py",
    "test_prov_o_schema.py",
    "test_schema.py",
    "test_source_post_voice_history_live.py",
])
def test_postgresql_skip_does_not_publish_configured_credentials(tmp_path, module_name) -> None:
    """Exercise each PostgreSQL module's real skip stdout and JUnit boundary."""
    root = Path(__file__).resolve().parents[1]
    module = root / "tests" / module_name
    definitions = ast.parse(module.read_text(encoding="utf-8")).body
    case = next(
        node.name for node in definitions
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    username = "synthetic_skip_user_sentinel"
    password = "synthetic_skip_password_sentinel"
    dsn = f"postgresql://{username}:{password}@127.0.0.1:1/unavailable?connect_timeout=1"
    env = {
        key: value for key, value in os.environ.items()
        if key in {"PATH", "HOME", "TMPDIR", "LANG", "LC_ALL"}
    }
    env.update({
        "LINEAGEWEAVE_TEST_POSTGRES_ADMIN_DSN": dsn,
        "PYTHONPATH": str(root),
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    xml = tmp_path / "skipped.xml"
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            f"tests/{module_name}::{case}",
            "-q", "-ra", "-p", "no:cacheprovider", f"--junitxml={xml}",
        ],
        cwd=root, env=env, capture_output=True, text=True, timeout=45,
    )
    assert result.returncode == 0
    assert "1 skipped" in result.stdout
    assert xml.exists()
    reports = result.stdout + result.stderr + xml.read_text(encoding="utf-8")
    assert username not in reports
    assert password not in reports
    assert dsn not in reports
