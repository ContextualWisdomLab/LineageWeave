"""Naming contract for the governed ontology-site publisher."""

from __future__ import annotations

import ast
from pathlib import Path

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "publish_ontology_site.py"


def test_ontology_site_publisher_uses_semantic_owned_identifiers() -> None:
    """Keep publication, graph, compatibility, and CLI names specific."""
    syntax_tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
    owned_identifiers = {
        syntax_node.id
        for syntax_node in ast.walk(syntax_tree)
        if isinstance(syntax_node, ast.Name)
    }
    owned_identifiers.update(
        syntax_node.arg
        for syntax_node in ast.walk(syntax_tree)
        if isinstance(syntax_node, ast.arg)
    )
    owned_identifiers.update(
        syntax_node.name
        for syntax_node in ast.walk(syntax_tree)
        if isinstance(syntax_node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )

    assert owned_identifiers.isdisjoint(
        {
            "_fragment",
            "_parse_args",
            "args",
            "canonical",
            "compatibility",
            "fragment",
            "graph",
            "iri",
            "item",
            "kind",
            "kinds",
            "mapping",
            "mappings",
            "module",
            "output",
            "parser",
            "path",
            "predicate",
            "profile",
            "renderer",
            "requested",
            "root",
            "scheme",
            "script",
            "source",
            "spec",
            "subject",
            "subjects",
            "target",
            "value",
        }
    )
    assert {
        "canonical_ontology_graph",
        "command_arguments",
        "ontology_publication_parser",
        "ontology_subject",
        "publication_output_dir",
        "repository_root",
    } <= owned_identifiers
