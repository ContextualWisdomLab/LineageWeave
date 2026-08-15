"""Deterministically remove the competing PR writer from LineageWeave PR 76."""

from __future__ import annotations

from pathlib import Path


def repair_workflow() -> None:
    """Retain the product-gap generator while delegating PR governance centrally."""
    path = Path(".github/workflows/hourly-commercialization-loop.yml")
    content = path.read_text(encoding="utf-8")
    content = content.replace(
        "name: Hourly LineageWeave Commercialization Loop",
        "name: Hourly LineageWeave Product Gap Loop",
        1,
    ).replace(
        "group: lineageweave-hourly-commercialization-loop",
        "group: lineageweave-hourly-product-gap-loop",
        1,
    )
    jobs_start = content.index("jobs:\n  inspect-pr-queue:")
    product_start = content.index("  develop-next-product-gap:", jobs_start)
    content = content[:jobs_start] + "jobs:\n" + content[product_start:]
    product_start = content.index("  develop-next-product-gap:")
    runs_on_start = content.index("    runs-on: ubuntu-24.04", product_start)
    content = (
        content[:product_start]
        + "  develop-next-product-gap:\n"
        + content[runs_on_start:]
    )
    old_message = (
        "An open pull request owns the queue; review, repair, checks, "
        "and merge stay ahead of new development."
    )
    new_message = (
        "Central governance owns every open pull request; product development "
        "remains read-only and waits for the queue to reach zero."
    )
    if old_message not in content:
        raise SystemExit("missing queue-owner message")
    content = content.replace(old_message, new_message, 1)
    content = content.replace(
        "python -m compileall -q lineageweave backend tests",
        "uv run --frozen python -m compileall -q lineageweave backend tests",
        1,
    )
    forbidden = (
        "pr-review-merge-scheduler.yml",
        "pr-review-fix-scheduler.yml",
        "pull-requests: write",
        "actions: write",
        "merge_mode:",
        "enable_auto_merge:",
    )
    for marker in forbidden:
        if marker in content:
            raise SystemExit(f"competing PR-governance marker remains: {marker}")
    path.write_text(content, encoding="utf-8")


