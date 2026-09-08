"""Semantic identifier contracts for the authorized job-architecture importer."""

from __future__ import annotations

import ast
from pathlib import Path


_GENERIC_OWNED_NAMES = {
    "args",
    "bindings",
    "child",
    "children",
    "code",
    "conn",
    "count",
    "digest",
    "edge",
    "edges",
    "entity_id",
    "field",
    "incoming",
    "key",
    "kind",
    "missing",
    "name",
    "node",
    "nodes",
    "occupation",
    "parent",
    "parsed",
    "parser",
    "path",
    "ready",
    "reader",
    "row",
    "scheme",
    "supplied",
    "text",
    "value",
    "version",
    "visited",
}


def _bound_names(source_tree: ast.AST) -> set[str]:
    """Collect function, argument, assignment, and loop-target names."""
    bound_names: set[str] = set()
    for syntax_node in ast.walk(source_tree):
        if isinstance(syntax_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bound_names.add(syntax_node.name)
            bound_names.update(
                argument.arg
                for argument in (
                    *syntax_node.args.posonlyargs,
                    *syntax_node.args.args,
                    *syntax_node.args.kwonlyargs,
                )
            )
        elif isinstance(syntax_node, ast.Name) and isinstance(
            syntax_node.ctx, (ast.Store, ast.Param)
        ):
            bound_names.add(syntax_node.id)
    return bound_names


def test_job_architecture_importer_uses_bounded_context_names() -> None:
    """Reject underspecified owned identifiers while preserving source contracts."""
    source_file = Path(__file__).parents[1] / "scripts" / "import_job_architecture.py"
    source_tree = ast.parse(source_file.read_text(encoding="utf-8"))

    assert _GENERIC_OWNED_NAMES.isdisjoint(_bound_names(source_tree))
