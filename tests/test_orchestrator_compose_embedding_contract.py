"""Canonical Compose embedding capability contract tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
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


def test_orchestrator_image_tag_matches_the_downloaded_revision() -> None:
    """Prevent a cached image tag from claiming a different source revision."""
    compose = (_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    dockerfile = (_ROOT / "docker/contextual-orchestrator/Dockerfile").read_text(
        encoding="utf-8"
    )
    image_match = re.search(r"-orchestrator:([0-9a-f]{40})", compose)
    archive_match = re.search(r"archive/([0-9a-f]{40})\.tar\.gz", dockerfile)
    assert image_match is not None
    assert archive_match is not None
    assert image_match.group(1) == archive_match.group(1)


def test_orchestrator_image_verifies_archive_and_dependency_bytes() -> None:
    """Require byte verification for upstream source and all installed wheels."""
    dockerfile = (_ROOT / "docker/contextual-orchestrator/Dockerfile").read_text(
        encoding="utf-8"
    )
    requirements = (
        _ROOT / "docker/contextual-orchestrator/requirements.lock"
    ).read_text(encoding="utf-8")
    roots = (_ROOT / "docker/contextual-orchestrator/requirements.in").read_text(
        encoding="utf-8"
    )

    assert re.search(
        r"ADD --checksum=sha256:[0-9a-f]{64} "
        r"https://github\.com/ContextualWisdomLab/contextual-orchestrator/archive/"
        r"[0-9a-f]{40}\.tar\.gz ",
        dockerfile,
    )
    assert "--require-hashes" in dockerfile
    assert "-r /tmp/orchestrator-requirements.lock" in dockerfile
    assert not re.search(r"(?:>=|~=|==[^\n ]*\*)", roots)
    assert not re.search(
        r"^[a-z0-9_.-]+(?:\[[^]]+\])?\s*(?:>=|~=|==[^\n ]*\*)",
        requirements,
        re.MULTILINE,
    )
    locked_packages = re.findall(
        r"^([a-z0-9_.-]+)==[^\\\n ]+ \\$", requirements, re.MULTILINE
    )
    assert len(locked_packages) == len(set(locked_packages))
    assert len(locked_packages) >= 14
    assert requirements.count("--hash=sha256:") >= len(locked_packages)
