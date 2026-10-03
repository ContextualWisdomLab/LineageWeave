"""Keep Compose project and data-volume identities explicit and recoverable."""

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _compose_config(
    project_directory: Path,
    *,
    project_name: str | None = None,
    volume_names: dict[str, str] | None = None,
) -> dict[str, object]:
    """Render Compose without printing interpolated environment values."""
    environment = os.environ.copy()
    environment.pop("COMPOSE_PROJECT_NAME", None)
    environment.update(volume_names or {})
    command = ["docker", "compose", "--project-directory", str(project_directory)]
    if project_name:
        command.extend(["--project-name", project_name])
    command.extend(
        ["-f", str(ROOT / "docker-compose.yml"), "config", "--format", "json"]
    )
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    return json.loads(result.stdout)


def test_compose_uses_canonical_name_and_volumes_outside_repository_directory(
    tmp_path: Path,
) -> None:
    """The standard project keeps its identity and volume names stable."""
    project = _compose_config(tmp_path)

    assert project["name"] == "lineageweave"
    volumes = project["volumes"]
    assert volumes["postgres_data"]["name"] == "lineageweave_postgres_data"
    assert volumes["valkey_data"]["name"] == "lineageweave_valkey_data"


def test_isolated_projects_get_project_scoped_data_volumes(tmp_path: Path) -> None:
    """An explicit test project cannot attach the official project's volumes."""
    project = _compose_config(tmp_path, project_name="lineageweave-test")

    assert project["name"] == "lineageweave-test"
    volumes = project["volumes"]
    assert volumes["postgres_data"]["name"] == "lineageweave-test_postgres_data"
    assert volumes["valkey_data"]["name"] == "lineageweave-test_valkey_data"


def test_existing_named_volumes_can_be_reused_during_project_migration(
    tmp_path: Path,
) -> None:
    """An operator can attach the exact old volumes to the canonical project."""
    project = _compose_config(
        tmp_path,
        volume_names={
            "POSTGRES_DATA_VOLUME": "prior_stack_postgres_data",
            "VALKEY_DATA_VOLUME": "prior_stack_valkey_data",
        },
    )

    volumes = project["volumes"]
    assert volumes["postgres_data"]["name"] == "prior_stack_postgres_data"
    assert volumes["valkey_data"]["name"] == "prior_stack_valkey_data"


def test_make_down_legacy_stops_only_the_named_project_without_deleting_volumes(
    tmp_path: Path,
) -> None:
    """Legacy cleanup targets the supplied project and never passes ``-v``."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    capture = tmp_path / "docker-args.txt"
    docker = bin_dir / "docker"
    docker.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$@" > "$DOCKER_ARGS_CAPTURE"\n',
        encoding="utf-8",
    )
    docker.chmod(0o755)
    environment = os.environ.copy()
    environment.update(
        {
            "DOCKER_ARGS_CAPTURE": str(capture),
            "HOME": str(tmp_path),
            "LEGACY_COMPOSE_PROJECT_NAME": "prior-stack",
            "PATH": f"{bin_dir}:{environment['PATH']}",
        }
    )

    subprocess.run(
        ["make", "down-legacy"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert capture.read_text(encoding="utf-8").splitlines() == [
        "compose",
        "--env-file",
        str(tmp_path / ".env"),
        "--project-name",
        "prior-stack",
        "down",
    ]


def test_make_commands_pin_the_official_compose_project() -> None:
    """Official service lifecycle commands use the canonical project name."""
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert 'COMPOSE := docker compose --env-file "$$HOME/.env" --project-name lineageweave' in makefile
