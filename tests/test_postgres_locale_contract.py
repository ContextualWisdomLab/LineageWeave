"""Contracts for the PostgreSQL image and locale used by acceptance lanes."""

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
POSTGRES_IMAGE = (
    "postgres:16.15-bookworm@sha256:"
    "bb3e1a57e5407e0a5280b4211980a5e537f4abd234a87014ac979849a78dd825"
)
SERVICE_WORKFLOWS = (
    REPOSITORY_ROOT / ".github/workflows/tests.yml",
    REPOSITORY_ROOT / ".github/workflows/prov-o-contract.yml",
)


def test_acceptance_workflows_pin_one_debian_postgres_locale_contract() -> None:
    """Both PostgreSQL acceptance lanes must use the same explicit locale."""

    for workflow_path in SERVICE_WORKFLOWS:
        workflow = workflow_path.read_text(encoding="utf-8")
        assert f"image: {POSTGRES_IMAGE}" in workflow
        assert "LANG: en_US.utf8" in workflow
        assert 'POSTGRES_INITDB_ARGS: "--locale=en_US.utf8"' in workflow
        assert "postgres:16-alpine" not in workflow


def test_product_postgres_image_uses_the_same_debian_locale_contract() -> None:
    """The product database image must not diverge from acceptance PostgreSQL."""

    dockerfile = (
        REPOSITORY_ROOT / "docker/postgres-init/Dockerfile"
    ).read_text(encoding="utf-8")
    assert dockerfile.startswith(f"FROM {POSTGRES_IMAGE}\n")
    assert "ENV LANG=en_US.utf8" in dockerfile
    assert "postgres:16-alpine" not in dockerfile
