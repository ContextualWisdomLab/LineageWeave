#!/usr/bin/env python3
"""Migrate active contextual-orchestrator consumers from route to auto."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BRANCH = "agent/adaptive-orchestrator-default"
ACTIVE_CLIENTS = (
    "lineageweave/post_summary.py",
    "lineageweave/post_evaluation.py",
    "lineageweave/keyman_extraction.py",
    "lineageweave/commitment_extraction.py",
    "lineageweave/post_chat.py",
    "lineageweave/entity_relationship_classification.py",
)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    """Replace exactly one expected repository fragment."""
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    """Patch code and add policy evidence."""
    branch = os.environ.get("GITHUB_REF_NAME", EXPECTED_BRANCH)
    if branch != EXPECTED_BRANCH:
        raise RuntimeError(f"refusing to mutate unexpected branch: {branch}")

    for relative in ACTIVE_CLIENTS:
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        original = text
        text = text.replace('"mode": "route"', '"mode": "auto"')
        text = text.replace('mode="route"', 'mode="auto"')
        text = text.replace('mode: str = "route"', 'mode: str = "auto"')
        if text == original:
            raise RuntimeError(f"{relative}: expected a route default to migrate")
        path.write_text(text, encoding="utf-8")

    keyman_path = ROOT / "lineageweave" / "keyman_extraction.py"
    keyman = keyman_path.read_text(encoding="utf-8")
    keyman = replace_once(
        keyman,
        '''that benefits from the orchestrator's reasoning-effort allocation, not a
single confidence number, so it uses ``mode="auto"`` (one worker call) at
a ``"medium"`` reasoning effort by default rather than ``verify``'s
worker-plus-checker pattern, which is reserved for adjudication's binary
judgment calls.
''',
        '''that benefits from the orchestrator's task-sensitive allocation of model,
reasoning effort, and workflow depth. It therefore uses ``mode="auto"`` at
a ``"medium"`` reasoning effort by default; contextual-orchestrator may use
a single worker or escalate to verification/conducted work when the detected
quality requirement justifies the additional cost.
''',
        "keyman policy explanation",
    )
    keyman_path.write_text(keyman, encoding="utf-8")

    changelog_path = ROOT / "CHANGELOG.md"
    changelog = changelog_path.read_text(encoding="utf-8")
    changelog = replace_once(
        changelog,
        "## [0.71.0] - 2026-08-14\n",
        "## [Unreleased]\n\n### Changed\n\n"
        "- Active contextual-orchestrator clients now request `mode=\"auto\"` rather than forcing a one-model route. The orchestrator owns the minimum-cost route, verification, or conducted workflow that satisfies the detected quality requirement; explicit modes remain available for controlled experiments and operator overrides.\n\n"
        "## [0.71.0] - 2026-08-14\n",
        "changelog",
    )
    changelog_path.write_text(changelog, encoding="utf-8")

    test_path = ROOT / "tests" / "test_contextual_orchestrator_default_policy.py"
    if test_path.exists():
        raise RuntimeError(f"refusing to replace existing policy test: {test_path}")
    test_path.write_text(POLICY_TEST, encoding="utf-8")

    adr_path = ROOT / "docs" / "adr" / "0005-adaptive-orchestrator-default.md"
    if adr_path.exists():
        raise RuntimeError(f"refusing to replace existing ADR: {adr_path}")
    adr_path.write_text(ADR, encoding="utf-8")


POLICY_TEST = '''"""Contract tests for adaptive contextual-orchestrator consumer defaults."""
from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_CLIENTS = (
    "lineageweave/post_summary.py",
    "lineageweave/post_evaluation.py",
    "lineageweave/keyman_extraction.py",
    "lineageweave/commitment_extraction.py",
    "lineageweave/post_chat.py",
    "lineageweave/entity_relationship_classification.py",
)


class AdaptiveOrchestratorDefaultTest(unittest.TestCase):
    """Protect production clients from regressing to forced one-model routing."""

    def test_active_clients_use_auto_and_never_force_route(self) -> None:
        for relative in ACTIVE_CLIENTS:
            source = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(path=relative):
                self.assertNotIn('"mode": "route"', source)
                self.assertNotIn('mode="route"', source)
                self.assertNotIn('mode: str = "route"', source)
                self.assertTrue(
                    '"mode": "auto"' in source
                    or 'mode="auto"' in source
                    or 'mode: str = "auto"' in source
                )

    def test_high_stakes_adjudication_retains_explicit_checked_override(self) -> None:
        source = (ROOT / "lineageweave/adjudication_client.py").read_text(encoding="utf-8")
        self.assertIn('"mode": "verify"', source)


if __name__ == "__main__":
    unittest.main()
'''

ADR = '''# ADR-0005: Adaptive contextual-orchestrator mode is the consumer default

- Status: Accepted
- Date: 2026-08-15

## Context

LineageWeave previously forced `mode="route"` in summarization, post evaluation,
Keyman extraction, commitment extraction, post chat, and relationship
classification. That made the consumer choose a single model before
contextual-orchestrator could evaluate task difficulty, capability fit,
verification need, and known model price.

Research on adaptive orchestration and cost-aware reliability shows that no fixed
model/workflow/budget choice dominates for all requests. Dynamic scaffolding and
query-level cost allocation are therefore responsibilities of the orchestration
plane, not of each domain client.

## Decision

Active general-purpose clients request `mode="auto"`.

- contextual-orchestrator selects the quality-sufficient route, bounded
  verification, or conducted workflow and then minimizes known cost inside the
  selected capability tier;
- LineageWeave continues to own prompts, schemas, strict parsing, domain evidence,
  and failure semantics;
- the low-volume lineage adjudication channel retains the explicit `verify`
  override because an independently checked verdict is part of that domain
  contract, not an accidental routing default;
- explicit modes remain permitted for ablation, regression comparison, and
  emergency operator policy, but they are not ordinary production defaults.

## Consequences

Trace width is no longer a stable consumer assumption for `auto` requests.
Telemetry and tests must record the requested policy and actual trace. Cost
claims require configured price evidence; an unpriced model is never treated as
free.

## References

Omidvar, H., & Akhlaghi, V. (2026). *A communication-theoretic framework for LLM agents: Cost-aware adaptive reliability* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2605.09121

Tang, Y., Cetin, E., Xu, J., Sun, Q., Nielsen, S., Richard, V., Goda, H., Tymchenko, I., Nguyen, N., Lee, H., Ashiga, M., Kotyan, S., Kuroki, S., & Clanuwat, T. (2026). *Sakana Fugu technical report* [Technical report]. arXiv. https://doi.org/10.48550/arXiv.2606.21228
'''

if __name__ == "__main__":
    main()
