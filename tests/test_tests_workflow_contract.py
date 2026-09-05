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
    "types: [opened, synchronize, reopened, ready_for_review]"
)
_DRAFT_ADMISSION = "github.event.pull_request.draft == false"


def test_product_workflows_do_not_create_inactive_pr_runs() -> None:
    """Leave draft and closed lifecycle cleanup to the central workflow."""

    workflow = (_WORKFLOW_DIRECTORY / "tests.yml").read_text(encoding="utf-8")

    assert _PULL_REQUEST_TYPES in workflow
    assert "converted_to_draft" not in workflow
    assert "github.event.action != 'closed'" not in workflow


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
