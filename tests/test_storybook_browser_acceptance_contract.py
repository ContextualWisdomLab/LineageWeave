"""Executable contract for buyer-visible Storybook interaction evidence."""

from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_PACKAGE = REPOSITORY_ROOT / "frontend" / "package.json"
TESTS_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "tests.yml"


def test_frontend_ci_executes_storybook_browser_interactions() -> None:
    """The hosted frontend lane must execute, not merely build, material UI stories."""
    package = json.loads(FRONTEND_PACKAGE.read_text(encoding="utf-8"))
    assert package["scripts"].get("test:storybook:browser") == (
        "playwright test --config playwright.storybook.config.ts"
    )

    workflow = TESTS_WORKFLOW.read_text(encoding="utf-8")
    build_command = "pnpm run build-storybook"
    browser_command = "pnpm run test:storybook:browser"
    assert build_command in workflow
    assert browser_command in workflow
    assert workflow.index(build_command) < workflow.index(browser_command)
