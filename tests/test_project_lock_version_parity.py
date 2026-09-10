"""Release metadata contracts for the repository-local package."""

from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def test_editable_lineageweave_lock_version_matches_project_version() -> None:
    """The frozen local package must carry the same version as pyproject.toml."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))

    project_version = project["project"]["version"]
    local_packages = [
        package
        for package in lock["package"]
        if package.get("name") == "lineageweave"
        and package.get("source", {}).get("editable") == "."
    ]

    assert len(local_packages) == 1, "uv.lock must contain exactly one editable lineageweave package"
    assert local_packages[0]["version"] == project_version, (
        "uv.lock is stale: editable lineageweave version "
        f"{local_packages[0]['version']} != pyproject.toml {project_version}"
    )
