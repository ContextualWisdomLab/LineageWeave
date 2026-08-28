"""Canonical Compose embedding capability contract tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess


_ROOT = Path(__file__).parents[1]


def test_rendered_compose_keeps_embedding_selection_upstream(tmp_path: Path) -> None:
    """Render Compose without a LineageWeave-owned embedding selector."""
    (tmp_path / ".env").write_text("", encoding="utf-8")
    environment = os.environ.copy()
    environment["HOME"] = str(tmp_path)
    standalone_compose = shutil.which("docker-compose")
    compose_command = [standalone_compose] if standalone_compose else ["docker", "compose"]
    rendered = subprocess.run(
        [
            *compose_command,
            "-f",
            str(_ROOT / "docker-compose.yml"),
            "--profile",
            "mcp",
            "config",
            "--format",
            "json",
        ],
        cwd=_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    config = json.loads(rendered.stdout)
    orchestrator_environment = config["services"]["orchestrator"]["environment"]
    backend_environment = config["services"]["backend"]["environment"]
    backend_dependencies = config["services"]["backend"]["depends_on"]

    assert "LLM_GATEWAY_EMBEDDING_MODEL" not in orchestrator_environment
    assert "LLM_GATEWAY_EMBEDDING_PROVIDER" not in orchestrator_environment
    assert (
        orchestrator_environment["CONTEXTUAL_ORCHESTRATOR_TOKEN"]
        == backend_environment["ORCHESTRATOR_API_KEY"]
    )
    assert config["services"]["orchestrator"]["healthcheck"]["test"][-1].find(
        "/healthz"
    ) >= 0
    assert backend_dependencies["backend-worker"]["condition"] == "service_healthy"
    assert config["services"]["backend-worker"]["command"] == [
        "python",
        "-m",
        "backend.app.worker",
    ]
    assert config["services"]["backend-worker"]["healthcheck"]["test"] == [
        "CMD",
        "/bin/sh",
        "/app/backend/worker-healthcheck.sh",
    ]
    assert backend_environment["ORCHESTRATOR_ROUTING_ENDPOINT"] == ""
    assert config["services"]["backend-worker"]["environment"][
        "ORCHESTRATOR_ROUTING_ENDPOINT"
    ] == ""
    assert config["services"]["mcp"]["environment"][
        "ORCHESTRATOR_ROUTING_ENDPOINT"
    ] == ""
    assert "env_file" not in config["services"]["backend"]
    assert "env_file" not in config["services"]["backend-worker"]
    assert "env_file" not in config["services"]["mcp"]


def test_routing_endpoint_contract_is_documented() -> None:
    """The ADR limits the runtime selector to exact text API paths."""
    adr = (
        _ROOT / "docs/adr/0070-contextual-orchestrator-upstream-integration.md"
    ).read_text(encoding="utf-8")
    assert "`ORCHESTRATOR_ROUTING_ENDPOINT`" in adr
    assert "exactly `/v1/chat/completions` or `/v1/responses`" in adr
    assert "not applied to embeddings, batch routes" in adr

    compose = (_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    selector_boundary = (
        "ORCHESTRATOR_ROUTING_ENDPOINT: ${ORCHESTRATOR_ROUTING_ENDPOINT:-}"
    )
    assert compose.count(selector_boundary) == 2
    orchestrator_service = compose.split("  orchestrator:\n", 1)[1].split(
        "  backend:\n", 1
    )[0]
    assert "env_file:\n      - ${HOME}/.env" in orchestrator_service
    assert selector_boundary not in orchestrator_service


def test_lineage_clients_do_not_select_an_embedding_model() -> None:
    """Keep provider/model ownership outside LineageWeave client services."""
    compose = (_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "LLM_GATEWAY_EMBEDDING_MODEL:" not in compose
    assert "LLM_GATEWAY_EMBEDDING_PROVIDER:" not in compose