def repair_operations() -> None:
    """Describe the central scheduler as the only PR governance writer."""
    path = Path("docs/operations/hourly-commercialization-loop.md")
    content = path.read_text(encoding="utf-8")
    start = content.index("## Purpose\n")
    cadence = content.index("## Accuracy-first cadence\n")
    replacement = (
        "## Purpose\n\n"
        "The hourly repository workflow turns the approved DB-grounded Figma design into\n"
        "one protected product increment only when the live LineageWeave pull-request\n"
        "queue is empty. It never reviews, repairs, updates, approves, or merges an\n"
        "existing pull request.\n\n"
        "The workflow file is\n"
        "`.github/workflows/hourly-commercialization-loop.yml`. It runs at minute 23 of\n"
        "every hour and can also be invoked manually.\n\n"
        "## Central governance and queue policy\n\n"
        "The central `.github` scheduler is the only PR review, repair, branch-update, and merge writer.\n"
        "It runs the organization-wide sweep every 15 minutes and reacts to PR, review,\n"
        "and required-workflow events. LineageWeave does not install a second merger or\n"
        "call the central reusable writer from its own schedule.\n\n"
        "```mermaid\n"
        "flowchart TD\n"
        "    A[Hourly product trigger] --> B[Read live open-PR count]\n"
        "    B --> C{Any open PR?}\n"
        "    C -->|yes| D[Exit without mutating the queue]\n"
        "    C -->|no| E[Select one buyer-visible DB-grounded gap]\n"
        "    E --> F[Write design supplement and failing test]\n"
        "    F --> G[Implement one vertical slice]\n"
        "    G --> H[Validate in isolated copy without network]\n"
        "    H --> I{Queue and main unchanged?}\n"
        "    I -->|no| J[Discard stale proposal]\n"
        "    I -->|yes| K[Open exactly one PR]\n"
        "    K --> L[Central governance reviews and merges]\n"
        "```\n\n"
        "The repository workflow receives only read access to pull-request inventory.\n"
        "After validation and repeated queue/base checks, it may exchange the existing\n"
        "OIDC credential for a short-lived app token that pushes one generated branch\n"
        "and opens one PR. It cannot approve, update, or merge that PR.\n\n"
    )
    content = content[:start] + replacement + content[cadence:]
    content = content.replace(
        "The product job has a 180-minute budget. It starts only after all three queue\n"
        "jobs succeed and no open pull request remains.",
        "The product job has a 180-minute budget. It starts only when read-only live\n"
        "inspection finds no open pull request; central governance continues independently.",
        1,
    )
    content = content.replace(
        "Review wait time is not a blocker. Subsequent hourly invocations continue\n"
        "repairing and revalidating the queue but do not create another product PR.",
        "Review wait time is not a blocker. The central scheduler continues reviewing,\n"
        "repairing, and revalidating the queue; the repository heartbeat exits without\n"
        "creating another product PR while any pull request remains open.",
        1,
    )
    old_evidence = (
        "The permanent contract tests in\n"
        "`tests/test_hourly_commercialization_workflow.py` verify the schedule,\n"
        "governance pins, NVIDIA-only model path, credential removal, red/green\n"
        "discipline, protected paths, isolated validation, stale-work checks, and\n"
        "one-PR/no-self-merge boundary.\n\n"
        "The central scheduler remains independently active. This repository workflow\n"
        "adds a LineageWeave-specific hourly heartbeat and product-gap generator; it\n"
        "does not duplicate the central scheduler's implementation."
    )
    new_evidence = (
        "The permanent contract tests in\n"
        "`tests/test_hourly_commercialization_workflow.py` verify the schedule, central\n"
        "single-writer boundary, read-only live queue gate, NVIDIA-only model path,\n"
        "credential removal, red/green discipline, protected paths, isolated\n"
        "validation, stale-work checks, and one-PR/no-self-merge boundary.\n\n"
        "The central scheduler remains independently active every 15 minutes. This\n"
        "repository workflow contributes only the LineageWeave product-gap heartbeat."
    )
    if old_evidence not in content:
        raise SystemExit("missing operations evidence anchor")
    path.write_text(content.replace(old_evidence, new_evidence, 1), encoding="utf-8")


def repair_changelog() -> None:
    """Record the central single-writer and read-only queue boundary."""
    path = Path("CHANGELOG.d/hourly-db-grounded-commercialization-loop.md")
    content = path.read_text(encoding="utf-8")
    content = content.replace(
        "- An hourly, review-first commercialization workflow now drains open pull\n"
        "  requests through current-head review, feedback repair, check revalidation,\n"
        "  branch refresh, and protected merge before creating more work.",
        "- An hourly product-gap workflow now reads the live pull-request queue and\n"
        "  exits without mutation whenever an open PR exists. The organization-central\n"
        "  scheduler remains the only review, repair, branch-update, and merge writer.",
        1,
    )
    content = content.replace(
        "- Permanent workflow-contract tests bind the schedule, immutable central\n"
        "  governance references, credential removal, no-Copilot rule, test-first\n"
        "  evidence, protected paths, stale-work checks, and no-self-merge boundary.",
        "- Permanent workflow-contract tests bind the hourly schedule, central\n"
        "  single-writer boundary, read-only queue gate, credential removal,\n"
        "  no-Copilot rule, test-first evidence, protected paths, stale-work checks,\n"
        "  and no-self-merge boundary.",
        1,
    )
    path.write_text(content, encoding="utf-8")


def main() -> None:
    """Apply every deterministic governance repair."""
    repair_workflow()
    repair_operations()
    repair_changelog()


if __name__ == "__main__":
    main()
