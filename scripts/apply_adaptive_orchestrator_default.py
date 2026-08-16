#!/usr/bin/env python3
"""Replace product-default single-route calls with contextual-orchestrator auto."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "lineageweave"
ADR_PATH = ROOT / "docs" / "adr" / "0005-adaptive-contextual-orchestrator-default.md"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"

replacements = {
    '"mode": "route"': '"mode": "auto"',
    "'mode': 'route'": "'mode': 'auto'",
    'mode="route"': 'mode="auto"',
    "mode='route'": "mode='auto'",
    'mode: str = "route"': 'mode: str = "auto"',
    "mode: str = 'route'": "mode: str = 'auto'",
    'with ``mode="route"``': 'with ``mode="auto"``',
    'uses ``mode="route"``': 'uses ``mode="auto"``',
}

changed_files: list[Path] = []
for path in sorted(PACKAGE_ROOT.glob("*.py")):
    text = path.read_text(encoding="utf-8")
    updated = text
    for old, new in replacements.items():
        updated = updated.replace(old, new)
    if updated != text:
        path.write_text(updated, encoding="utf-8")
        changed_files.append(path)

if not changed_files:
    # Idempotent continuation is allowed only when the desired source state is
    # already present. The permanent regression independently proves it.
    remaining = []
    for path in sorted(PACKAGE_ROOT.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for legacy in replacements:
            if legacy in text:
                remaining.append(f"{path}:{legacy}")
    if remaining:
        raise RuntimeError("legacy route defaults remain: " + ", ".join(remaining))

ADR_PATH.parent.mkdir(parents=True, exist_ok=True)
if not ADR_PATH.exists():
    ADR_PATH.write_text(
        '''# ADR-0005: Product LLM clients delegate default execution to contextual-orchestrator auto

- Status: Accepted
- Date: 2026-08-16

## Context

LineageWeave had several independent feature adapters for summarization, Keyman
extraction, relationship classification, commitments, chat, and post evaluation.
Each adapter hard-coded `route`, which duplicated policy and forced a single worker
regardless of uncertainty, risk, or task complexity. Adjudication separately uses
`verify` because it is an explicit controlled worker-plus-checker contract.

## Decision

Every production adapter that does not intentionally implement a controlled
ablation sends `mode="auto"`. Contextual-orchestrator owns model/provider selection,
reasoning effort, verification depth, failover, and the quality-first/cost-aware
execution tier. The explicit adjudication `verify` contract remains unchanged.

The application still owns prompt semantics, strict parsers, typed domain records,
tenant authorization, persistence, and fail-closed handling. Auto orchestration is
not permission to accept malformed or unsupported model output.

## Consequences

A simple extraction may still resolve to one worker when that is the
quality-sufficient least-cost plan. Evaluation and uncertain classification can use
a verifier, while complex synthesis can use a conducted workflow, without changing
LineageWeave's public interfaces. Returned trace and usage evidence remain available
for empirical calibration.

## References

Omidvar, H., & Akhlaghi, V. (2026). *A communication-theoretic framework for LLM agents: Cost-aware adaptive reliability* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2605.09121

Tang, Y., Cetin, E., Xu, J., Sun, Q., Nielsen, S., Richard, V., Goda, H., Tymchenko, I., Nguyen, N., Lee, H., Ashiga, M., Kotyan, S., Kuroki, S., & Clanuwat, T. (2026). *Sakana Fugu technical report* [Technical report]. arXiv. https://doi.org/10.48550/arXiv.2606.21228
''',
        encoding="utf-8",
    )

changelog = CHANGELOG_PATH.read_text(encoding="utf-8")
entry = (
    "- Product LLM adapters now delegate their default execution tier to "
    "contextual-orchestrator `auto` instead of forcing a single-model `route`; "
    "the explicit adjudication `verify` contract remains unchanged.\n"
)
if entry not in changelog:
    insertion = "## [Unreleased]\n\n### Changed\n\n" + entry + "\n"
    marker = "## [0.71.0]"
    if marker not in changelog:
        raise RuntimeError("CHANGELOG latest release marker was not found")
    changelog = changelog.replace(marker, insertion + marker, 1)
    CHANGELOG_PATH.write_text(changelog, encoding="utf-8")
