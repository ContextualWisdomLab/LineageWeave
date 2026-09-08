"""Machine-checkable DDD invariants that do not depend on one framework layout.

These checks protect domain ownership and scientific vocabulary. They avoid a
blanket folder template: directory moves still require an ADR/context-map
reason and consumer migration evidence.
"""

from __future__ import annotations

import ast
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_RUNTIME_ROOTS = ("backend", "lineageweave", "scripts")
_FORBIDDEN_RASCH_ALIASES = {
    "Rasch/1PL",
    "Rasch = 1PL",
    "Rasch (1PL)",
    "rasch/1pl",
    "rasch = 1pl",
    "rasch (1pl)",
}


def _runtime_python_files() -> list[Path]:
    paths: list[Path] = []
    for root_name in _RUNTIME_ROOTS:
        root = _ROOT / root_name
        paths.extend(path for path in root.rglob("*.py") if "tests" not in path.parts)
    return sorted(paths)


def _runtime_string_literals(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def test_context_map_names_canonical_owner_boundaries() -> None:
    """The repository must have one discoverable map of its owner contracts."""
    context_map = (_ROOT / "docs" / "context-map.md").read_text(encoding="utf-8")
    for owner in (
        "contextual-orchestrator",
        "fast-mlsirm",
        "TEPP",
        "RankWeave",
        "ThreadWeave",
        "Keyverse",
        "EgressWeave",
    ):
        assert owner in context_map
    assert "Measurement Policy" in context_map
    assert "Instrument Administration" in context_map
    assert "Evidence & Adjudication" in context_map
    assert "Reporting & Interpretation" in context_map


def test_ubiquitous_language_keeps_rasch_distinct_from_generic_1pl() -> None:
    """Rasch and generic one-parameter logistic IRT remain different concepts."""
    vocabulary = (_ROOT / "docs" / "ubiquitous-language.md").read_text(encoding="utf-8")
    assert "**Rasch**" in vocabulary
    assert "**2PLM (`irt_2plm`)**" in vocabulary
    assert "**3PLM (`irt_3plm`)**" in vocabulary
    assert "**4PLM (`irt_4plm`)**" in vocabulary
    assert "never an alias" in vocabulary


def test_runtime_does_not_alias_rasch_to_generic_1pl() -> None:
    """No production Python literal may encode the forbidden Rasch=1PL shorthand."""
    violations: dict[str, list[str]] = {}
    for path in _runtime_python_files():
        literals = _runtime_string_literals(path)
        matched = sorted(alias for alias in _FORBIDDEN_RASCH_ALIASES if alias in literals)
        if matched:
            violations[str(path.relative_to(_ROOT))] = matched
    assert violations == {}


def test_generic_1pl_identifier_is_not_a_normal_runtime_choice() -> None:
    """A future generic 1PL use requires a deliberate ADR and fitness-test change."""
    violations: list[str] = []
    for path in _runtime_python_files():
        if "irt_1pl_logistic" in _runtime_string_literals(path):
            violations.append(str(path.relative_to(_ROOT)))
    assert violations == []
