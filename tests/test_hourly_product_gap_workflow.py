"""Contract tests for the isolated hourly product-gap proposal workflow."""

from __future__ import annotations

import re
from pathlib import Path


WORKFLOW = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "hourly-product-gap.yml"
)
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def test_hourly_workflow_has_a_bounded_nim_proposal_and_separate_verifier() -> None:
    """Keep model credentials, proposal artifacts, and verification separate."""

    text = WORKFLOW.read_text(encoding="utf-8")
    assert 'cron: "17 * * * *"' in text
    assert "NVIDIA_NIM_API_KEY" in text
    assert "opencode run" in text
    assert "env -u GH_TOKEN" in text
    assert "actions/upload-artifact@" in text
    assert "actions/download-artifact@" in text
    assert "uv run --frozen pytest -q" in text
    assert "npm run coverage --prefix web" in text
    assert "npm run build --prefix web" in text
    assert "gh pr create" in text
    assert "gh pr merge" not in text
    assert "COPILOT_GITHUB_TOKEN" not in text


def test_hourly_workflow_pins_every_external_action() -> None:
    """Reject mutable GitHub Action references in the scheduled workflow."""

    text = WORKFLOW.read_text(encoding="utf-8")
    references = re.findall(r"uses:\s*[^\s@]+@([0-9a-f]+)", text)
    assert references
    assert all(FULL_SHA.fullmatch(reference) for reference in references)


def test_hourly_workflow_has_fail_closed_queue_and_patch_limits() -> None:
    """Keep queue races and oversized model patches outside publication."""

    text = WORKFLOW.read_text(encoding="utf-8")
    for marker in (
        "pull_request_inventory_unavailable",
        "open_pull_request",
        "nim_api_key_unavailable",
        "MAX_CHANGED_FILES",
        "MAX_DIFF_BYTES",
        "git diff --cached --check",
        "git diff --cached --raw",
        "The hourly scheduler is not self-modifiable",
        "The model credential appears in the proposed patch",
        "BASE_SHA",
        "git rev-parse FETCH_HEAD",
    ):
        assert marker in text


def test_workflow_python_bootstrap_is_hash_pinned() -> None:
    """Keep CI bootstrap packages pinned to the known Linux wheel digest."""
    root = WORKFLOW.parents[2]
    expected = "--hash=sha256:cbff74f884846d794713670faf8abe10db3bd70c43b01e63223f74eb7d958689"
    for relative_path in (".github/workflows/hourly-product-gap.yml", ".github/workflows/tests.yml"):
        text = (root / relative_path).read_text(encoding="utf-8")
        assert "--require-hashes" in text
        assert expected in text
