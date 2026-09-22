"""Keep developer-facing Python commands inside the project environment."""

from pathlib import Path
import tomllib


_ROOT = Path(__file__).resolve().parents[1]


def test_makefile_runtime_targets_use_locked_uv_environment() -> None:
    """Make targets must resolve the pinned dependency graph before execution."""

    makefile = (_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "uv run --locked --extra dev python scripts/smoke_test_oidc.py" in makefile
    assert (
        "uv run --locked --extra dev --extra backend "
        "python scripts/seed_demo_data.py"
    ) in makefile
    assert "\n\tpython3 scripts/smoke_test_oidc.py" not in makefile
    assert "\n\tpython3 scripts/seed_demo_data.py" not in makefile


def test_oidc_smoke_declares_the_extra_that_supplies_pyjwt() -> None:
    """The smoke target must activate the locked extra that provides its jwt import."""

    script = (_ROOT / "scripts" / "smoke_test_oidc.py").read_text(encoding="utf-8")
    project = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dev_dependencies = project["project"]["optional-dependencies"]["dev"]

    assert "\nimport jwt\n" in script
    assert any(dependency.lower().startswith("pyjwt[") for dependency in dev_dependencies)


def test_oidc_smoke_usage_points_to_dependency_declaring_entrypoint() -> None:
    """Script help must not advertise a direct interpreter path that omits PyJWT."""

    script = (_ROOT / "scripts" / "smoke_test_oidc.py").read_text(encoding="utf-8")

    assert "Canonical usage: make smoke" in script
    assert "Usage: python3 scripts/smoke_test_oidc.py" not in script
    assert "Allow `python3 scripts/smoke_test_oidc.py`" not in script


def test_oidc_smoke_does_not_overclaim_browser_authentication_evidence() -> None:
    """A direct-access token probe must not masquerade as browser OIDC acceptance."""

    script = (_ROOT / "scripts" / "smoke_test_oidc.py").read_text(encoding="utf-8")

    assert "Resource Owner Password Credentials" in script
    assert "RFC 9700" in script
    assert "not browser OIDC authorization-flow acceptance" in script
    assert "Proves the Docker Compose Keycloak stack does a real OIDC round-trip." not in script
    assert "PASS: real login round-trip verified." not in script
