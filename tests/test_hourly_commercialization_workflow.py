"""Contract tests for the hourly DB-grounded commercialization workflow.

The workflow is security-sensitive production automation. These tests keep its
review-first queue discipline, NVIDIA-only OpenCode execution, test-first
authoring, sandboxed validation, and one-PR mutation boundary visible in code
review instead of relying on prose.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOW_PATH = _ROOT / ".github" / "workflows" / "hourly-commercialization-loop.yml"
_SPEC_PATH = (
    _ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-08-14-db-grounded-product-ux-design.md"
)
_OPERATIONS_PATH = _ROOT / "docs" / "operations" / "hourly-commercialization-loop.md"
_DOCTORING_PATH = _ROOT / "docs" / "doctoring" / "PRODUCT_UX_REFERENCES.md"
_WORKFLOW = _WORKFLOW_PATH.read_text(encoding="utf-8")


def _job_text(job_name: str) -> str:
    """Return one top-level job block from the workflow source."""
    marker = f"  {job_name}:\n"
    start = _WORKFLOW.index(marker)
    match = re.search(r"^  [a-z0-9-]+:\n", _WORKFLOW[start + len(marker) :], re.MULTILINE)
    if match is None:
        return _WORKFLOW[start:]
    return _WORKFLOW[start : start + len(marker) + match.start()]


def _implementation_path_classifiers() -> dict[str, object]:
    """Load the pure path classifiers from the workflow's boundary script."""
    develop = _job_text("develop-next-product-gap")
    boundary = develop.split(
        "      - name: Enforce the autonomous implementation boundary\n", maxsplit=1
    )[1].split(
        "      - name: Validate the proposal in an isolated copy without network\n",
        maxsplit=1,
    )[0]
    match = re.search(
        r"^          def is_frontend_test_path\(.*?(?=^          total_bytes = 0$)",
        boundary,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None, "workflow path classifiers were not found"
    namespace: dict[str, object] = {}
    exec(textwrap.dedent(match.group(0)), namespace)
    return namespace


def test_schedule_runs_hourly_without_cancelling_long_accuracy_work() -> None:
    """The heartbeat is hourly while long OpenCode runs queue instead of being killed."""
    assert '- cron: "23 * * * *"' in _WORKFLOW
    assert "group: lineageweave-hourly-commercialization-loop" in _WORKFLOW
    assert "cancel-in-progress: false" in _WORKFLOW
    assert "timeout-minutes: 180" in _WORKFLOW


def test_review_fix_check_merge_loop_precedes_new_development() -> None:
    """Every run inspects, repairs, and revalidates PRs before opening new work."""
    assert _WORKFLOW.index("  inspect-pr-queue:") < _WORKFLOW.index(
        "  repair-review-feedback:"
    )
    assert _WORKFLOW.index("  repair-review-feedback:") < _WORKFLOW.index(
        "  revalidate-pr-queue:"
    )
    assert _WORKFLOW.index("  revalidate-pr-queue:") < _WORKFLOW.index(
        "  develop-next-product-gap:"
    )
    develop = _job_text("develop-next-product-gap")
    assert "needs: [inspect-pr-queue, repair-review-feedback, revalidate-pr-queue]" in develop
    assert "open_pr_count" in develop
    assert "An open pull request owns the queue" in develop


def test_central_review_and_repair_workflows_are_immutable_pins() -> None:
    """Reusable governance workflows must use exact commits, never moving refs."""
    expected = (
        "ContextualWisdomLab/.github/.github/workflows/"
        "pr-review-merge-scheduler.yml@"
        "6eb06cdd08c79a06f7b390069d4ffa49e2eb7dba"
    )
    repair = (
        "ContextualWisdomLab/.github/.github/workflows/"
        "pr-review-fix-scheduler.yml@"
        "6eb06cdd08c79a06f7b390069d4ffa49e2eb7dba"
    )
    assert _WORKFLOW.count(expected) == 2
    assert repair in _WORKFLOW
    assert "@main" not in "\n".join(
        line for line in _WORKFLOW.splitlines() if "uses: ContextualWisdomLab/.github" in line
    )


def test_scheduler_is_configured_to_exhaust_the_pr_queue() -> None:
    """Review and branch-update budgets do not strand additional eligible PRs."""
    assert _WORKFLOW.count('review_dispatch_limit: "-1"') == 2
    assert _WORKFLOW.count('branch_update_limit: "-1"') == 2
    assert _WORKFLOW.count("merge_mode: direct_or_auto") == 2
    assert _WORKFLOW.count("enable_auto_merge: true") == 2
    assert 'max_dispatches: "50"' in _WORKFLOW


def test_product_agent_uses_only_nvidia_nim_and_pinned_opencode() -> None:
    """No Copilot token or unverified OpenCode binary may enter the product loop."""
    assert "NVIDIA_NIM_API_KEY" in _WORKFLOW
    assert "NVIDIA_API_KEY" in _WORKFLOW
    assert "COPILOT_GITHUB_TOKEN" not in _WORKFLOW
    assert 'OPENCODE_VERSION: "1.17.13"' in _WORKFLOW
    assert (
        "OPENCODE_SHA256: "
        "157afa289d1a8d9372de0ce19ac726119b937a1f6b201808d46f06e4e59bb348"
        in _WORKFLOW
    )
    assert "sha256sum -c -" in _WORKFLOW
    assert "enabled_providers" in _WORKFLOW
    assert '["nvidia"]' in _WORKFLOW


def test_agent_never_receives_github_or_oidc_credentials() -> None:
    """Both OpenCode phases explicitly remove write-authority environment values."""
    assert _WORKFLOW.count("env -u GH_TOKEN -u GITHUB_TOKEN") == 2
    assert _WORKFLOW.count(
        "-u ACTIONS_ID_TOKEN_REQUEST_TOKEN -u ACTIONS_ID_TOKEN_REQUEST_URL"
    ) == 2
    assert _WORKFLOW.index("Recheck queue and base before acquiring write authority") < (
        _WORKFLOW.index("Exchange an OpenCode app token for the generated PR")
    )


def test_agent_permissions_are_test_first_and_deny_shell_or_web() -> None:
    """The red phase can author evidence only; neither phase can execute tools."""
    assert '"*": "deny"' in _WORKFLOW
    assert '"tests/**": "allow"' in _WORKFLOW
    assert '"backend/tests/**": "allow"' in _WORKFLOW
    assert '"frontend/src/**/*.test.tsx": "allow"' in _WORKFLOW
    assert _WORKFLOW.count('"bash": "deny"') == 2
    assert _WORKFLOW.count('"webfetch": "deny"') == 2
    assert _WORKFLOW.count('"websearch": "deny"') == 2
    assert _WORKFLOW.count('"question": "deny"') == 2


def test_red_state_requires_real_failing_tests_and_a_design_supplement() -> None:
    """A prose-only or already-green proposal cannot advance to implementation."""
    assert "red phase did not add or modify a regression test" in _WORKFLOW
    assert "red phase did not write a design supplement" in _WORKFLOW
    assert "The red phase did not produce a failing regression" in _WORKFLOW
    assert ".agent-python-red-output.txt" in _WORKFLOW
    assert ".agent-frontend-red-output.txt" in _WORKFLOW
    assert "AUTOMATION_RED_SHA" in _WORKFLOW


def test_virtual_environment_path_is_exported_from_step_scope() -> None:
    """Runner-scoped paths are expanded in a step before later commands consume them."""
    develop = _job_text("develop-next-product-gap")
    env_block = develop.split("    steps:\n", maxsplit=1)[0]
    assert "runner.temp" not in env_block
    setup_step = """      - name: Pin the project virtual environment path
        if: steps.gate.outputs.eligible == 'true'
        run: |
          set -euo pipefail
          echo "UV_PROJECT_ENVIRONMENT=${RUNNER_TEMP}/lineageweave-venv" >>"$GITHUB_ENV"
"""
    assert setup_step in develop
    assert develop.index("Set up locked Python dependency manager") < develop.index(
        "Pin the project virtual environment path"
    ) < develop.index("Install the committed dependency locks")


def test_implementation_preserves_governance_and_db_grounded_boundaries() -> None:
    """Protected policy files and unsupported product claims remain out of scope."""
    develop = _job_text("develop-next-product-gap")
    for protected in (
        '".github/**": "deny"',
        '"AGENTS.md": "deny"',
        '"CLAUDE.md": "deny"',
        '"CODEOWNERS": "deny"',
        '"SECURITY.md": "deny"',
    ):
        assert protected in develop
    assert "account affiliations separate from global role" in develop
    assert "AUTO-*" in develop
    assert "access assignment" in develop
    assert "standards-complete PROV-O separate from the compact" in develop
    assert "Do not add unsupported" in develop


def test_every_increment_requires_production_tests_spec_and_changelog() -> None:
    """One bounded PR must contain the complete buyer-visible vertical slice."""
    assert "buyer-visible increment must change production code or schema" in _WORKFLOW
    assert "autonomous increment must include regression tests" in _WORKFLOW
    assert "autonomous increment must include a design supplement" in _WORKFLOW
    assert "autonomous increment must include a changelog fragment" in _WORKFLOW
    assert "implementation must write PR_MESSAGE.md" in _WORKFLOW


def test_frontend_test_only_diff_does_not_satisfy_production_gate() -> None:
    """Regression files count as evidence but never as buyer-visible product code."""
    classifiers = _implementation_path_classifiers()
    is_production_path = classifiers["is_production_path"]
    is_test_path = classifiers["is_test_path"]
    assert callable(is_production_path)
    assert callable(is_test_path)

    assert is_test_path("frontend/src/App.test.tsx") is True
    assert is_test_path("frontend/src/lineageLayout.test.ts") is True
    assert is_production_path("frontend/src/App.test.tsx") is False
    assert is_production_path("frontend/src/lineageLayout.test.ts") is False

    assert is_production_path("frontend/src/App.tsx") is True
    assert is_production_path("frontend/src/App.css") is True
    assert is_production_path("backend/app/main.py") is True
    assert is_production_path("lineageweave/reconstruct.py") is True
    assert is_production_path("migrations/0001_initial_schema.sql") is True
    assert is_production_path("docs/architecture-note.md") is False


def test_untrusted_validation_is_networkless_unprivileged_and_complete() -> None:
    """The proposal is tested in a disposable copy without inherited credentials."""
    assert "cp -a \"$GITHUB_WORKSPACE/.\" \"$validation_workspace/\"" in _WORKFLOW
    assert 'rm -rf "$validation_workspace/.git"' in _WORKFLOW
    assert "sudo unshare --net --pid --fork --mount-proc" in _WORKFLOW
    assert "--no-new-privs" in _WORKFLOW
    assert "--bounding-set=-all" in _WORKFLOW
    assert "env -i" in _WORKFLOW
    for command in (
        "uv run --frozen python -m pytest -q",
        "uv run --frozen python -m compileall -q lineageweave backend tests",
        "pnpm --dir frontend run lint",
        "pnpm --dir frontend run test",
        "pnpm --dir frontend run build",
    ):
        assert command in _WORKFLOW


def test_networkless_validation_keeps_real_service_evidence_in_exact_head_ci() -> None:
    """Operations guidance must distinguish sandbox skips from real-service CI."""
    operations = _OPERATIONS_PATH.read_text(encoding="utf-8")
    assert "module-level availability probes" in operations
    assert "pytest.mark.skipif" in operations
    assert "they skip rather than error" in operations
    assert "ordinary exact-head pull-request checks" in operations


def test_mutation_rechecks_single_writer_and_base_freshness() -> None:
    """A concurrent PR or moved main branch discards stale autonomous work."""
    assert _WORKFLOW.count(
        'gh api "/repos/${TARGET_REPOSITORY}/pulls?state=open&per_page=1"'
    ) >= 3
    assert _WORKFLOW.count(
        'gh api "/repos/${TARGET_REPOSITORY}/commits/${BASE_BRANCH}"'
    ) >= 2
    assert "Another pull request acquired the queue; discarding this proposal." in _WORKFLOW
    assert "The base branch moved during authoring; discarding this stale proposal." in _WORKFLOW


def test_agent_cannot_approve_merge_or_release() -> None:
    """The product job opens one PR and delegates all review and merge authority."""
    develop = _job_text("develop-next-product-gap")
    assert "gh pr create" in develop
    assert "gh pr merge" not in develop
    assert "gh pr review --approve" not in develop
    assert "gh release create" not in develop
    assert "Do not commit, push" in develop
    assert "approve, merge, publish, or release" in develop


def test_canonical_product_and_operations_documents_exist() -> None:
    """Automation must stay bound to the reviewed product and operations contracts."""
    assert _SPEC_PATH.is_file()
    assert _OPERATIONS_PATH.is_file()
    assert _DOCTORING_PATH.is_file()
    assert str(_SPEC_PATH.relative_to(_ROOT)) in _WORKFLOW
    spec = _SPEC_PATH.read_text(encoding="utf-8")
    operations = _OPERATIONS_PATH.read_text(encoding="utf-8")
    assert "DB cardinality is the interaction contract" in spec
    assert "process_unit |o--o{ account_affiliation : narrows" in spec
    assert "process_unit o|--o{ account_affiliation : narrows" not in spec
    assert "Archive — superseded drafts" in spec
    assert "UpjgFQEu4u2Kr2hmyorAqe" in spec
    assert "uv run --frozen python -m compileall -q lineageweave backend tests" in operations
