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
_INACTIVE_ADMISSION = (
    "github.event.action != 'closed' && github.event.pull_request.draft == false"
)


def test_lifecycle_events_cancel_inactive_pr_work() -> None:
    """Keep lifecycle events so Draft/close transitions cancel active local work."""

    expected_inactive_guards = {
        "tests.yml": 2,
        "prov-o-contract.yml": 1,
        "ontology-pages.yml": 1,
    }
    for workflow_name, expected_guard_count in expected_inactive_guards.items():
        workflow = (_WORKFLOW_DIRECTORY / workflow_name).read_text(encoding="utf-8")
        assert _PULL_REQUEST_TYPES in workflow, workflow_name
        assert workflow.count(_INACTIVE_ADMISSION) == expected_guard_count, workflow_name


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
        "tests.yml": 2,
        "prov-o-contract.yml": 1,
        "ontology-pages.yml": 1,
    }
    for workflow_name, expected_guard_count in expected_draft_guards.items():
        workflow = (_WORKFLOW_DIRECTORY / workflow_name).read_text(encoding="utf-8")
        assert _PULL_REQUEST_TYPES in workflow, workflow_name
        assert workflow.count(_DRAFT_ADMISSION) == expected_guard_count, workflow_name


def test_ontology_publication_runs_are_not_cancelled() -> None:
    """Keep publication runs isolated and non-cancelling outside pull requests."""

    workflow = (_WORKFLOW_DIRECTORY / "ontology-pages.yml").read_text(
        encoding="utf-8"
    )
    assert "github.run_id" in workflow
    assert _PULL_REQUEST_CANCELLATION in workflow
