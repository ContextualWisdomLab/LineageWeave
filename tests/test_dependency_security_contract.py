"""Security floors for dependencies with repository-wide scan findings."""

from pathlib import Path
import tomllib


def _locked_version(package_name: str) -> tuple[int, ...]:
    """Return a package version from the canonical uv lock as integers."""
    lock = tomllib.loads(Path("uv.lock").read_text(encoding="utf-8"))
    for package in lock["package"]:
        if package["name"] == package_name:
            return tuple(int(part) for part in package["version"].split("."))
    raise AssertionError(f"{package_name} is absent from uv.lock")


def test_vulnerable_auth_and_transport_versions_cannot_return() -> None:
    """Keep the PyJWT and urllib3 fixes enforced at their locked source."""
    assert _locked_version("pyjwt") >= (2, 15, 1)
    assert _locked_version("urllib3") >= (2, 8, 0)
