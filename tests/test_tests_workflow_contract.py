"""Regression contracts for the repository test workflow."""

from pathlib import Path


def test_pr_close_cancels_obsolete_test_runs_without_starting_jobs() -> None:
    """A close event must cancel the same-PR run while scheduling no test work."""
    workflow = (
        Path(__file__).resolve().parents[1] / ".github/workflows/tests.yml"
    ).read_text(encoding="utf-8")

    assert "types: [opened, synchronize, reopened, closed]" in workflow
    assert "group: tests-${{ github.ref }}" in workflow
    assert "cancel-in-progress: true" in workflow
    assert workflow.count("github.event.action != 'closed'") == 2
