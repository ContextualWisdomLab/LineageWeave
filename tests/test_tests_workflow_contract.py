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


def test_pull_request_concurrency_survives_closed_ref_change() -> None:
    """Key synchronize and closed events by PR number so close cancels stale work."""

    workflow = (_WORKFLOW_DIRECTORY / "tests.yml").read_text(encoding="utf-8")

    assert "types: [opened, synchronize, reopened, closed]" in workflow
    assert workflow.count("github.event.action != 'closed'") == 2


def test_pull_request_workflows_cancel_only_superseded_same_pr_runs() -> None:
    """Scope PR cancellation by workflow, repository, and pull request number."""

    for workflow_path in sorted(_WORKFLOW_DIRECTORY.glob("*.yml")):
        workflow = workflow_path.read_text(encoding="utf-8")
        if "pull_request:" not in workflow:
            continue
        assert _PULL_REQUEST_GROUP in workflow, workflow_path.name
        assert _PULL_REQUEST_CANCELLATION in workflow, workflow_path.name


def test_ontology_publication_runs_are_not_cancelled() -> None:
    """Keep publication runs isolated and non-cancelling outside pull requests."""

    workflow = (_WORKFLOW_DIRECTORY / "ontology-pages.yml").read_text(
        encoding="utf-8"
    )
    assert "github.run_id" in workflow
    assert _PULL_REQUEST_CANCELLATION in workflow
