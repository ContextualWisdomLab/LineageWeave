"""Keep every Compose entry point on the canonical application project."""

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_compose_uses_canonical_project_name_outside_repository_directory(tmp_path: Path) -> None:
    """The Compose file keeps project identity stable in an isolated checkout.

    The orchestrator's required ``${HOME}/.env`` is resolved at ``config``
    time, so the test supplies its own empty file under a synthetic HOME.
    This keeps the check hermetic on runners without a private env file and
    does not load the developer's real ``HOME/.env`` file.
    """
    home = tmp_path / "home"
    home.mkdir()
    (home / ".env").write_text("", encoding="utf-8")
    project = tmp_path / "project"
    project.mkdir()
    environment = os.environ.copy()
    environment.pop("COMPOSE_PROJECT_NAME", None)
    environment.pop("COMPOSE_ENV_FILES", None)
    environment.pop("POSTGRES_PASSWORD", None)
    # Keep Docker CLI plugin discovery (``docker compose``) on the caller's
    # configuration directory; only the Compose ``${HOME}`` interpolation moves.
    environment.setdefault("DOCKER_CONFIG", str(Path.home() / ".docker"))
    environment["HOME"] = str(home)
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--project-directory",
            str(project),
            "-f",
            str(ROOT / "docker-compose.yml"),
            "config",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert json.loads(result.stdout)["name"] == "lineageweave"


def test_make_commands_pin_the_official_compose_project() -> None:
    """Official service lifecycle commands override ambient project names."""
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert 'COMPOSE := docker compose --env-file "$$HOME/.env" --project-name lineageweave' in makefile


def test_compose_project_check_drops_external_env_file_and_password(tmp_path: Path, monkeypatch) -> None:
    """Caller overrides cannot bypass the empty env file or reflect a DB password."""
    monkeypatch.setenv("COMPOSE_ENV_FILES", str(tmp_path / "missing-caller.env"))
    monkeypatch.setenv("POSTGRES_PASSWORD", "synthetic-password-not-for-compose")
    calls = []

    def capture_config(command, **kwargs):
        environment = kwargs["env"]
        assert "COMPOSE_ENV_FILES" not in environment
        assert "POSTGRES_PASSWORD" not in environment
        assert (Path(environment["HOME"]) / ".env").read_text(encoding="utf-8") == ""
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout='{"name": "lineageweave"}')

    monkeypatch.setattr(subprocess, "run", capture_config)
    test_compose_uses_canonical_project_name_outside_repository_directory(tmp_path)
    assert len(calls) == 1
