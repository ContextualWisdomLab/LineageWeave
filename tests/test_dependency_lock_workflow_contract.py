"""Regression contract for reproducible lockfile verification in hosted tests."""

from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "tests.yml"


def test_tests_workflow_fails_closed_on_stale_universal_lock() -> None:
    """A stale uv.lock must fail before frozen install while preserving the resolver candidate."""

    workflow = WORKFLOW.read_text(encoding="utf-8")

    verify = workflow.index("- name: Verify committed universal lock")
    preserve = workflow.index("- name: Preserve resolver-generated lock candidate")
    install = workflow.index("- name: Install the committed universal lock")

    assert verify < preserve < install
    assert "if uv lock --check; then" in workflow
    assert "uv lock\n" in workflow
    assert "if: failure() && steps.lock.outputs.stale == 'true'" in workflow
    assert "name: uv-lock-candidate-${{ github.sha }}" in workflow
    assert "retention-days: 1" in workflow
