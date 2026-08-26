"""Keep developer-facing Python commands inside the project environment."""

from pathlib import Path


def test_makefile_runtime_targets_use_locked_uv_environment() -> None:
    """Make targets must resolve the pinned dependency graph before execution."""

    makefile = (Path(__file__).resolve().parents[1] / "Makefile").read_text(
        encoding="utf-8"
    )

    assert "uv run --locked --extra dev python scripts/smoke_test_oidc.py" in makefile
    assert "--extra backend python scripts/smoke_test_oidc.py" not in makefile
    assert "uv run --locked python scripts/seed_demo_data.py" in makefile
    assert "\n\tpython3 scripts/smoke_test_oidc.py" not in makefile
    assert "\n\tpython3 scripts/seed_demo_data.py" not in makefile
