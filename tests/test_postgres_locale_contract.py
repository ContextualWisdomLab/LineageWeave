"""Contracts for the PostgreSQL image and locale used by acceptance lanes."""

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
POSTGRES_IMAGE = (
    "postgres:16.15-bookworm@sha256:"
    "bb3e1a57e5407e0a5280b4211980a5e537f4abd234a87014ac979849a78dd825"
)
SERVICE_WORKFLOWS = (
    (REPOSITORY_ROOT / ".github/workflows/tests.yml", "pytest"),
    (REPOSITORY_ROOT / ".github/workflows/prov-o-contract.yml", "standards-contract"),
)


def _mapping_block(document: str, key: str) -> str:
    """Return one indentation-scoped YAML mapping block for an exact key."""

    lines = document.splitlines()
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("#") or stripped != f"{key}:":
            continue
        indentation = len(line) - len(stripped)
        block = [line]
        for nested_line in lines[index + 1 :]:
            nested_stripped = nested_line.lstrip()
            if nested_stripped and not nested_stripped.startswith("#"):
                nested_indentation = len(nested_line) - len(nested_stripped)
                if nested_indentation <= indentation:
                    break
            block.append(nested_line)
        return "\n".join(block)
    raise AssertionError(f"missing YAML mapping: {key}")


def _direct_scalar(mapping: str, key: str) -> str:
    """Read one direct scalar child while ignoring comments and nested values."""

    lines = mapping.splitlines()
    root = lines[0]
    root_indentation = len(root) - len(root.lstrip())
    candidate_lines = []
    child_indentation: int | None = None
    for line in lines[1:]:
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        indentation = len(line) - len(stripped)
        if indentation <= root_indentation:
            continue
        if child_indentation is None or indentation < child_indentation:
            child_indentation = indentation
            candidate_lines = [line]
        elif indentation == child_indentation:
            candidate_lines.append(line)

    if child_indentation is None:
        raise AssertionError(f"empty YAML mapping while reading scalar: {key}")

    prefix = f"{key}:"
    matches = [
        line.lstrip()[len(prefix) :].strip()
        for line in candidate_lines
        if line.lstrip().startswith(prefix)
        and line.lstrip()[: len(prefix)] == prefix
    ]
    if len(matches) != 1:
        raise AssertionError(f"expected one direct YAML scalar {key}, found {len(matches)}")

    raw_value = matches[0]
    if not raw_value:
        raise AssertionError(f"YAML key is not a scalar: {key}")
    if raw_value[0] in {'"', "'"} and raw_value[-1:] == raw_value[0]:
        return raw_value[1:-1]
    return raw_value.split(" #", maxsplit=1)[0].rstrip()


def _named_step_run(job: str, step_name: str) -> str:
    """Return the literal run block belonging to one exact workflow step."""

    lines = job.splitlines()
    marker = f"- name: {step_name}"
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("#") or stripped != marker:
            continue
        step_indentation = len(line) - len(stripped)
        step_lines: list[str] = []
        for nested_line in lines[index + 1 :]:
            nested_stripped = nested_line.lstrip()
            if nested_stripped and not nested_stripped.startswith("#"):
                nested_indentation = len(nested_line) - len(nested_stripped)
                if nested_indentation <= step_indentation:
                    break
            step_lines.append(nested_line)

        for run_index, run_line in enumerate(step_lines):
            run_stripped = run_line.lstrip()
            if not run_stripped.startswith("run:"):
                continue
            run_indentation = len(run_line) - len(run_stripped)
            run_value = run_stripped[len("run:") :].strip()
            if run_value not in {"|", "|-", ">", ">-"}:
                raise AssertionError(f"expected block scalar run step: {step_name}")
            body: list[str] = []
            for body_line in step_lines[run_index + 1 :]:
                body_stripped = body_line.lstrip()
                if body_stripped:
                    body_indentation = len(body_line) - len(body_stripped)
                    if body_indentation <= run_indentation:
                        break
                body.append(body_line)
            return "\n".join(body)
        raise AssertionError(f"missing run block for workflow step: {step_name}")
    raise AssertionError(f"missing workflow step: {step_name}")


def test_locale_mapping_evidence_cannot_be_satisfied_by_comments_or_other_scalars() -> None:
    """Comment and unrelated scalar text must not satisfy locale evidence."""

    workflow = """\
jobs:
  pytest:
    services:
      postgres:
        image: wrong-image
        env:
          LANG: C
          POSTGRES_INITDB_ARGS: "--locale=C"
          NOTE: "LANG: en_US.utf8"
          # LANG: en_US.utf8
          # POSTGRES_INITDB_ARGS: "--locale=en_US.utf8"
    steps:
      - name: Verify PostgreSQL locale contract
        run: |
          echo 'select datcollate, datctype from pg_database' >/dev/null
"""
    jobs = _mapping_block(workflow, "jobs")
    job = _mapping_block(jobs, "pytest")
    services = _mapping_block(job, "services")
    postgres = _mapping_block(services, "postgres")
    environment = _mapping_block(postgres, "env")

    assert _direct_scalar(postgres, "image") == "wrong-image"
    assert _direct_scalar(environment, "LANG") == "C"
    assert _direct_scalar(environment, "POSTGRES_INITDB_ARGS") == "--locale=C"


def test_acceptance_workflows_pin_one_debian_postgres_locale_contract() -> None:
    """Both PostgreSQL acceptance lanes must use the same service locale."""

    for workflow_path, job_name in SERVICE_WORKFLOWS:
        workflow = workflow_path.read_text(encoding="utf-8")
        jobs = _mapping_block(workflow, "jobs")
        job = _mapping_block(jobs, job_name)
        services = _mapping_block(job, "services")
        postgres = _mapping_block(services, "postgres")
        environment = _mapping_block(postgres, "env")
        locale_run = _named_step_run(job, "Verify PostgreSQL locale contract")

        assert _direct_scalar(postgres, "image") == POSTGRES_IMAGE
        assert _direct_scalar(environment, "LANG") == "en_US.utf8"
        assert _direct_scalar(environment, "POSTGRES_INITDB_ARGS") == "--locale=en_US.utf8"
        assert "select datcollate, datctype from pg_database" in locale_run
        assert "show lc_collate" not in locale_run
        assert "postgres:16-alpine" not in postgres


def test_product_postgres_image_uses_the_same_debian_locale_contract() -> None:
    """The product database image must not diverge from acceptance PostgreSQL."""

    dockerfile = (
        REPOSITORY_ROOT / "docker/postgres-init/Dockerfile"
    ).read_text(encoding="utf-8")
    assert dockerfile.startswith(f"FROM {POSTGRES_IMAGE}\n")
    assert "ENV LANG=en_US.utf8" in dockerfile
    assert "postgres:16-alpine" not in dockerfile
