"""Canonical Compose embedding capability contract tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess


_ROOT = Path(__file__).parents[1]


def test_rendered_compose_owns_exact_embedding_pair(tmp_path: Path) -> None:
    """Render Compose and retain the gateway-owned exact embedding model."""
    (tmp_path / ".env").write_text("", encoding="utf-8")
    environment = os.environ.copy()
    environment["HOME"] = str(tmp_path)
    standalone_compose = shutil.which("docker-compose")
    compose_command = [standalone_compose] if standalone_compose else ["docker", "compose"]
    rendered = subprocess.run(
        [*compose_command, "-f", str(_ROOT / "docker-compose.yml"), "config", "--format", "json"],
        cwd=_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    config = json.loads(rendered.stdout)
    orchestrator_environment = config["services"]["orchestrator"]["environment"]

    assert orchestrator_environment["LLM_GATEWAY_EMBEDDING_MODEL"] == "text-embedding-3-large"


def test_lineage_clients_do_not_select_an_embedding_model() -> None:
    """Keep provider/model ownership outside LineageWeave client services."""
    compose = (_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert compose.count("LLM_GATEWAY_EMBEDDING_MODEL:") == 1
