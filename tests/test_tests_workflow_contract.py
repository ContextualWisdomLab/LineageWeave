"""Regression contracts for repository-local workflow concurrency."""

from pathlib import Path


_WORKFLOW_DIRECTORY = Path(__file__).parents[1] / ".github" / "workflows"
_PULL_REQUEST_GROUP = (
    "group: ${{ github.workflow }}-${{ github.repository }}-"
    "${{ github.event_name == 'pull_request' && "
    "github.event.pull_request.number || github.run_id }}"
)
_PULL_REQUEST_CANCELLATION = (
    "cancel-in-progress: ${{ github.event_name == 'pull_request' }}"
)
_PULL_REQUEST_TYPES = (
    "types: [opened, synchronize, reopened, ready_for_review, "
    "converted_to_draft, closed]"
)
_DRAFT_ADMISSION = "github.event.pull_request.draft == false"


def test_pull_request_concurrency_survives_closed_ref_change() -> None:
    """Key synchronize and closed events by PR number so close cancels stale work."""

    workflow = (_WORKFLOW_DIRECTORY / "tests.yml").read_text(encoding="utf-8")

    assert _PULL_REQUEST_TYPES in workflow
    assert workflow.count("github.event.action != 'closed'") == 3


def test_pull_request_workflows_cancel_only_superseded_same_pr_runs() -> None:
    """Scope PR cancellation by workflow, repository, and pull request number."""

    for workflow_path in sorted(_WORKFLOW_DIRECTORY.glob("*.yml")):
        workflow = workflow_path.read_text(encoding="utf-8")
        if "pull_request:" not in workflow:
            continue
        assert _PULL_REQUEST_GROUP in workflow, workflow_path.name
        assert _PULL_REQUEST_CANCELLATION in workflow, workflow_path.name


def test_draft_pull_requests_do_not_consume_repository_local_runners() -> None:
    """Cancel stale draft runs while deferring expensive jobs until review readiness."""

    expected_draft_guards = {
        "tests.yml": 3,
        "prov-o-contract.yml": 1,
        "ontology-pages.yml": 1,
    }
    for workflow_name, expected_guard_count in expected_draft_guards.items():
        workflow = (_WORKFLOW_DIRECTORY / workflow_name).read_text(encoding="utf-8")
        assert _PULL_REQUEST_TYPES in workflow, workflow_name
        assert workflow.count(_DRAFT_ADMISSION) == expected_guard_count, workflow_name


def test_summary_authorization_job_avoids_unrelated_compose_env_file() -> None:
    """Keep three-service acceptance independent of the orchestrator private env."""

    workflow = (_WORKFLOW_DIRECTORY / "tests.yml").read_text(encoding="utf-8")
    summary_job = workflow.split("  summary-authorization-integration:\n", 1)[1]
    summary_job = summary_job.split("\n  frontend:\n", 1)[0]

    assert "COMPOSE_PROJECT_NAME: summary-auth-${{ github.run_id }}" in summary_job
    assert "docker compose up -d --build postgres valkey keycloak" in summary_job
    assert 'label=com.docker.compose.project=${COMPOSE_PROJECT_NAME}' in summary_job
    assert "label=com.docker.compose.service=valkey" in summary_job
    assert "docker compose exec" not in summary_job
    assert "docker compose ps" not in summary_job
    assert "docker compose logs" not in summary_job
    assert "docker compose down" not in summary_job


def test_ontology_publication_runs_are_not_cancelled() -> None:
    """Keep publication runs isolated and non-cancelling outside pull requests."""

    workflow = (_WORKFLOW_DIRECTORY / "ontology-pages.yml").read_text(
        encoding="utf-8"
    )
    assert "github.run_id" in workflow
    assert _PULL_REQUEST_CANCELLATION in workflow
