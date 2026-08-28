"""Regression contracts for the repository-local test workflow."""

from pathlib import Path


_WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "tests.yml"


def test_pull_request_concurrency_survives_closed_ref_change() -> None:
    """Key synchronize and closed events by PR number so close cancels stale work."""

    workflow = _WORKFLOW.read_text(encoding="utf-8")

    assert "types: [opened, synchronize, reopened, closed]" in workflow
    assert "group: tests-${{ github.event.pull_request.number || github.ref }}" in workflow
    assert "cancel-in-progress: true" in workflow
    assert workflow.count("github.event.action != 'closed'") == 2
