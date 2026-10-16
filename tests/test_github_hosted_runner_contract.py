"""Repository-owned Linux workflows use an explicit supported hosted image."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_JOB_COUNTS = {
    ROOT / ".github" / "workflows" / "tests.yml": 2,
    ROOT / ".github" / "workflows" / "ontology-pages.yml": 2,
    ROOT / ".github" / "workflows" / "prov-o-contract.yml": 1,
}


def _job_level_runners(path: Path) -> dict[str, str]:
    """Return literal ``jobs.<job>.runs-on`` declarations from one workflow.

    GitHub workflow job keys are two spaces below the top-level ``jobs`` map and
    their scalar ``runs-on`` declarations are four spaces below it. Restricting
    extraction to those structural levels prevents comments, shell heredocs, and
    unrelated strings from satisfying this repository contract without adding a
    YAML parser solely for a CI-policy test.
    """
    runners: dict[str, str] = {}
    current_job: str | None = None
    in_jobs = False

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if raw_line == "jobs:":
            in_jobs = True
            current_job = None
            continue
        if not in_jobs:
            continue
        if raw_line and not raw_line.startswith(" ") and not raw_line.startswith("#"):
            break
        if raw_line.startswith("  ") and not raw_line.startswith("    "):
            stripped = raw_line.strip()
            if stripped and not stripped.startswith("#") and stripped.endswith(":"):
                current_job = stripped[:-1]
            continue
        if current_job is not None and raw_line.startswith("    runs-on:"):
            value = raw_line.split(":", 1)[1].split("#", 1)[0].strip().strip("'\"")
            runners[current_job] = value

    return runners


def test_repository_workflows_pin_ubuntu_2404() -> None:
    """Require every actual repository-owned Linux job to pin Ubuntu 24.04."""
    for path, expected_count in EXPECTED_JOB_COUNTS.items():
        runners = _job_level_runners(path)
        assert len(runners) == expected_count, (path, runners)
        assert set(runners.values()) == {"ubuntu-24.04"}, (path, runners)
