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


def _mapping_block(document: str, key: str) -> str:
    """Return one indentation-scoped YAML mapping block without parsing values."""

    lines = document.splitlines()
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped != f"{key}:":
            continue
        indentation = len(line) - len(stripped)
        block = [line]
        for nested_line in lines[index + 1 :]:
            nested_stripped = nested_line.lstrip()
            if nested_stripped:
                nested_indentation = len(nested_line) - len(nested_stripped)
                if nested_indentation <= indentation:
                    break
            block.append(nested_line)
        return "\n".join(block)
    raise AssertionError(f"missing YAML mapping: {key}")


def test_acceptance_workflows_pin_one_debian_postgres_locale_contract() -> None:
    """Both PostgreSQL acceptance lanes must use the same service locale."""

    for workflow_path in SERVICE_WORKFLOWS:
        workflow = workflow_path.read_text(encoding="utf-8")
        services = _mapping_block(workflow, "services")
        postgres = _mapping_block(services, "postgres")
        environment = _mapping_block(postgres, "env")

        assert f"image: {POSTGRES_IMAGE}" in postgres
        assert "LANG: en_US.utf8" in environment
        assert 'POSTGRES_INITDB_ARGS: "--locale=en_US.utf8"' in environment
        assert "select datcollate, datctype from pg_database" in workflow
        assert "show lc_collate" not in workflow
        assert "postgres:16-alpine" not in workflow


def test_product_postgres_image_uses_the_same_debian_locale_contract() -> None:
    """The product database image must not diverge from acceptance PostgreSQL."""

    dockerfile = (
        REPOSITORY_ROOT / "docker/postgres-init/Dockerfile"
    ).read_text(encoding="utf-8")
    assert dockerfile.startswith(f"FROM {POSTGRES_IMAGE}\n")
    assert "ENV LANG=en_US.utf8" in dockerfile
    assert "postgres:16-alpine" not in dockerfile
